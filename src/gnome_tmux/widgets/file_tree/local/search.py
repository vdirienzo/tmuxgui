"""
search.py - Búsqueda de archivos locales

Autor: Homero Thompson del Lago del Terror
"""

import re
import subprocess
from pathlib import Path

try:
    from loguru import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)  # type: ignore


def search_by_name(root_path: Path, query: str) -> list[Path]:
    """
    Busca archivos por nombre usando find.

    Args:
        root_path: Directorio raíz de búsqueda
        query: Patrón de búsqueda

    Returns:
        Lista de paths que coinciden (max 100)
    """
    try:
        result = subprocess.run(
            ["find", str(root_path), "-name", f"*{query}*", "-not", "-path", "*/.*"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        paths = []
        for line in result.stdout.strip().split("\n"):
            if line:
                path = Path(line)
                if path.exists() and path != root_path:
                    paths.append(path)
        return paths[:100]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def search_by_regex(root_path: Path, query: str) -> list[Path]:
    """
    Busca archivos por patrón regex.

    Args:
        root_path: Directorio raíz de búsqueda
        query: Expresión regular

    Returns:
        Lista de paths que coinciden (max 100)
    """
    try:
        pattern = re.compile(query, re.IGNORECASE)
    except re.error:
        return []

    results = []
    try:
        for path in root_path.rglob("*"):
            if path.name.startswith("."):
                continue
            if pattern.search(path.name):
                results.append(path)
            if len(results) >= 100:
                break
    except (PermissionError, OSError) as e:
        logger.debug(f"Permission error during regex search: {e}")
    return results


def search_by_content(root_path: Path, query: str) -> list[Path]:
    """
    Busca en contenido de archivos usando grep.

    Args:
        root_path: Directorio raíz de búsqueda
        query: Texto a buscar

    Returns:
        Lista de paths que contienen el texto (max 100)
    """
    try:
        result = subprocess.run(
            ["grep", "-r", "-l", "-i", "--include=*", query, str(root_path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        paths = []
        for line in result.stdout.strip().split("\n"):
            if line:
                path = Path(line)
                if path.exists() and not any(p.startswith(".") for p in path.parts):
                    paths.append(path)
        return paths[:100]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []
