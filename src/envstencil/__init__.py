"""envstencil — gera um .env.example seguro a partir do seu .env."""

from .core import (
    DEFAULT_PLACEHOLDER,
    AppendResult,
    append_missing_variables,
    generate_example,
    parse_env_file,
    render_stencil,
)

__version__ = "0.2.0"

__all__ = [
    "DEFAULT_PLACEHOLDER",
    "AppendResult",
    "append_missing_variables",
    "generate_example",
    "parse_env_file",
    "render_stencil",
]
