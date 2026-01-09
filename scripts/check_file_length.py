#!/usr/bin/env python3
"""
check_file_length.py - Verifica que archivos Python no excedan límite de líneas

Este script es usado por pre-commit y CI para enforcement de la regla de modularidad.
Regla: Máximo 300 líneas por archivo Python (excluyendo __init__.py)

Autor: Homero Thompson del Lago del Terror
"""

import argparse
import sys
from pathlib import Path


def check_file_length(filepath: str, max_lines: int) -> tuple[bool, int]:
    """
    Verifica si un archivo excede el límite de líneas.

    Returns:
        tuple: (passed, line_count)
    """
    path = Path(filepath)

    # Ignorar __init__.py - típicamente son cortos y sirven de re-exports
    if path.name == "__init__.py":
        return True, 0

    # Ignorar si no es .py o no existe
    if path.suffix != ".py" or not path.exists():
        return True, 0

    try:
        lines = len(path.read_text().splitlines())
        return lines <= max_lines, lines
    except Exception:
        return True, 0


def main():
    parser = argparse.ArgumentParser(
        description="Verifica que archivos Python no excedan límite de líneas"
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Archivos a verificar",
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        default=300,
        help="Máximo de líneas permitidas (default: 300)",
    )
    parser.add_argument(
        "--warn-at",
        type=int,
        default=250,
        help="Mostrar advertencia a partir de este número (default: 250)",
    )
    args = parser.parse_args()

    failed = []
    warnings = []

    for filepath in args.files:
        passed, lines = check_file_length(filepath, args.max_lines)
        if not passed:
            failed.append((filepath, lines))
        elif lines > args.warn_at:
            warnings.append((filepath, lines))

    # Mostrar advertencias
    if warnings:
        print(f"⚠️  Archivos acercándose al límite ({args.warn_at}-{args.max_lines} líneas):")
        for f, lines in warnings:
            print(f"   {f}: {lines} líneas")
        print()

    # Mostrar errores
    if failed:
        print(f"❌ Archivos que EXCEDEN {args.max_lines} líneas:")
        for f, lines in failed:
            excess = lines - args.max_lines
            print(f"   {f}: {lines} líneas (+{excess} sobre límite)")

        print()
        print("💡 Sugerencias para resolver:")
        print("   1. Divide el archivo en módulos más pequeños (~200 líneas c/u)")
        print("   2. Extrae clases/funciones relacionadas a archivos separados")
        print("   3. Usa un package (carpeta con __init__.py) para agrupar módulos")
        print()
        print("📚 Ver: ~/.claude/rules/development/python-development.md")
        sys.exit(1)

    if warnings:
        print("✅ Todos los archivos están dentro del límite (con advertencias)")
    else:
        print("✅ Todos los archivos están dentro del límite")
    sys.exit(0)


if __name__ == "__main__":
    main()
