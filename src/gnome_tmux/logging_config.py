"""
logging_config.py - Configuración de logging con loguru

Autor: Homero Thompson del Lago del Terror
"""

import sys
from pathlib import Path

from loguru import logger

# Remover handler por defecto
logger.remove()

# Configurar logging para la aplicación
LOG_DIR = Path.home() / ".local" / "share" / "tmuxgui" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Handler para stderr (solo WARNING y superior)
logger.add(
    sys.stderr,
    level="WARNING",
    format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> | {message}",
)

# Handler para archivo (DEBUG y superior)
logger.add(
    LOG_DIR / "tmuxgui_{time:YYYY-MM-DD}.log",
    rotation="00:00",  # Rotar a medianoche
    retention="7 days",  # Mantener 7 días
    compression="zip",  # Comprimir logs antiguos
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
)

__all__ = ["logger"]
