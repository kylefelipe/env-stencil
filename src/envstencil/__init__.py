"""envstencil — gera um .env.example seguro a partir do seu .env."""

from .core import (
    DEFAULT_PLACEHOLDER,
    generate_example,
    parse_env_file,
    render_stencil,
)

__version__ = "0.1.0"

__all__ = [
    "DEFAULT_PLACEHOLDER",
    "generate_example",
    "parse_env_file",
    "render_stencil",
]
