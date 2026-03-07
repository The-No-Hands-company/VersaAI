"""
Multi-Model Manager for VersaAI

Automatically selects and routes requests to the best available model
based on task complexity, language, and system resources.

This enables users to benefit from ALL downloaded models without
manually choosing which one to use for each task.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from versaai.models.model_router import ModelRouter, TaskComplexity, ModelTier, ModelSpec


@dataclass
class LocalModel:
    """Local GGUF model information"""
    path: Path
    size_bytes: int
    name: str
    tier: ModelTier
    estimated_ram_gb: int


class MultiModelManager:
    """
    Manages multiple local models and automatically selects the best one
    
    Features:
    - Scans for all available local models
    - Tracks system resources (RAM, VRAM)
    - Automatically loads/unloads models as needed
    - Routes requests to optimal model
    - Fallback to smaller models if resource constrained
    """
    
    # Model patterns to detect from filename
    MODEL_PATTERNS = {
        'deepseek-coder-1.3b': {
            'patterns': ['deepseek', '1.3b', '1_3b'],
            'tier': ModelTier.FAST,
            'estimated_ram': 4
        },
        'deepseek-coder-6.7b': {
            'patterns': ['deepseek', '6.7b', '6_7b'],
            'tier': ModelTier.BALANCED,
            'estimated_ram': 8
        },
        'starcoder2-7b': {
            'patterns': ['starcoder2', '7b'],
            'tier': ModelTier.BALANCED,
            'estimated_ram': 8
        },
        'codellama-7b': {
            'patterns': ['codellama', '7b'],
            'tier': ModelTier.BALANCED,
            'estimated_ram': 8
        },
        'codellama-13b': {
            'patterns': ['codellama', '13b'],
            'tier': ModelTier.POWERFUL,
            'estimated_ram': 16
        },
        'deepseek-coder-33b': {
            'patterns': ['deepseek', '33b'],
            'tier': ModelTier.POWERFUL,
            'estimated_ram': 32
        },
        'wizardcoder-15b': {
            'patterns': ['wizard', '15b'],
            'tier': ModelTier.POWERFUL,
            'estimated_ram': 18
        }
    }
    
    def __init__(
        self,
        models_dir: Optional[Path] = None,
        auto_detect: bool = True,
        enable_fallback: bool = True
    ):
        """
        Initialize multi-model manager
        
        Args:
            models_dir: Directory containing GGUF models
            auto_detect: Automatically scan for models
            enable_fallback: Fall back to smaller models if needed
        """
        self.logger = logging.getLogger(__name__)
        
        if models_dir is None:
            models_dir = Path.home() / ".versaai" / "models"
        
        self.models_dir = Path(models_dir)
        self.enable_fallback = enable_fallback
        
        # Detected models
        self.local_models: Dict[str, LocalModel] = {}
        
        # Currently loaded model
        self.current_model = None
        self.current_model_name = None
        
        # Model router for selection logic
        self.router = None
        
        if auto_detect:
            self.scan_models()
    
    def scan_models(self) -> Dict[str, LocalModel]:
        """Scan models directory for GGUF files"""
        if not self.models_dir.exists():
            self.logger.warning(f"Models directory does not exist: {self.models_dir}")
            return {}
        
        self.logger.info(f"Scanning for models in: {self.models_dir}")
        
        # Find all .gguf files
        gguf_files = list(self.models_dir.glob("*.gguf"))
        
        if not gguf_files:
            self.logger.warning(f"No GGUF models found in {self.models_dir}")
            return {}
        
        self.logger.info(f"Found {len(gguf_files)} GGUF file(s)")
        
        # Identify each model
        for gguf_file in gguf_files:
            model_info = self._identify_model(gguf_file)
            if model_info:
                self.local_models[model_info.name] = model_info
                self.logger.info(
                    f"  ✓ {model_info.name}: {gguf_file.name} "
                    f"({model_info.size_bytes / (1024**3):.1f}GB, "
                    f"~{model_info.estimated_ram_gb}GB RAM)"
                )
        
        # Initialize router with available models
        if self.local_models:
            available_ram = self._get_available_ram_gb()
            self.router = ModelRouter(
                available_models=list(self.local_models.keys()),
                available_ram_gb=int(available_ram)
            )
            
            self.logger.info(
                f"Multi-model manager ready with {len(self.local_models)} model(s)"
            )
        
        return self.local_models
    
    def _identify_model(self, gguf_path: Path) -> Optional[LocalModel]:
        """Identify model from filename"""
        filename_lower = gguf_path.name.lower()
        
        # Try exact matching first (more specific)
        for model_name, config in self.MODEL_PATTERNS.items():
            patterns = config['patterns']
            
            # For models like deepseek-1.3b, need both 'deepseek' AND '1.3b'
            # For models like starcoder2-7b, need both 'starcoder2' AND '7b'
            if all(pattern in filename_lower for pattern in patterns):
                return LocalModel(
                    path=gguf_path,
                    size_bytes=gguf_path.stat().st_size,
                    name=model_name,
                    tier=config['tier'],
                    estimated_ram_gb=config['estimated_ram']
                )
        
        # Try fuzzy matching for common patterns
        if 'deepseek' in filename_lower and ('1.3' in filename_lower or '1_3' in filename_lower):
            return LocalModel(
                path=gguf_path,
                size_bytes=gguf_path.stat().st_size,
                name='deepseek-coder-1.3b',
                tier=ModelTier.FAST,
                estimated_ram_gb=4
            )
        elif 'deepseek' in filename_lower and ('6.7' in filename_lower or '6_7' in filename_lower):
            return LocalModel(
                path=gguf_path,
                size_bytes=gguf_path.stat().st_size,
                name='deepseek-coder-6.7b',
                tier=ModelTier.BALANCED,
                estimated_ram_gb=8
            )
        elif 'deepseek' in filename_lower and '33' in filename_lower:
            return LocalModel(
                path=gguf_path,
                size_bytes=gguf_path.stat().st_size,
                name='deepseek-coder-33b',
                tier=ModelTier.POWERFUL,
                estimated_ram_gb=32
            )
        elif 'starcoder' in filename_lower and '7' in filename_lower:
            return LocalModel(
                path=gguf_path,
                size_bytes=gguf_path.stat().st_size,
                name='starcoder2-7b',
                tier=ModelTier.BALANCED,
                estimated_ram_gb=8
            )
        elif 'codellama' in filename_lower and '7' in filename_lower:
            return LocalModel(
                path=gguf_path,
                size_bytes=gguf_path.stat().st_size,
                name='codellama-7b',
                tier=ModelTier.BALANCED,
                estimated_ram_gb=8
            )
        elif 'codellama' in filename_lower and '13' in filename_lower:
            return LocalModel(
                path=gguf_path,
                size_bytes=gguf_path.stat().st_size,
                name='codellama-13b',
                tier=ModelTier.POWERFUL,
                estimated_ram_gb=16
            )
        elif 'wizard' in filename_lower and '15' in filename_lower:
            return LocalModel(
                path=gguf_path,
                size_bytes=gguf_path.stat().st_size,
                name='wizardcoder-15b',
                tier=ModelTier.POWERFUL,
                estimated_ram_gb=18
            )
        
        # Unknown model - make best guess from size
        size_gb = gguf_path.stat().st_size / (1024**3)
        
        if size_gb < 2:
            tier = ModelTier.FAST
            ram = 4
            name = 'small-model'
        elif size_gb < 6:
            tier = ModelTier.BALANCED
            ram = 8
            name = 'medium-model'
        else:
            tier = ModelTier.POWERFUL
            ram = 16
            name = 'large-model'
        
        return LocalModel(
            path=gguf_path,
            size_bytes=gguf_path.stat().st_size,
            name=f"{name}-{gguf_path.stem[:20]}",
            tier=tier,
            estimated_ram_gb=ram
        )
    
    def _get_available_ram_gb(self) -> float:
        """Get available system RAM in GB"""
        if not PSUTIL_AVAILABLE:
            return 8.0  # Conservative default
        try:
            mem = psutil.virtual_memory()
            return mem.available / (1024**3)
        except:
            return 8.0  # Default assumption
    
    def _get_total_ram_gb(self) -> float:
        """Get total system RAM in GB"""
        if not PSUTIL_AVAILABLE:
            # Try to read from /proc/meminfo on Linux
            try:
                with open('/proc/meminfo', 'r') as f:
                    for line in f:
                        if 'MemTotal' in line:
                            kb = int(line.split()[1])
                            return kb / (1024**2)
            except:
                pass
            return 16.0  # Default assumption
        
        try:
            mem = psutil.virtual_memory()
            return mem.total / (1024**3)
        except:
            return 16.0  # Default assumption
    
    def select_model_for_task(
        self,
        task: str,
        language: Optional[str] = None,
        prefer_speed: bool = False,
        prefer_quality: bool = False
    ) -> Optional[LocalModel]:
        """
        Select best model for the task
        
        Args:
            task: Task description
            language: Programming language
            prefer_speed: Prioritize fast response
            prefer_quality: Prioritize output quality
            
        Returns:
            LocalModel to use, or None if no suitable model
        """
        if not self.router or not self.local_models:
            self.logger.error("No models available")
            return None
        
        # Get available RAM
        available_ram = self._get_available_ram_gb()
        
        # Filter models that can fit in available RAM
        usable_models = [
            name for name, model in self.local_models.items()
            if model.estimated_ram_gb <= available_ram
        ]
        
        if not usable_models:
            if self.enable_fallback:
                # Fall back to smallest model
                smallest = min(
                    self.local_models.values(),
                    key=lambda m: m.estimated_ram_gb
                )
                self.logger.warning(
                    f"Insufficient RAM ({available_ram:.1f}GB available). "
                    f"Using smallest model: {smallest.name}"
                )
                return smallest
            else:
                self.logger.error(
                    f"No models can run with {available_ram:.1f}GB available RAM"
                )
                return None
        
        # Use router to select best model from usable ones
        try:
            # Temporarily update router's available models
            original_usable = self.router.usable_models
            self.router.usable_models = usable_models
            
            model_id, model_spec = self.router.select_model(
                task=task,
                language=language,
                prefer_speed=prefer_speed,
                prefer_quality=prefer_quality
            )
            
            # Restore original
            self.router.usable_models = original_usable
            
            return self.local_models.get(model_id)
            
        except Exception as e:
            self.logger.debug(f"Model selection error (using fallback): {e}")
            # Fall back to first available
            return self.local_models[usable_models[0]]
    
    def get_model_path(self, model_name: str) -> Optional[Path]:
        """Get path to a specific model"""
        model = self.local_models.get(model_name)
        return model.path if model else None
    
    def list_models(self) -> List[Dict]:
        """List all available models with details"""
        models = []
        available_ram = self._get_available_ram_gb()
        total_ram = self._get_total_ram_gb()
        
        for name, model in self.local_models.items():
            can_run = model.estimated_ram_gb <= available_ram
            
            models.append({
                'name': name,
                'path': str(model.path),
                'size_gb': model.size_bytes / (1024**3),
                'tier': model.tier.value,
                'estimated_ram_gb': model.estimated_ram_gb,
                'can_run': can_run,
                'status': 'ready' if can_run else 'insufficient_ram'
            })
        
        # Sort by tier (fast -> balanced -> powerful)
        tier_order = {ModelTier.FAST: 0, ModelTier.BALANCED: 1, ModelTier.POWERFUL: 2}
        models.sort(key=lambda m: tier_order.get(
            ModelTier(m['tier']), 99
        ))
        
        return models
    
    def get_stats(self) -> Dict:
        """Get manager statistics"""
        available_ram = self._get_available_ram_gb()
        total_ram = self._get_total_ram_gb()
        
        usable_count = sum(
            1 for m in self.local_models.values()
            if m.estimated_ram_gb <= available_ram
        )
        
        total_size = sum(m.size_bytes for m in self.local_models.values())
        
        return {
            'total_models': len(self.local_models),
            'usable_models': usable_count,
            'total_size_gb': total_size / (1024**3),
            'available_ram_gb': available_ram,
            'total_ram_gb': total_ram,
            'models_dir': str(self.models_dir)
        }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Initialize manager
    manager = MultiModelManager()
    
    # Show stats
    stats = manager.get_stats()
    print("\n📊 Multi-Model Manager Stats:")
    print(f"  Models found: {stats['total_models']}")
    print(f"  Can run: {stats['usable_models']}")
    print(f"  Total size: {stats['total_size_gb']:.1f}GB")
    print(f"  Available RAM: {stats['available_ram_gb']:.1f}GB / {stats['total_ram_gb']:.1f}GB")
    
    # List models
    print("\n📦 Available Models:")
    for model in manager.list_models():
        status = "✅" if model['can_run'] else "⚠️"
        print(f"{status} {model['name']}: {model['size_gb']:.1f}GB "
              f"(needs {model['estimated_ram_gb']}GB RAM)")
    
    # Test selection
    if stats['usable_models'] > 0:
        print("\n🎯 Testing Model Selection:")
        
        test_tasks = [
            ("Write a simple Python function to add two numbers", "python", True, False),
            ("Debug complex C++ memory management issue", "c++", False, True),
            ("Refactor entire React application architecture", "javascript", False, True),
        ]
        
        for task, lang, speed, quality in test_tasks:
            model = manager.select_model_for_task(task, lang, speed, quality)
            if model:
                print(f"\nTask: {task[:50]}...")
                print(f"  → Model: {model.name} ({model.tier.value})")
                print(f"  → Path: {model.path.name}")
