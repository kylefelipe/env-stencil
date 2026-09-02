"""envstencil — gera um .env.example seguro a partir do seu .env."""

from .core import (
    DEFAULT_PLACEHOLDER,
    AppendResult,
    EnvComparison,
    append_missing_variables,
    compare_env_files,
    generate_example,
    parse_env_file,
    render_stencil,
)

__version__ = "0.2.0"

__all__ = [
    "DEFAULT_PLACEHOLDER",
    "AppendResult",
    "EnvComparison",
    "append_missing_variables",
    "compare_env_files",
    "generate_example",
    "parse_env_file",
    "render_stencil",
]
