# src/utils/logging_utils.py
from loguru import logger
import sys
from pathlib import Path

# Configure logging
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logger.remove()
logger.add(sys.stderr, level="INFO", 
          format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | {level} | {message}")
logger.add(LOG_DIR / "research_analyst.log", level="DEBUG", 
          rotation="10 MB", retention="7 days")

__all__ = ["logger"]