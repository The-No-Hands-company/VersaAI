"""
Multimodal Pipeline Framework — cross-modal processing and routing.

Provides an extensible framework for handling multiple input/output modalities
(text, image, audio, video, 3D) with automatic detection, normalization,
and routing between processors.

Architecture:
    ModalityDetector → InputNormalizer → ModalityRouter → Processor → Output

Each Processor implements a modality→modality transformation:
    - TextToText      (LLM inference — already implemented)
    - ImageToText     (captioning, OCR — future: CLIP, LLaVA)
    - TextToImage     (generation — future: Stable Diffusion, DALL-E)
    - AudioToText     (transcription — future: Whisper)
    - TextToAudio     (TTS — future: Bark, XTTS)
    - TextTo3D        (3D generation — future: Point-E, TripoSR)

This module provides the FRAMEWORK; actual model integrations are added
incrementally as processors are connected.

Usage:
    >>> from versaai.multimodal import MultimodalPipeline, Modality
    >>> pipeline = MultimodalPipeline()
    >>> result = pipeline.process(
    ...     input_data="Describe this image",
    ...     input_modality=Modality.TEXT,
    ...     target_modality=Modality.TEXT,
    ... )
"""

import base64
import logging
import mimetypes
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


# ============================================================================
# Modality definitions
# ============================================================================


class Modality(str, Enum):
    """Supported modality types."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    THREE_D = "3d"
    CODE = "code"    # Specialized text modality for code
    UNKNOWN = "unknown"


@dataclass
class ModalityPayload:
    """
    Normalized representation of any modality input/output.

    For text: data is str
    For binary (image/audio/video/3D): data is bytes (raw) or str (base64)
    """
    modality: Modality
    data: Union[str, bytes]
    mime_type: str = "text/plain"
    metadata: Dict[str, Any] = field(default_factory=dict)
    encoding: str = "utf-8"  # For text; "base64" for binary

    @property
    def text(self) -> str:
        """Get data as text. Decodes bytes if needed."""
        if isinstance(self.data, str):
            return self.data
        return self.data.decode(self.encoding, errors="replace")

    @property
    def binary(self) -> bytes:
        """Get data as bytes. Encodes text if needed."""
        if isinstance(self.data, bytes):
            return self.data
        if self.encoding == "base64":
            return base64.b64decode(self.data)
        return self.data.encode(self.encoding)

    def size_bytes(self) -> int:
        if isinstance(self.data, bytes):
            return len(self.data)
        return len(self.data.encode("utf-8"))


# ============================================================================
# Modality Detection
# ============================================================================


# MIME type → Modality mapping
_MIME_MAP: Dict[str, Modality] = {
    "text/plain": Modality.TEXT,
    "text/markdown": Modality.TEXT,
    "text/html": Modality.TEXT,
    "application/json": Modality.TEXT,
    "image/png": Modality.IMAGE,
    "image/jpeg": Modality.IMAGE,
    "image/gif": Modality.IMAGE,
    "image/webp": Modality.IMAGE,
    "image/svg+xml": Modality.IMAGE,
    "audio/wav": Modality.AUDIO,
    "audio/mp3": Modality.AUDIO,
    "audio/mpeg": Modality.AUDIO,
    "audio/ogg": Modality.AUDIO,
    "audio/flac": Modality.AUDIO,
    "video/mp4": Modality.VIDEO,
    "video/webm": Modality.VIDEO,
    "video/avi": Modality.VIDEO,
    "model/gltf+json": Modality.THREE_D,
    "model/gltf-binary": Modality.THREE_D,
    "application/octet-stream": Modality.UNKNOWN,
}

# Extension → Modality (fallback)
_EXT_MAP: Dict[str, Modality] = {
    ".txt": Modality.TEXT, ".md": Modality.TEXT,
    ".py": Modality.CODE, ".js": Modality.CODE, ".ts": Modality.CODE,
    ".cpp": Modality.CODE, ".hpp": Modality.CODE, ".c": Modality.CODE,
    ".rs": Modality.CODE, ".go": Modality.CODE, ".java": Modality.CODE,
    ".png": Modality.IMAGE, ".jpg": Modality.IMAGE, ".jpeg": Modality.IMAGE,
    ".gif": Modality.IMAGE, ".webp": Modality.IMAGE, ".svg": Modality.IMAGE,
    ".wav": Modality.AUDIO, ".mp3": Modality.AUDIO, ".ogg": Modality.AUDIO,
    ".flac": Modality.AUDIO,
    ".mp4": Modality.VIDEO, ".webm": Modality.VIDEO, ".avi": Modality.VIDEO,
    ".glb": Modality.THREE_D, ".gltf": Modality.THREE_D,
    ".obj": Modality.THREE_D, ".stl": Modality.THREE_D,
    ".fbx": Modality.THREE_D, ".usdz": Modality.THREE_D,
}


def detect_modality(
    data: Union[str, bytes, None] = None,
    mime_type: Optional[str] = None,
    file_path: Optional[str] = None,
) -> Modality:
    """
    Detect the modality of input data.

    Priority: explicit mime_type → file extension → content heuristics
    """
    if mime_type:
        m = _MIME_MAP.get(mime_type)
        if m and m != Modality.UNKNOWN:
            return m

    if file_path:
        ext = Path(file_path).suffix.lower()
        m = _EXT_MAP.get(ext)
        if m:
            return m

    if isinstance(data, str):
        return Modality.TEXT

    if isinstance(data, bytes):
        # Magic byte detection for common formats
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return Modality.IMAGE
        if data[:3] == b"\xff\xd8\xff":
            return Modality.IMAGE
        if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
            return Modality.AUDIO
        if data[:4] in (b"\x00\x00\x00\x1c", b"\x00\x00\x00\x18"):
            return Modality.VIDEO
        if data[:4] == b"glTF":
            return Modality.THREE_D

    return Modality.UNKNOWN


# ============================================================================
# Processor interface
# ============================================================================


@dataclass
class ProcessorCapability:
    """Declares what a processor can do."""
    input_modality: Modality
    output_modality: Modality
    name: str
    description: str = ""
    max_input_bytes: int = 100 * 1024 * 1024  # 100MB default


class ModalityProcessor(ABC):
    """
    Abstract base class for modality transformation processors.

    Each processor converts from one modality to another.
    """

    @abstractmethod
    def capability(self) -> ProcessorCapability:
        """Declare this processor's input/output modalities."""
        ...

    @abstractmethod
    def process(
        self, payload: ModalityPayload, params: Optional[Dict[str, Any]] = None
    ) -> ModalityPayload:
        """
        Transform the input payload to the output modality.

        Args:
            payload: Input data in the source modality.
            params: Optional processing parameters.

        Returns:
            Transformed data in the target modality.
        """
        ...


# ============================================================================
# Built-in Processors
# ============================================================================


class TextToTextProcessor(ModalityProcessor):
    """Pass-through for text→text (delegates to LLM)."""

    def capability(self) -> ProcessorCapability:
        return ProcessorCapability(
            input_modality=Modality.TEXT,
            output_modality=Modality.TEXT,
            name="text_to_text",
            description="LLM text generation",
        )

    def process(
        self, payload: ModalityPayload, params: Optional[Dict[str, Any]] = None
    ) -> ModalityPayload:
        from versaai.agents.llm_client import LLMClient

        cfg = params or {}
        llm = LLMClient(
            model=cfg.get("model"),
            temperature=cfg.get("temperature", 0.7),
        )
        response = llm.complete(payload.text)
        return ModalityPayload(
            modality=Modality.TEXT,
            data=response,
            mime_type="text/plain",
            metadata={"processor": "text_to_text", "model": llm.model_id},
        )


class CodeToTextProcessor(ModalityProcessor):
    """Code analysis / explanation via LLM."""

    def capability(self) -> ProcessorCapability:
        return ProcessorCapability(
            input_modality=Modality.CODE,
            output_modality=Modality.TEXT,
            name="code_to_text",
            description="Code analysis and explanation",
        )

    def process(
        self, payload: ModalityPayload, params: Optional[Dict[str, Any]] = None
    ) -> ModalityPayload:
        from versaai.agents.llm_client import LLMClient

        cfg = params or {}
        llm = LLMClient(
            model=cfg.get("model"),
            system_prompt="You are an expert code analyst. Analyze and explain the code.",
            temperature=0.3,
        )
        response = llm.complete(payload.text)
        return ModalityPayload(
            modality=Modality.TEXT,
            data=response,
            mime_type="text/plain",
            metadata={"processor": "code_to_text"},
        )


# ============================================================================
# Processor Registry
# ============================================================================


class ProcessorRegistry:
    """Registry of available modality processors, keyed by (input, output) pair."""

    def __init__(self):
        self._processors: Dict[Tuple[Modality, Modality], ModalityProcessor] = {}

    def register(self, processor: ModalityProcessor) -> None:
        cap = processor.capability()
        key = (cap.input_modality, cap.output_modality)
        self._processors[key] = processor
        logger.debug("Registered processor: %s → %s", cap.input_modality, cap.output_modality)

    def get(
        self, input_mod: Modality, output_mod: Modality
    ) -> Optional[ModalityProcessor]:
        return self._processors.get((input_mod, output_mod))

    def available_routes(self) -> List[Dict[str, str]]:
        """List all available modality transformation routes."""
        routes = []
        for (inp, out), proc in self._processors.items():
            cap = proc.capability()
            routes.append({
                "input": inp.value,
                "output": out.value,
                "name": cap.name,
                "description": cap.description,
            })
        return routes

    def find_path(
        self, source: Modality, target: Modality, max_hops: int = 3
    ) -> Optional[List[Tuple[Modality, Modality]]]:
        """
        Find a multi-hop path from source to target modality.

        Uses BFS to find shortest transformation chain.
        Returns list of (input, output) tuples representing the path,
        or None if no path exists.
        """
        if source == target:
            return []

        direct = self.get(source, target)
        if direct is not None:
            return [(source, target)]

        # BFS
        from collections import deque
        visited = {source}
        queue: deque[Tuple[Modality, List[Tuple[Modality, Modality]]]] = deque()

        for (inp, out) in self._processors:
            if inp == source and out not in visited:
                queue.append((out, [(inp, out)]))
                visited.add(out)

        while queue:
            current, path = queue.popleft()
            if current == target:
                return path
            if len(path) >= max_hops:
                continue
            for (inp, out) in self._processors:
                if inp == current and out not in visited:
                    visited.add(out)
                    queue.append((out, path + [(inp, out)]))

        return None


# ============================================================================
# Pipeline
# ============================================================================


class MultimodalPipeline:
    """
    Top-level multimodal processing pipeline.

    Automatically detects input modality, finds a transformation path
    to the target modality, and executes the processor chain.
    """

    def __init__(self):
        self._registry = ProcessorRegistry()
        self._register_builtins()

    def _register_builtins(self) -> None:
        """Register all built-in processors."""
        self._registry.register(TextToTextProcessor())
        self._registry.register(CodeToTextProcessor())

    @property
    def registry(self) -> ProcessorRegistry:
        return self._registry

    def process(
        self,
        input_data: Union[str, bytes],
        input_modality: Optional[Modality] = None,
        target_modality: Modality = Modality.TEXT,
        mime_type: Optional[str] = None,
        file_path: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> ModalityPayload:
        """
        Process input through the multimodal pipeline.

        Args:
            input_data: Raw input (text string or binary bytes).
            input_modality: Explicit source modality (auto-detected if None).
            target_modality: Desired output modality.
            mime_type: MIME type hint for detection.
            file_path: File path hint for detection.
            params: Processor-specific parameters.

        Returns:
            Processed ModalityPayload in the target modality.

        Raises:
            ValueError: If no processing path exists.
        """
        start = time.monotonic()

        # Detect input modality
        source = input_modality or detect_modality(
            input_data, mime_type, file_path
        )
        if source == Modality.UNKNOWN:
            source = Modality.TEXT  # Default fallback

        # Build input payload
        payload = ModalityPayload(
            modality=source,
            data=input_data,
            mime_type=mime_type or mimetypes.guess_type(file_path or "")[0] or "text/plain",
            metadata={"source_file": file_path},
        )

        # Same modality — return as-is
        if source == target_modality:
            return payload

        # Find transformation path
        path = self._registry.find_path(source, target_modality)
        if path is None:
            raise ValueError(
                f"No processing path from {source.value} to {target_modality.value}. "
                f"Available routes: {self._registry.available_routes()}"
            )

        # Execute processor chain
        current = payload
        for inp_mod, out_mod in path:
            processor = self._registry.get(inp_mod, out_mod)
            if processor is None:
                raise ValueError(
                    f"Processor for {inp_mod.value}→{out_mod.value} disappeared"
                )
            current = processor.process(current, params)

        current.metadata["pipeline_time_s"] = time.monotonic() - start
        current.metadata["transformation_path"] = [
            f"{a.value}→{b.value}" for a, b in path
        ]
        return current

    def available_routes(self) -> List[Dict[str, str]]:
        """List all available transformation routes."""
        return self._registry.available_routes()
