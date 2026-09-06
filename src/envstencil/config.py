"""Internal configuration model and source discovery for envstencil.

The model (dataclasses, defaults, parsing, merge), the discovery layer
(`load_config` and friends) and per-command resolution
(`resolve_check_config` / `resolve_generate_config`) all live here. The
`--config` option is parsed by the CLI and feeds `load_config`, but the
existing commands do **not** yet act on the resolved configuration.

Every configurable field is `... | None`: `None` means "not set at this
layer" and is what `merge_config` uses to decide whether an override wins.
`False` is a real, explicit value and never behaves like `None`.

Effective config is built layer by layer, lowest precedence first:
built-in defaults → user global config → `pyproject.toml` `[tool.envstencil]`
→ `<cwd>/.envstencil.toml` → `--config` file (when given).
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field, fields, replace
from pathlib import Path
from typing import Any

USER_CONFIG_DIRNAME = "envstencil"
USER_CONFIG_FILENAME = "config.toml"
PROJECT_CONFIG_FILENAME = ".envstencil.toml"
PYPROJECT_FILENAME = "pyproject.toml"


class ConfigError(ValueError):
    """Raised when a configuration file has an invalid value or type."""


@dataclass
class GlobalConfig:
    """`[global]` section — defaults shared by every command."""

    file1: Path | None = None
    file2: Path | None = None


@dataclass
class GenerateConfig:
    """`[generate]` section — may later override `[global]`."""

    file1: Path | None = None
    file2: Path | None = None
    force: bool | None = None


@dataclass
class CheckConfig:
    """`[check]` section — may later override `[global]`."""

    file1: Path | None = None
    file2: Path | None = None
    diff: bool | None = None


@dataclass
class EnvStencilConfig:
    """The whole configuration.

    The attribute for the `[global]` section is `global_` (``global`` is a
    Python keyword).
    """

    global_: GlobalConfig = field(default_factory=GlobalConfig)
    generate: GenerateConfig = field(default_factory=GenerateConfig)
    check: CheckConfig = field(default_factory=CheckConfig)


def default_config() -> EnvStencilConfig:
    """Return a fresh `EnvStencilConfig` holding the tool's built-in defaults.

    A new object every call, so callers and tests can mutate the result
    without affecting anyone else.
    """
    return EnvStencilConfig(
        global_=GlobalConfig(
            file1=Path(".env"),
            file2=Path(".env.example"),
        ),
        generate=GenerateConfig(force=False),
        check=CheckConfig(diff=False),
    )


# --- parsing ---------------------------------------------------------------


def load_toml(path: Path) -> dict[str, Any]:
    """Read `path` as TOML with the standard library and return the raw data.

    Kept separate from `parse_config` so most tests can feed dicts directly.

    A syntax error in the file is re-raised as `ConfigError` (with the
    parser's message and the path). Filesystem errors — `FileNotFoundError`,
    `PermissionError`, `IsADirectoryError`, … — are left to propagate: a file
    that can't be read is a different problem from a file with invalid TOML.
    """
    with path.open("rb") as handle:
        try:
            return tomllib.load(handle)
        except tomllib.TOMLDecodeError as exc:
            raise ConfigError(
                f"Invalid TOML configuration in {path}: {exc}"
            ) from exc


def _as_bool(section: str, key: str, value: Any) -> bool:
    # `isinstance(1, bool)` is False, so ints like `1`/`0` are rejected.
    if not isinstance(value, bool):
        raise ConfigError(
            f"Invalid configuration: {section}.{key} must be a boolean."
        )
    return value


def _as_path(section: str, key: str, value: Any) -> Path:
    if not isinstance(value, str):
        raise ConfigError(
            f"Invalid configuration: {section}.{key} must be a string."
        )
    return Path(value)


def _section_table(section: str, raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ConfigError(
            f"Invalid configuration: [{section}] must be a table."
        )
    return raw


def _reject_unknown_keys(
    section: str, raw: dict[str, Any], allowed: set[str]
) -> None:
    extra = sorted(set(raw) - allowed)
    if extra:
        raise ConfigError(
            f"Invalid configuration: unknown key {section}.{extra[0]}."
        )


def _parse_global(raw: Any) -> GlobalConfig:
    table = _section_table("global", raw)
    _reject_unknown_keys("global", table, {"file1", "file2"})
    return GlobalConfig(
        file1=(
            _as_path("global", "file1", table["file1"])
            if "file1" in table
            else None
        ),
        file2=(
            _as_path("global", "file2", table["file2"])
            if "file2" in table
            else None
        ),
    )


def _parse_generate(raw: Any) -> GenerateConfig:
    table = _section_table("generate", raw)
    _reject_unknown_keys("generate", table, {"file1", "file2", "force"})
    return GenerateConfig(
        file1=(
            _as_path("generate", "file1", table["file1"])
            if "file1" in table
            else None
        ),
        file2=(
            _as_path("generate", "file2", table["file2"])
            if "file2" in table
            else None
        ),
        force=(
            _as_bool("generate", "force", table["force"])
            if "force" in table
            else None
        ),
    )


def _parse_check(raw: Any) -> CheckConfig:
    table = _section_table("check", raw)
    _reject_unknown_keys("check", table, {"file1", "file2", "diff"})
    return CheckConfig(
        file1=(
            _as_path("check", "file1", table["file1"])
            if "file1" in table
            else None
        ),
        file2=(
            _as_path("check", "file2", table["file2"])
            if "file2" in table
            else None
        ),
        diff=(
            _as_bool("check", "diff", table["diff"])
            if "diff" in table
            else None
        ),
    )


def parse_config(data: dict[str, Any]) -> EnvStencilConfig:
    """Build an `EnvStencilConfig` from raw TOML data.

    Only the `[global]`, `[generate]` and `[check]` sections are read; any
    other top-level section is ignored (forward compatibility). An unknown
    key *inside* a known section, or a value of the wrong type, raises
    `ConfigError`. Sections absent from `data` stay all-`None` — defaults are
    a separate concern (`default_config` + `merge_config`).
    """
    config = EnvStencilConfig()
    if "global" in data:
        config.global_ = _parse_global(data["global"])
    if "generate" in data:
        config.generate = _parse_generate(data["generate"])
    if "check" in data:
        config.check = _parse_check(data["check"])
    return config


# --- merge ---------------------------------------------------------------


def _merge_section(base: Any, override: Any) -> Any:
    """Field-by-field merge: a non-`None` override field wins."""
    merged = {}
    for f in fields(base):
        override_value = getattr(override, f.name)
        merged[f.name] = (
            override_value
            if override_value is not None
            else getattr(base, f.name)
        )
    return replace(base, **merged)


def merge_config(
    base: EnvStencilConfig, override: EnvStencilConfig
) -> EnvStencilConfig:
    """Merge `override` onto `base`, field by field.

    A field set to a non-`None` value in `override` replaces the one in
    `base` (including `False`). A `None` field in `override` leaves the base
    value untouched. Neither argument is mutated — a new object is returned.
    """
    return EnvStencilConfig(
        global_=_merge_section(base.global_, override.global_),
        generate=_merge_section(base.generate, override.generate),
        check=_merge_section(base.check, override.check),
    )


# --- source discovery --------------------------------------------------


def get_user_config_path() -> Path:
    """Return the path of the user's global config file (XDG-aware).

    `$XDG_CONFIG_HOME/envstencil/config.toml` when `XDG_CONFIG_HOME` is set
    and non-empty, otherwise `~/.config/envstencil/config.toml`.
    """
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / USER_CONFIG_DIRNAME / USER_CONFIG_FILENAME


def _load_config_file(path: Path) -> EnvStencilConfig:
    """`parse_config(load_toml(path))` if `path` exists, else an empty config.

    Only *non-existence* is treated as "no override at this layer". A path
    that exists but is not a readable file (a directory, no read permission,
    …) is left to `load_toml` / `Path.open`, so the filesystem error
    propagates; invalid TOML or bad values still surface as `ConfigError`.
    """
    if not path.exists():
        return EnvStencilConfig()
    return parse_config(load_toml(path))


def load_user_config() -> EnvStencilConfig:
    """Load the user's global config, or an empty config if it is absent."""
    return _load_config_file(get_user_config_path())


def load_pyproject_config(cwd: Path | None = None) -> EnvStencilConfig:
    """Load `[tool.envstencil]` from `<cwd>/pyproject.toml`.

    Returns an empty config when `pyproject.toml` is missing or has no
    `[tool.envstencil]`. Other tables in the file are ignored. Raises
    `ConfigError` for invalid TOML, invalid values, or a `tool` /
    `tool.envstencil` that is not a table.
    """
    path = (cwd or Path.cwd()) / PYPROJECT_FILENAME
    if not path.exists():
        return EnvStencilConfig()

    data = load_toml(path)
    tool = data.get("tool", {})
    if not isinstance(tool, dict):
        raise ConfigError("Invalid configuration: [tool] must be a table.")
    section = tool.get("envstencil", {})
    if not isinstance(section, dict):
        raise ConfigError(
            "Invalid configuration: [tool.envstencil] must be a table."
        )
    return parse_config(section)


def load_project_config(cwd: Path | None = None) -> EnvStencilConfig:
    """Load `<cwd>/.envstencil.toml`, or an empty config if it is absent.

    No ascending search — only the given directory is looked at.
    """
    path = (cwd or Path.cwd()) / PROJECT_CONFIG_FILENAME
    return _load_config_file(path)


def load_explicit_config(path: Path) -> EnvStencilConfig:
    """Load a config file the user named explicitly (via `--config`).

    Unlike the auto-discovered sources, a missing `path` is **not** silently
    treated as "no config" — the user asked for this file. `load_toml` /
    `Path.open` handle a missing path, a directory or a permission problem
    (those filesystem errors propagate); invalid TOML or invalid values
    surface as `ConfigError`.
    """
    return parse_config(load_toml(path))


def load_config(
    cwd: Path | None = None,
    explicit_config: Path | None = None,
) -> EnvStencilConfig:
    """Build the effective configuration from every source.

    Layers, lowest precedence first: built-in defaults, the user's global
    config, `pyproject.toml` `[tool.envstencil]`, `<cwd>/.envstencil.toml`,
    and finally — when given — the file passed as `explicit_config`
    (`--config`). Merging stays field by field (`merge_config`); no section
    ever replaces another section wholesale, and `explicit_config` is one
    more layer, not a replacement for the rest.

    An absent auto-discovered source contributes an empty config; a source
    that exists but is invalid raises. `explicit_config` additionally raises
    when it does not exist.
    """
    cwd = cwd or Path.cwd()
    config = default_config()
    config = merge_config(config, load_user_config())
    config = merge_config(config, load_pyproject_config(cwd))
    config = merge_config(config, load_project_config(cwd))
    if explicit_config is not None:
        config = merge_config(config, load_explicit_config(explicit_config))
    return config


# --- command resolution ----------------------------------------------


@dataclass
class ResolvedCheckConfig:
    """`check` configuration with every value settled (no `None`)."""

    file1: Path
    file2: Path
    diff: bool


@dataclass
class ResolvedGenerateConfig:
    """`generate` configuration with every value settled (no `None`)."""

    file1: Path
    file2: Path
    force: bool


def _resolve(qualified_name: str, *candidates: Any) -> Any:
    """Return the first candidate that is not `None`.

    Explicit `None` checks (never `a or b`) so `False` and empty strings are
    kept. If every candidate is `None` the value cannot be resolved and a
    `ConfigError` is raised, so these functions are safe even on a bare
    `EnvStencilConfig()`.
    """
    for candidate in candidates:
        if candidate is not None:
            return candidate
    raise ConfigError(
        f"Invalid configuration: {qualified_name} could not be resolved."
    )


def resolve_check_config(config: EnvStencilConfig) -> ResolvedCheckConfig:
    """Resolve `[check]` against `[global]`.

    `check.file1` / `check.file2` win over `global.file1` / `global.file2`;
    `diff` comes straight from `check.diff` (the composed config carries it
    thanks to the built-in defaults).
    """
    return ResolvedCheckConfig(
        file1=_resolve(
            "check.file1", config.check.file1, config.global_.file1
        ),
        file2=_resolve(
            "check.file2", config.check.file2, config.global_.file2
        ),
        diff=_resolve("check.diff", config.check.diff),
    )


def resolve_generate_config(
    config: EnvStencilConfig,
) -> ResolvedGenerateConfig:
    """Resolve `[generate]` against `[global]`.

    `generate.file1` / `generate.file2` win over `global.file1` /
    `global.file2`; `force` comes straight from `generate.force`.
    """
    return ResolvedGenerateConfig(
        file1=_resolve(
            "generate.file1", config.generate.file1, config.global_.file1
        ),
        file2=_resolve(
            "generate.file2", config.generate.file2, config.global_.file2
        ),
        force=_resolve("generate.force", config.generate.force),
    )
