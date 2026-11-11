# src/utils/config_loader.py
import os
from pathlib import Path
from typing import Dict, Optional
import yaml
from loguru import logger

def load_config(config_path: Optional[str] = None) -> Dict:
    """Load configuration with proper error handling"""
    try:
        if config_path is None:
            root_dir = Path(__file__).parent.parent.parent
            config_path = root_dir / "config" / "main_config.yaml"
        
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found at: {config_path}")
            
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        if not config:
            raise ValueError("Empty configuration file")
            
        logger.info(f"✅ Configuration loaded from {config_path}")
        return config
        
    except Exception as e:
        logger.error(f"❌ Failed to load configuration: {str(e)}")
        raise