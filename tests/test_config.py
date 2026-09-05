from pathlib import Path

import pytest

from envstencil.config import (
    CheckConfig,
    ConfigError,
    EnvStencilConfig,
    GenerateConfig,
    GlobalConfig,
    default_config,
    load_toml,
    merge_config,
    parse_config,
)

# --- defaults -----------------------------------------------------------


def test_default_config_values() -> None:
    cfg = default_config()

    assert cfg.global_.file1 == Path(".env")
    assert cfg.global_.file2 == Path(".env.example")
    assert cfg.generate.force is False
    assert cfg.check.diff is False
    # not part of the documented defaults
    assert cfg.generate.file1 is None
    assert cfg.check.file1 is None


def test_default_config_returns_independent_objects() -> None:
    a = default_config()
    b = default_config()

    a.check.diff = True
    a.global_.file1 = Path("mutated")

    assert b.check.diff is False
    assert b.global_.file1 == Path(".env")
    assert a is not b
    assert a.check is not b.check


# --- parsing ----------------------------------------------------------


def test_parse_empty_config_is_all_none() -> None:
    cfg = parse_config({})

    assert isinstance(cfg, EnvStencilConfig)
    assert cfg.global_ == GlobalConfig()
    assert cfg.generate == GenerateConfig()
    assert cfg.check == CheckConfig()


def test_parse_global_section() -> None:
    cfg = parse_config(
        {"global": {"file1": ".env.local", "file2": ".env.sample"}}
    )

    assert cfg.global_.file1 == Path(".env.local")
    assert cfg.global_.file2 == Path(".env.sample")
    assert isinstance(cfg.global_.file1, Path)
    assert cfg.generate == GenerateConfig()
    assert cfg.check == CheckConfig()


def test_parse_generate_section() -> None:
    cfg = parse_config(
        {"generate": {"file1": "a", "file2": "b", "force": True}}
    )

    assert cfg.generate == GenerateConfig(
        file1=Path("a"), file2=Path("b"), force=True
    )


def test_parse_check_section() -> None:
    cfg = parse_config({"check": {"file1": "a", "file2": "b", "diff": False}})

    assert cfg.check == CheckConfig(
        file1=Path("a"), file2=Path("b"), diff=False
    )
    # diff=False must survive parsing, not become None
    assert cfg.check.diff is False


def test_parse_partial_sections() -> None:
    cfg = parse_config({"global": {"file1": ".env"}, "check": {"diff": True}})

    assert cfg.global_.file1 == Path(".env")
    assert cfg.global_.file2 is None
    assert cfg.check.diff is True
    assert cfg.generate == GenerateConfig()


def test_parse_ignores_unknown_top_level_section() -> None:
    cfg = parse_config({"sync": {"whatever": 1}, "check": {"diff": True}})

    assert cfg.check.diff is True


def test_parse_partial_keys_leave_others_none() -> None:
    cfg = parse_config({"generate": {"force": True}})

    assert cfg.generate.force is True
    assert cfg.generate.file1 is None
    assert cfg.generate.file2 is None


# --- validation -----------------------------------------------------


def test_parse_rejects_string_boolean() -> None:
    with pytest.raises(ConfigError) as excinfo:
        parse_config({"check": {"diff": "true"}})

    assert "check.diff" in str(excinfo.value)
    assert "boolean" in str(excinfo.value)


def test_parse_rejects_int_boolean() -> None:
    with pytest.raises(ConfigError) as excinfo:
        parse_config({"generate": {"force": 1}})

    assert "generate.force" in str(excinfo.value)


def test_parse_rejects_non_string_path() -> None:
    with pytest.raises(ConfigError) as excinfo:
        parse_config({"global": {"file1": False}})

    assert "global.file1" in str(excinfo.value)
    assert "string" in str(excinfo.value)


def test_parse_rejects_unknown_key_in_known_section() -> None:
    with pytest.raises(ConfigError) as excinfo:
        parse_config({"check": {"dif": True}})

    assert "check.dif" in str(excinfo.value)


def test_parse_rejects_non_table_section() -> None:
    with pytest.raises(ConfigError):
        parse_config({"global": "not a table"})


# --- load_toml ----------------------------------------------------


def test_load_toml_reads_file(tmp_path: Path) -> None:
    path = tmp_path / "cfg.toml"
    path.write_text(
        "[global]\nfile1 = '.env'\n\n[check]\ndiff = true\n",
        encoding="utf-8",
    )

    data = load_toml(path)
    cfg = parse_config(data)

    assert data == {"global": {"file1": ".env"}, "check": {"diff": True}}
    assert cfg.global_.file1 == Path(".env")
    assert cfg.check.diff is True


# --- merge -----------------------------------------------------


def test_merge_override_replaces_simple_value() -> None:
    base = parse_config({"global": {"file1": ".env", "file2": ".env.example"}})
    override = parse_config({"global": {"file1": ".env.local"}})

    result = merge_config(base, override)

    assert result.global_.file1 == Path(".env.local")
    assert result.global_.file2 == Path(".env.example")


def test_merge_is_field_by_field_across_sections() -> None:
    base = parse_config(
        {
            "global": {"file1": ".env", "file2": ".env.example"},
            "check": {"diff": True},
        }
    )
    override = parse_config({"global": {"file1": ".env.local"}})

    result = merge_config(base, override)

    assert result.global_.file1 == Path(".env.local")
    assert result.global_.file2 == Path(".env.example")
    assert result.check.diff is True


def test_merge_none_override_keeps_base() -> None:
    base = parse_config({"check": {"diff": True}})
    override = EnvStencilConfig()  # everything None

    assert merge_config(base, override).check.diff is True


def test_merge_false_override_replaces_true() -> None:
    base = parse_config({"check": {"diff": True}})
    override = parse_config({"check": {"diff": False}})

    assert merge_config(base, override).check.diff is False


def test_merge_does_not_mutate_inputs() -> None:
    base = parse_config({"global": {"file1": ".env"}, "check": {"diff": True}})
    override = parse_config({"global": {"file1": ".env.local"}})

    merge_config(base, override)

    assert base.global_.file1 == Path(".env")
    assert base.check.diff is True
    assert override.global_.file1 == Path(".env.local")
    assert override.check.diff is None


def test_merge_with_defaults_as_base() -> None:
    result = merge_config(
        default_config(), parse_config({"check": {"diff": True}})
    )

    assert result.global_.file1 == Path(".env")
    assert result.generate.force is False
    assert result.check.diff is True
