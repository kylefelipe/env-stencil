"""Internal configuration model for envstencil.

Milestone 1: infrastructure only. This module is **not** wired into the CLI,
`pyproject.toml`, `.envstencil.toml`, the user's global config or `--config`
yet — it is the reusable base those integrations will build on.

Every configurable field is `... | None`: `None` means "not set at this
layer" and is what `merge_config` uses to decide whether an override wins.
`False` is a real, explicit value and never behaves like `None`.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field, fields, replace
from pathlib import Path
from typing import Any


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
    """
    with open(path, "rb") as handle:
        return tomllib.load(handle)


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
