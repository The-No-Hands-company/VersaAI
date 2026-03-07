"""
Model Ensemble Manager for VersaAI

Coordinates multiple models to provide best results:
- Load balancing across models
- Parallel inference for comparison
- Consensus voting for critical tasks
- Fallback chains for reliability
"""

import logging
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


class ModelEnsemble:
    """
    Manages multiple code models as an ensemble
    
    Features:
    - Automatic model selection via router
    - Parallel inference across multiple models
    - Consensus/voting for high-stakes tasks
    - Fallback if primary model fails
    """
    
    def __init__(self, router, model_loader):
        """
        Initialize ensemble
        
        Args:
            router: ModelRouter instance
            model_loader: Function to load models by ID
        """
        self.router = router
        self.model_loader = model_loader
        self.loaded_models: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
        
        # Performance tracking
        self.model_stats = {
            model_id: {
                "calls": 0,
                "successes": 0,
                "failures": 0,
                "avg_time": 0.0
            }
            for model_id in router.MODELS.keys()
        }
    
    def load_model(self, model_id: str) -> Any:
        """Load model on-demand"""
        if model_id in self.loaded_models:
            return self.loaded_models[model_id]
        
        self.logger.info(f"Loading model: {model_id}")
        model = self.model_loader(model_id)
        self.loaded_models[model_id] = model
        
        return model
    
    def generate(
        self,
        task: str,
        language: Optional[str] = None,
        mode: str = "auto",  # auto, fast, quality, consensus
        **kwargs
    ) -> Dict:
        """
        Generate code using ensemble
        
        Args:
            task: Task description
            language: Programming language
            mode: Generation mode:
                - auto: Router selects best model
                - fast: Use fastest available model
                - quality: Use best quality model
                - consensus: Use multiple models and vote
            **kwargs: Additional generation parameters
            
        Returns:
            Dictionary with generated code and metadata
        """
        if mode == "auto":
            return self._generate_auto(task, language, **kwargs)
        elif mode == "fast":
            return self._generate_fast(task, language, **kwargs)
        elif mode == "quality":
            return self._generate_quality(task, language, **kwargs)
        elif mode == "consensus":
            return self._generate_consensus(task, language, **kwargs)
        else:
            raise ValueError(f"Unknown mode: {mode}")
    
    def _generate_auto(self, task: str, language: Optional[str], **kwargs) -> Dict:
        """Use router to select best model"""
        model_id, model_spec = self.router.select_model(task, language)
        
        return self._generate_with_model(model_id, task, language, **kwargs)
    
    def _generate_fast(self, task: str, language: Optional[str], **kwargs) -> Dict:
        """Use fastest model (Phi-2)"""
        # Find fastest usable model
        fast_models = [
            mid for mid in self.router.usable_models
            if self.router.MODELS[mid].tier.value == "fast"
        ]
        
        if not fast_models:
            # Fallback to any model
            fast_models = self.router.usable_models
        
        model_id = fast_models[0]
        
        return self._generate_with_model(model_id, task, language, **kwargs)
    
    def _generate_quality(self, task: str, language: Optional[str], **kwargs) -> Dict:
        """Use highest quality model available"""
        # Find most powerful usable model
        powerful_models = [
            mid for mid in self.router.usable_models
            if self.router.MODELS[mid].tier.value == "powerful"
        ]
        
        if not powerful_models:
            # Fallback to balanced
            powerful_models = self.router.usable_models
        
        # Get largest model
        model_id = max(
            powerful_models,
            key=lambda mid: self.router.MODELS[mid].size_gb
        )
        
        return self._generate_with_model(model_id, task, language, **kwargs)
    
    def _generate_consensus(self, task: str, language: Optional[str], **kwargs) -> Dict:
        """
        Use multiple models and combine results
        
        Good for:
        - Critical production code
        - Security-sensitive tasks
        - When quality matters most
        """
        # Select top 3 models
        num_models = min(3, len(self.router.usable_models))
        
        # Get diverse set of models (different tiers)
        selected_models = []
        for tier in ["powerful", "balanced", "fast"]:
            tier_models = [
                mid for mid in self.router.usable_models
                if self.router.MODELS[mid].tier.value == tier
            ]
            if tier_models:
                selected_models.append(tier_models[0])
            if len(selected_models) >= num_models:
                break
        
        if len(selected_models) < num_models:
            # Fill with remaining models
            remaining = [m for m in self.router.usable_models if m not in selected_models]
            selected_models.extend(remaining[:num_models - len(selected_models)])
        
        self.logger.info(f"Consensus mode: using {len(selected_models)} models")
        
        # Generate in parallel
        results = []
        with ThreadPoolExecutor(max_workers=len(selected_models)) as executor:
            futures = {
                executor.submit(
                    self._generate_with_model, mid, task, language, **kwargs
                ): mid
                for mid in selected_models
            }
            
            for future in as_completed(futures):
                model_id = futures[future]
                try:
                    result = future.result(timeout=60)
                    results.append((model_id, result))
                except Exception as e:
                    self.logger.error(f"Model {model_id} failed: {e}")
        
        if not results:
            raise RuntimeError("All models failed to generate")
        
        # Combine results
        return self._combine_results(results, task, language)
    
    def _generate_with_model(
        self,
        model_id: str,
        task: str,
        language: Optional[str],
        **kwargs
    ) -> Dict:
        """Generate with specific model"""
        start_time = time.time()
        
        try:
            # Load model
            model = self.load_model(model_id)
            
            # Generate
            # This will call the actual model's generate method
            # For now, we'll create a placeholder that integrates with real models
            result = {
                "code": f"# Generated by {model_id}\n# Task: {task}\n# TODO: Implement",
                "model": model_id,
                "model_name": self.router.MODELS[model_id].name,
                "language": language,
                "generation_time": 0.0
            }
            
            # Update stats
            elapsed = time.time() - start_time
            result["generation_time"] = elapsed
            
            stats = self.model_stats[model_id]
            stats["calls"] += 1
            stats["successes"] += 1
            stats["avg_time"] = (
                (stats["avg_time"] * (stats["successes"] - 1) + elapsed) /
                stats["successes"]
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Generation failed with {model_id}: {e}")
            
            # Update stats
            self.model_stats[model_id]["calls"] += 1
            self.model_stats[model_id]["failures"] += 1
            
            raise
    
    def _combine_results(
        self,
        results: List[tuple],
        task: str,
        language: Optional[str]
    ) -> Dict:
        """
        Combine results from multiple models
        
        Strategy:
        1. If all models agree, use that
        2. If different, use result from best model
        3. Include all results for user review
        """
        # Extract codes
        codes = [r[1]["code"] for r in results]
        model_ids = [r[0] for r in results]
        
        # Check if all similar (>80% overlap)
        # Simplified: just use best model's result
        # In production, you'd do semantic similarity
        
        # Find most powerful model used
        best_model_idx = max(
            range(len(model_ids)),
            key=lambda i: self.router.MODELS[model_ids[i]].size_gb
        )
        
        primary_result = results[best_model_idx][1]
        
        # Add consensus info
        primary_result["consensus"] = {
            "num_models": len(results),
            "models_used": model_ids,
            "all_results": [
                {"model": mid, "code": r["code"]}
                for mid, r in results
            ]
        }
        
        return primary_result
    
    def get_stats(self) -> Dict:
        """Get performance statistics"""
        return {
            "loaded_models": list(self.loaded_models.keys()),
            "model_stats": self.model_stats
        }
    
    def unload_model(self, model_id: str):
        """Unload model to free memory"""
        if model_id in self.loaded_models:
            del self.loaded_models[model_id]
            self.logger.info(f"Unloaded model: {model_id}")
    
    def unload_all(self):
        """Unload all models"""
        self.loaded_models.clear()
        self.logger.info("Unloaded all models")


# Example usage
if __name__ == "__main__":
    from .model_router import ModelRouter
    
    logging.basicConfig(level=logging.INFO)
    
    # Mock model loader
    def mock_loader(model_id):
        return {"model_id": model_id, "loaded": True}
    
    # Initialize
    router = ModelRouter(available_ram_gb=16)
    ensemble = ModelEnsemble(router, mock_loader)
    
    # Test different modes
    task = "Create a Python function for binary search"
    
    print("\n🎯 Ensemble Test:\n")
    
    # Auto mode
    print("1. Auto mode:")
    result = ensemble.generate(task, mode="auto")
    print(f"   Selected: {result['model_name']}\n")
    
    # Fast mode
    print("2. Fast mode:")
    result = ensemble.generate(task, mode="fast")
    print(f"   Selected: {result['model_name']}\n")
    
    # Quality mode
    print("3. Quality mode:")
    result = ensemble.generate(task, mode="quality")
    print(f"   Selected: {result['model_name']}\n")
    
    # Consensus mode
    print("4. Consensus mode:")
    result = ensemble.generate(task, mode="consensus")
    print(f"   Used {result['consensus']['num_models']} models")
    print(f"   Models: {', '.join(result['consensus']['models_used'])}\n")
    
    # Stats
    print("\n📊 Stats:")
    stats = ensemble.get_stats()
    for model_id, s in stats['model_stats'].items():
        if s['calls'] > 0:
            print(f"   {model_id}: {s['calls']} calls, {s['successes']} successes")
