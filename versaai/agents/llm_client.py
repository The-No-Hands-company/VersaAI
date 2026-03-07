"""
Unified LLM Client — single interface for all agent LLM calls.

This client wraps VersaAI's provider infrastructure (Ollama, llama.cpp)
and exposes a clean, consistent interface that all agents share.

The key problem it solves: CodingAgent uses `.generate(prompt, config=GenerationConfig, stream=True)`,
ResearchAgent uses `.generate(prompt, max_tokens=200, temperature=0.7)`, and
ReasoningEngine uses `llm_function(prompt, params_dict)`. This client unifies all three.

Usage:
    >>> from versaai.agents.llm_client import LLMClient
    >>> llm = LLMClient()  # Uses default model from config
    >>> llm = LLMClient(model="ollama/qwen2.5-coder:7b")
    >>>
    >>> # Simple completion
    >>> response = llm.complete("Explain quicksort")
    >>>
    >>> # Chat with messages
    >>> response = llm.chat([
    ...     {"role": "system", "content": "You are a coding assistant."},
    ...     {"role": "user", "content": "Write a sort function"},
    ... ])
    >>>
    >>> # Streaming
    >>> for token in llm.chat_stream(messages):
    ...     print(token, end="", flush=True)
    >>>
    >>> # As a callable (for ReasoningEngine)
    >>> engine = ReasoningEngine(llm_function=llm)
    >>> engine.reason("What is 15% of 80?")
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Union

from versaai.config import settings
from versaai.api.provider_registry import get_registry

logger = logging.getLogger(__name__)


@dataclass
class GenerationParams:
    """
    Unified generation parameters.

    Normalizes the various parameter formats used across agents:
    - CodingAgent's GenerationConfig (max_tokens, temperature)
    - ResearchAgent's kwargs (max_tokens=200, temperature=0.7)
    - ReasoningEngine's params dict ({'temperature': 0.3})
    """
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 0.95
    stop: Optional[List[str]] = None
    system_prompt: Optional[str] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "GenerationParams":
        """Create from a dict, ignoring unknown keys."""
        known = {"temperature", "max_tokens", "top_p", "stop", "system_prompt"}
        return cls(**{k: v for k, v in d.items() if k in known})

    @classmethod
    def from_kwargs(cls, **kwargs) -> "GenerationParams":
        """Create from keyword arguments, ignoring unknown keys."""
        return cls.from_dict(kwargs)


class LLMClient:
    """
    Unified LLM client used by all agents.

    Wraps the provider registry to give agents a simple interface.
    Also callable — `llm("prompt", params)` — for ReasoningEngine compatibility.

    Provider resolution:
    - If model is specified: "ollama/qwen2.5-coder:7b" → Ollama with that model
    - If no model: uses default from config (settings.models.default_provider / default_model)
    """

    def __init__(
        self,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ):
        self._registry = get_registry()

        # Resolve model
        if model:
            self._model_id = model
        else:
            provider = settings.models.default_provider
            if provider == "ollama":
                self._model_id = f"ollama/{settings.models.ollama.default_model}"
            elif provider == "llamacpp":
                self._model_id = "llamacpp/default"
            else:
                self._model_id = f"{provider}/default"

        self._system_prompt = system_prompt
        self._default_temperature = temperature
        self._default_max_tokens = max_tokens

        # Resolve provider once
        self._provider, self._model_name = self._registry.get_provider_and_model(
            self._model_id
        )
        self._provider_name, _ = self._registry.parse_model_id(self._model_id)

        logger.info(
            f"LLMClient initialized: provider={self._provider_name} "
            f"model={self._model_name}"
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model_name(self) -> str:
        return self._model_name

    # ------------------------------------------------------------------
    # Core methods
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        prompt_or_messages: Union[str, List[Dict[str, str]]],
        system_prompt: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """Normalize input into a message list."""
        sys = system_prompt or self._system_prompt

        if isinstance(prompt_or_messages, str):
            messages = []
            if sys:
                messages.append({"role": "system", "content": sys})
            messages.append({"role": "user", "content": prompt_or_messages})
            return messages

        # Already a message list
        messages = list(prompt_or_messages)
        if sys and (not messages or messages[0].get("role") != "system"):
            messages.insert(0, {"role": "system", "content": sys})
        return messages

    def chat(
        self,
        messages: Union[str, List[Dict[str, str]]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: float = 0.95,
        stop: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Non-streaming chat. Returns the full response as a string.

        Args:
            messages: Either a prompt string or list of chat messages.
            temperature: Sampling temperature (default: instance default).
            max_tokens: Max tokens to generate.
            top_p: Nucleus sampling threshold.
            stop: Stop sequences.
            system_prompt: Override system prompt for this call.

        Returns:
            The assistant's response text.
        """
        msgs = self._build_messages(messages, system_prompt)
        temp = temperature if temperature is not None else self._default_temperature
        max_tok = max_tokens or self._default_max_tokens

        if self._provider_name == "ollama":
            response = self._provider.chat(
                messages=msgs,
                model=self._model_name,
                temperature=temp,
                max_tokens=max_tok,
                top_p=top_p,
                stop=stop,
            )
            return response.get("message", {}).get("content", "")

        elif self._provider_name == "llamacpp":
            response = self._provider.chat(
                messages=msgs,
                temperature=temp,
                max_tokens=max_tok,
                top_p=top_p,
                stop=stop,
            )
            choices = response.get("choices", [{}])
            return choices[0].get("message", {}).get("content", "") if choices else ""

        else:
            raise ValueError(f"Unsupported provider: {self._provider_name}")

    def chat_stream(
        self,
        messages: Union[str, List[Dict[str, str]]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: float = 0.95,
        stop: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
    ) -> Iterator[str]:
        """
        Streaming chat. Yields tokens as they arrive.

        Usage:
            >>> for token in llm.chat_stream("Write hello world"):
            ...     print(token, end="", flush=True)
        """
        msgs = self._build_messages(messages, system_prompt)
        temp = temperature if temperature is not None else self._default_temperature
        max_tok = max_tokens or self._default_max_tokens

        if self._provider_name == "ollama":
            for chunk in self._provider.chat_stream(
                messages=msgs,
                model=self._model_name,
                temperature=temp,
                max_tokens=max_tok,
                top_p=top_p,
                stop=stop,
            ):
                content = chunk.get("message", {}).get("content", "")
                if content:
                    yield content

        elif self._provider_name == "llamacpp":
            for chunk in self._provider.chat_stream(
                messages=msgs,
                temperature=temp,
                max_tokens=max_tok,
                top_p=top_p,
                stop=stop,
            ):
                choices = chunk.get("choices", [{}])
                content = (
                    choices[0].get("delta", {}).get("content", "")
                    if choices
                    else ""
                )
                if content:
                    yield content

        else:
            raise ValueError(f"Unsupported provider: {self._provider_name}")

    def complete(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Simple text completion (convenience wrapper around chat).

        Args:
            prompt: The prompt text.
            temperature: Sampling temperature.
            max_tokens: Max tokens to generate.
            system_prompt: Optional system prompt.

        Returns:
            The generated text.
        """
        return self.chat(
            prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
        )

    def complete_stream(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
    ) -> Iterator[str]:
        """Streaming text completion."""
        yield from self.chat_stream(
            prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
        )

    # ------------------------------------------------------------------
    # Callable interface (for ReasoningEngine)
    # ------------------------------------------------------------------

    def __call__(
        self,
        prompt: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Callable interface for backward compatibility with ReasoningEngine.

        ReasoningEngine passes: llm_function(prompt, {'temperature': 0.3})
        This makes LLMClient work as a drop-in replacement for the placeholder.

        Args:
            prompt: The prompt text.
            params: Optional dict with generation parameters.

        Returns:
            The generated text.
        """
        if params:
            gp = GenerationParams.from_dict(params)
            return self.chat(
                prompt,
                temperature=gp.temperature,
                max_tokens=gp.max_tokens,
                top_p=gp.top_p,
                stop=gp.stop,
                system_prompt=gp.system_prompt,
            )
        return self.complete(prompt)

    # ------------------------------------------------------------------
    # Generate interface (for CodingAgent / ResearchAgent compatibility)
    # ------------------------------------------------------------------

    def generate(
        self,
        prompt: str,
        config: Any = None,
        stream: bool = False,
        **kwargs,
    ) -> Union[str, Iterator[Dict[str, Any]]]:
        """
        Generate interface matching the old CodeLLMBase.generate() signature.

        This allows LLMClient to be a drop-in replacement for:
        - CodingAgent: llm.generate(prompt, config=GenerationConfig, stream=True)
        - ResearchAgent: llm.generate(prompt, max_tokens=200, temperature=0.7)

        When stream=True, yields dicts: {"choices": [{"text": "token"}]}
        matching the format CodingAgent's stream consumer expects.
        """
        # Extract params from config object or kwargs
        temperature = kwargs.get("temperature", self._default_temperature)
        max_tokens = kwargs.get("max_tokens", self._default_max_tokens)

        if config is not None:
            # CodingAgent passes a GenerationConfig dataclass
            temperature = getattr(config, "temperature", temperature)
            max_tokens = getattr(config, "max_tokens", max_tokens)

        if stream:
            return self._generate_stream(prompt, temperature, max_tokens)
        else:
            return self.chat(
                prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )

    def _generate_stream(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> Iterator[Dict[str, Any]]:
        """Yield stream chunks in the format CodingAgent expects."""
        for token in self.chat_stream(
            prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            yield {"choices": [{"text": token}]}

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"LLMClient(model={self._model_id!r}, "
            f"provider={self._provider_name!r})"
        )
