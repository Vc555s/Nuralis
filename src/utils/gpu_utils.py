# src/utils/gpu_utils.py
import torch
from typing import Dict, Optional

class GPUManager:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.gpu_memory = self.get_gpu_memory() if self.device == "cuda" else None
        
    def get_gpu_memory(self) -> Dict:
        """Get GPU memory information"""
        if torch.cuda.is_available():
            return {
                "total": torch.cuda.get_device_properties(0).total_memory / 1e9,
                "allocated": torch.cuda.memory_allocated() / 1e9,
                "cached": torch.cuda.memory_reserved() / 1e9
            }
        return None
    
    def clear_memory(self):
        """Clear GPU memory cache"""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

gpu_manager = GPUManager()
