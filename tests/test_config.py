import tomllib
from pathlib import Path

import pytest

from envstencil.config import (
    CheckConfig,
    ConfigError,
    EnvStencilConfig,
    GenerateConfig,
    GlobalConfig,
    default_config,
    get_user_config_path,
    load_config,
    load_project_config,
    load_pyproject_config,
    load_toml,
    load_user_config,
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


def test_load_toml_invalid_syntax_raises_config_error(tmp_path: Path) -> None:
    path = tmp_path / "broken.toml"
    path.write_text("[check\ndiff = true\n", encoding="utf-8")

    with pytest.raises(ConfigError) as excinfo:
        load_toml(path)

    assert "broken.toml" in str(excinfo.value)
    assert isinstance(excinfo.value.__cause__, tomllib.TOMLDecodeError)


def test_load_toml_missing_file_propagates_filesystem_error(
    tmp_path: Path,
) -> None:
    with pytest.raises(FileNotFoundError):
        load_toml(tmp_path / "nao-existe.toml")


def test_load_toml_directory_propagates_filesystem_error(
    tmp_path: Path,
) -> None:
    with pytest.raises((IsADirectoryError, PermissionError)):
        load_toml(tmp_path)


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


# --- get_user_config_path -----------------------------------------


def test_user_config_path_uses_xdg_config_home(monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", "/tmp/xdg-config")

    assert get_user_config_path() == Path(
        "/tmp/xdg-config/envstencil/config.toml"
    )


def test_user_config_path_falls_back_to_dot_config(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")

    assert get_user_config_path() == (
        tmp_path / "home" / ".config" / "envstencil" / "config.toml"
    )


def test_user_config_path_empty_xdg_falls_back(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", "")
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")

    assert get_user_config_path() == (
        tmp_path / "home" / ".config" / "envstencil" / "config.toml"
    )


# --- load_user_config -----------------------------------------


def _write_user_config(tmp_path: Path, monkeypatch, content: str) -> Path:
    """Point XDG at a tmp dir and write the global config file there."""
    xdg = tmp_path / "xdg"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    path = xdg / "envstencil" / "config.toml"
    path.parent.mkdir(parents=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_load_user_config_missing_is_empty(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

    assert load_user_config() == EnvStencilConfig()


def test_load_user_config_reads_valid_file(
    tmp_path: Path, monkeypatch
) -> None:
    _write_user_config(
        tmp_path,
        monkeypatch,
        "[global]\nfile1 = '.env'\n\n[check]\ndiff = true\n",
    )

    cfg = load_user_config()

    assert cfg.global_.file1 == Path(".env")
    assert cfg.check.diff is True


def test_load_user_config_invalid_toml_raises(
    tmp_path: Path, monkeypatch
) -> None:
    _write_user_config(tmp_path, monkeypatch, "[global\nfile1 = '.env'\n")

    with pytest.raises(ConfigError):
        load_user_config()


def test_load_user_config_invalid_type_raises(
    tmp_path: Path, monkeypatch
) -> None:
    _write_user_config(tmp_path, monkeypatch, "[check]\ndiff = 'sim'\n")

    with pytest.raises(ConfigError):
        load_user_config()


# --- load_pyproject_config --------------------------------------


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_load_pyproject_missing_is_empty(tmp_path: Path) -> None:
    assert load_pyproject_config(tmp_path) == EnvStencilConfig()


def test_load_pyproject_without_tool_section_is_empty(tmp_path: Path) -> None:
    _write(
        tmp_path / "pyproject.toml",
        "[project]\nname = 'x'\n\n[tool.black]\nline-length = 79\n",
    )

    assert load_pyproject_config(tmp_path) == EnvStencilConfig()


def test_load_pyproject_reads_global(tmp_path: Path) -> None:
    _write(
        tmp_path / "pyproject.toml",
        "[tool.envstencil.global]\nfile1 = '.env'\nfile2 = '.env.example'\n",
    )

    cfg = load_pyproject_config(tmp_path)

    assert cfg.global_.file1 == Path(".env")
    assert cfg.global_.file2 == Path(".env.example")


def test_load_pyproject_reads_generate(tmp_path: Path) -> None:
    _write(
        tmp_path / "pyproject.toml",
        "[tool.envstencil.generate]\nforce = true\n",
    )

    assert load_pyproject_config(tmp_path).generate.force is True


def test_load_pyproject_reads_check(tmp_path: Path) -> None:
    _write(
        tmp_path / "pyproject.toml",
        "[tool.envstencil.check]\ndiff = true\n",
    )

    assert load_pyproject_config(tmp_path).check.diff is True


def test_load_pyproject_ignores_other_tables(tmp_path: Path) -> None:
    _write(
        tmp_path / "pyproject.toml",
        "[project]\nname = 'x'\n\n[tool.isort]\nprofile = 'black'\n\n"
        "[tool.envstencil.check]\ndiff = true\n",
    )

    assert load_pyproject_config(tmp_path).check.diff is True


def test_load_pyproject_tool_not_a_table_raises(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", "tool = 'foo'\n")

    with pytest.raises(ConfigError) as excinfo:
        load_pyproject_config(tmp_path)

    assert "tool" in str(excinfo.value)


def test_load_pyproject_envstencil_not_a_table_raises(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", "[tool]\nenvstencil = 'foo'\n")

    with pytest.raises(ConfigError) as excinfo:
        load_pyproject_config(tmp_path)

    assert "tool.envstencil" in str(excinfo.value)


def test_load_pyproject_invalid_toml_raises(tmp_path: Path) -> None:
    _write(
        tmp_path / "pyproject.toml", "[tool.envstencil.check\ndiff = true\n"
    )

    with pytest.raises(ConfigError):
        load_pyproject_config(tmp_path)


# --- load_project_config -------------------------------------


def test_load_project_config_missing_is_empty(tmp_path: Path) -> None:
    assert load_project_config(tmp_path) == EnvStencilConfig()


def test_load_project_config_reads_valid_file(tmp_path: Path) -> None:
    _write(
        tmp_path / ".envstencil.toml",
        "[global]\nfile1 = '.env.ci'\n\n[check]\ndiff = false\n",
    )

    cfg = load_project_config(tmp_path)

    assert cfg.global_.file1 == Path(".env.ci")
    assert cfg.check.diff is False


def test_load_project_config_invalid_toml_raises(tmp_path: Path) -> None:
    _write(tmp_path / ".envstencil.toml", "[check\ndiff = true\n")

    with pytest.raises(ConfigError):
        load_project_config(tmp_path)


# --- load_config (composition / precedence) ----------------


def test_load_config_no_sources_equals_defaults(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

    assert load_config(tmp_path) == default_config()


def test_load_config_precedence_example_from_spec(
    tmp_path: Path, monkeypatch
) -> None:
    _write_user_config(
        tmp_path,
        monkeypatch,
        "[global]\nfile1 = '.env'\nfile2 = '.env.example'\n\n"
        "[check]\ndiff = true\n",
    )
    _write(
        tmp_path / "pyproject.toml",
        "[tool.envstencil.global]\nfile1 = '.env.local'\n",
    )
    _write(tmp_path / ".envstencil.toml", "[check]\ndiff = false\n")

    cfg = load_config(tmp_path)

    assert cfg.global_.file1 == Path(".env.local")
    assert cfg.global_.file2 == Path(".env.example")
    assert cfg.check.diff is False


def test_load_config_project_wins_over_pyproject_and_user(
    tmp_path: Path, monkeypatch
) -> None:
    _write_user_config(tmp_path, monkeypatch, "[check]\ndiff = true\n")
    # pyproject does not define diff
    _write(
        tmp_path / "pyproject.toml",
        "[tool.envstencil.global]\nfile1 = '.env'\n",
    )
    _write(tmp_path / ".envstencil.toml", "[check]\ndiff = false\n")

    assert load_config(tmp_path).check.diff is False


def test_load_config_partial_merge_across_sources(
    tmp_path: Path, monkeypatch
) -> None:
    _write_user_config(
        tmp_path,
        monkeypatch,
        "[global]\nfile1 = 'A'\nfile2 = 'B'\n",
    )
    _write(
        tmp_path / "pyproject.toml",
        "[tool.envstencil.global]\nfile1 = 'C'\n",
    )
    _write(tmp_path / ".envstencil.toml", "[check]\ndiff = true\n")

    cfg = load_config(tmp_path)

    assert cfg.global_.file1 == Path("C")
    assert cfg.global_.file2 == Path("B")
    assert cfg.check.diff is True


def test_load_config_keeps_defaults_when_layer_silent(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    _write(tmp_path / ".envstencil.toml", "[check]\ndiff = true\n")

    cfg = load_config(tmp_path)

    assert cfg.global_.file1 == Path(".env")  # from defaults
    assert cfg.generate.force is False  # from defaults
    assert cfg.check.diff is True  # from .envstencil.toml


# --- existing-but-invalid path is not "absent" -----------------


def test_load_user_config_directory_propagates_filesystem_error(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    (tmp_path / "xdg" / "envstencil" / "config.toml").mkdir(parents=True)

    with pytest.raises((IsADirectoryError, PermissionError)):
        load_user_config()


def test_load_project_config_directory_propagates_filesystem_error(
    tmp_path: Path,
) -> None:
    (tmp_path / ".envstencil.toml").mkdir()

    with pytest.raises((IsADirectoryError, PermissionError)):
        load_project_config(tmp_path)


def test_load_pyproject_config_directory_propagates_filesystem_error(
    tmp_path: Path,
) -> None:
    (tmp_path / "pyproject.toml").mkdir()

    with pytest.raises((IsADirectoryError, PermissionError)):
        load_pyproject_config(tmp_path)
