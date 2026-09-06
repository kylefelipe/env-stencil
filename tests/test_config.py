import tomllib
from pathlib import Path

import pytest

from envstencil.config import (
    CheckConfig,
    ConfigError,
    EnvStencilConfig,
    GenerateBehaviour,
    GenerateConfig,
    GlobalConfig,
    ResolvedCheckConfig,
    ResolvedGenerateConfig,
    _find_upwards,
    default_config,
    get_user_config_path,
    load_config,
    load_project_config,
    load_pyproject_config,
    load_toml,
    load_user_config,
    merge_config,
    parse_config,
    resolve_check_config,
    resolve_generate_config,
)

# --- defaults -----------------------------------------------------------


def test_default_config_values() -> None:
    cfg = default_config()

    assert cfg.global_.file1 == Path(".env")
    assert cfg.global_.file2 == Path(".env.example")
    assert cfg.generate.behaviour is GenerateBehaviour.FAIL
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
        {"generate": {"file1": "a", "file2": "b", "behaviour": "force"}}
    )

    assert cfg.generate == GenerateConfig(
        file1=Path("a"), file2=Path("b"), behaviour=GenerateBehaviour.FORCE
    )


def test_parse_generate_behaviour_values() -> None:
    for raw, expected in (
        ("fail", GenerateBehaviour.FAIL),
        ("force", GenerateBehaviour.FORCE),
        ("append", GenerateBehaviour.APPEND),
    ):
        cfg = parse_config({"generate": {"behaviour": raw}})
        assert cfg.generate.behaviour is expected


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
    cfg = parse_config({"generate": {"behaviour": "force"}})

    assert cfg.generate.behaviour is GenerateBehaviour.FORCE
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
        parse_config({"generate": {"behaviour": 1}})

    assert "generate.behaviour" in str(excinfo.value)
    assert "string" in str(excinfo.value)


def test_parse_rejects_bool_behaviour() -> None:
    with pytest.raises(ConfigError) as excinfo:
        parse_config({"generate": {"behaviour": True}})

    assert "generate.behaviour" in str(excinfo.value)
    assert "string" in str(excinfo.value)


def test_parse_rejects_unknown_behaviour_value() -> None:
    with pytest.raises(ConfigError) as excinfo:
        parse_config({"generate": {"behaviour": "banana"}})

    msg = str(excinfo.value)
    assert "generate.behaviour" in msg
    assert "fail" in msg and "force" in msg and "append" in msg


def test_parse_rejects_legacy_force_key() -> None:
    with pytest.raises(ConfigError) as excinfo:
        parse_config({"generate": {"force": True}})

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


def test_merge_behaviour_override_replaces_lower_layer() -> None:
    for base_val, over_val in (
        ("fail", "force"),
        ("force", "append"),
        ("append", "fail"),
    ):
        base = parse_config({"generate": {"behaviour": base_val}})
        override = parse_config({"generate": {"behaviour": over_val}})

        merged = merge_config(base, override)

        assert merged.generate.behaviour is GenerateBehaviour(over_val)


def test_merge_none_behaviour_keeps_base() -> None:
    base = parse_config({"generate": {"behaviour": "append"}})
    override = EnvStencilConfig()  # behaviour is None

    assert (
        merge_config(base, override).generate.behaviour
        is GenerateBehaviour.APPEND
    )


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
    assert result.generate.behaviour is GenerateBehaviour.FAIL
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
        '[tool.envstencil.generate]\nbehaviour = "force"\n',
    )

    assert (
        load_pyproject_config(tmp_path).generate.behaviour
        is GenerateBehaviour.FORCE
    )


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
    assert cfg.generate.behaviour is GenerateBehaviour.FAIL  # from defaults
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


# --- load_config with explicit --config -----------------------


def _write_ci(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "ci.toml"
    path.write_text(content, encoding="utf-8")
    return path


def test_load_config_without_explicit_is_unchanged(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    _write(tmp_path / ".envstencil.toml", "[check]\ndiff = true\n")

    assert load_config(tmp_path) == load_config(tmp_path, explicit_config=None)
    assert load_config(tmp_path).check.diff is True


def test_explicit_config_is_applied_last(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    _write(tmp_path / ".envstencil.toml", "[check]\ndiff = true\n")
    ci = _write_ci(tmp_path, "[check]\ndiff = false\n")

    assert load_config(tmp_path, explicit_config=ci).check.diff is False


def test_explicit_config_partial_merge(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    _write(
        tmp_path / ".envstencil.toml",
        "[global]\nfile1 = '.env'\nfile2 = '.env.example'\n",
    )
    ci = _write_ci(tmp_path, "[global]\nfile1 = '.env.ci'\n")

    cfg = load_config(tmp_path, explicit_config=ci)

    assert cfg.global_.file1 == Path(".env.ci")
    assert cfg.global_.file2 == Path(".env.example")


def test_explicit_config_overrides_project(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    _write(tmp_path / ".envstencil.toml", "[global]\nfile1 = '.env.project'\n")
    ci = _write_ci(tmp_path, "[global]\nfile1 = '.env.ci'\n")

    assert load_config(tmp_path, explicit_config=ci).global_.file1 == Path(
        ".env.ci"
    )


def test_explicit_config_overrides_pyproject(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    _write(
        tmp_path / "pyproject.toml",
        "[tool.envstencil.global]\nfile1 = '.env.pyproject'\n",
    )
    ci = _write_ci(tmp_path, "[global]\nfile1 = '.env.ci'\n")

    assert load_config(tmp_path, explicit_config=ci).global_.file1 == Path(
        ".env.ci"
    )


def test_explicit_config_overrides_user(tmp_path: Path, monkeypatch) -> None:
    _write_user_config(
        tmp_path, monkeypatch, "[global]\nfile1 = '.env.user'\n"
    )
    ci = _write_ci(tmp_path, "[global]\nfile1 = '.env.ci'\n")

    assert load_config(tmp_path, explicit_config=ci).global_.file1 == Path(
        ".env.ci"
    )


def test_explicit_config_missing_raises(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

    with pytest.raises(FileNotFoundError):
        load_config(tmp_path, explicit_config=tmp_path / "nao-existe.toml")


def test_explicit_config_directory_raises_filesystem_error(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    (tmp_path / "asdir.toml").mkdir()

    with pytest.raises((IsADirectoryError, PermissionError)):
        load_config(tmp_path, explicit_config=tmp_path / "asdir.toml")


def test_explicit_config_invalid_toml_raises(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    ci = _write_ci(tmp_path, "[check\ndiff = true\n")

    with pytest.raises(ConfigError):
        load_config(tmp_path, explicit_config=ci)


def test_explicit_config_invalid_type_raises(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    ci = _write_ci(tmp_path, "[check]\ndiff = 'sim'\n")

    with pytest.raises(ConfigError):
        load_config(tmp_path, explicit_config=ci)


def test_explicit_config_is_a_layer_not_a_replacement(
    tmp_path: Path, monkeypatch
) -> None:
    _write_user_config(
        tmp_path,
        monkeypatch,
        "[global]\nfile1 = '.env'\nfile2 = '.env.example'\n",
    )
    _write(
        tmp_path / "pyproject.toml",
        '[tool.envstencil.generate]\nbehaviour = "force"\n',
    )
    ci = _write_ci(tmp_path, "[check]\ndiff = true\n")

    cfg = load_config(tmp_path, explicit_config=ci)

    assert cfg.global_.file1 == Path(".env")  # inherited from user
    assert (
        cfg.generate.behaviour is GenerateBehaviour.FORCE
    )  # inherited from pyproject
    assert cfg.check.diff is True  # from ci.toml


def test_load_config_full_precedence_example_from_spec(
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
    _write(
        tmp_path / ".envstencil.toml",
        '[generate]\nbehaviour = "force"\n',
    )
    ci = _write_ci(
        tmp_path,
        "[global]\nfile1 = '.env.ci'\nfile2 = '.env.ci.example'\n\n"
        "[check]\ndiff = false\n",
    )

    cfg = load_config(tmp_path, explicit_config=ci)

    assert cfg.global_.file1 == Path(".env.ci")
    assert cfg.global_.file2 == Path(".env.ci.example")
    assert cfg.generate.behaviour is GenerateBehaviour.FORCE
    assert cfg.check.diff is False


# --- resolve_check_config -----------------------------------


def test_resolve_check_inherits_global_files() -> None:
    cfg = merge_config(
        default_config(),
        parse_config(
            {
                "global": {"file1": ".env", "file2": ".env.example"},
                "check": {"diff": True},
            }
        ),
    )

    resolved = resolve_check_config(cfg)

    assert resolved == ResolvedCheckConfig(
        file1=Path(".env"), file2=Path(".env.example"), diff=True
    )


def test_resolve_check_file1_overrides_global() -> None:
    cfg = parse_config(
        {
            "global": {"file1": ".env", "file2": ".env.example"},
            "check": {"file1": ".env.production", "diff": False},
        }
    )

    resolved = resolve_check_config(cfg)

    assert resolved.file1 == Path(".env.production")
    assert resolved.file2 == Path(".env.example")
    assert resolved.diff is False


def test_resolve_check_file2_overrides_global() -> None:
    cfg = parse_config(
        {
            "global": {"file1": ".env", "file2": ".env.example"},
            "check": {"file2": ".env.prod.example", "diff": True},
        }
    )

    assert resolve_check_config(cfg).file2 == Path(".env.prod.example")
    assert resolve_check_config(cfg).file1 == Path(".env")


def test_resolve_check_both_overridden() -> None:
    cfg = parse_config(
        {
            "global": {"file1": ".env", "file2": ".env.example"},
            "check": {
                "file1": ".env.production",
                "file2": ".env.production.example",
                "diff": True,
            },
        }
    )

    resolved = resolve_check_config(cfg)

    assert resolved.file1 == Path(".env.production")
    assert resolved.file2 == Path(".env.production.example")


def test_resolve_check_diff_true_and_false_preserved() -> None:
    base = {"global": {"file1": ".env", "file2": ".env.example"}}

    assert (
        resolve_check_config(
            parse_config({**base, "check": {"diff": True}})
        ).diff
        is True
    )
    assert (
        resolve_check_config(
            parse_config({**base, "check": {"diff": False}})
        ).diff
        is False
    )


def test_resolve_check_unresolvable_raises() -> None:
    with pytest.raises(ConfigError) as excinfo:
        resolve_check_config(EnvStencilConfig())

    assert "check.file1" in str(excinfo.value)
    assert "could not be resolved" in str(excinfo.value)


def test_resolve_check_unresolvable_diff_raises() -> None:
    cfg = parse_config({"global": {"file1": ".env", "file2": ".env.example"}})

    with pytest.raises(ConfigError) as excinfo:
        resolve_check_config(cfg)

    assert "check.diff" in str(excinfo.value)


# --- resolve_generate_config ------------------------------


def test_resolve_generate_inherits_global_files() -> None:
    cfg = merge_config(
        default_config(),
        parse_config({"global": {"file1": ".env", "file2": ".env.example"}}),
    )

    resolved = resolve_generate_config(cfg)

    assert resolved == ResolvedGenerateConfig(
        file1=Path(".env"),
        file2=Path(".env.example"),
        behaviour=GenerateBehaviour.FAIL,
    )


def test_resolve_generate_file1_overrides_global() -> None:
    cfg = parse_config(
        {
            "global": {"file1": ".env", "file2": ".env.example"},
            "generate": {"file1": ".env.prod", "behaviour": "fail"},
        }
    )

    resolved = resolve_generate_config(cfg)

    assert resolved.file1 == Path(".env.prod")
    assert resolved.file2 == Path(".env.example")


def test_resolve_generate_file2_overrides_global() -> None:
    cfg = parse_config(
        {
            "global": {"file1": ".env", "file2": ".env.example"},
            "generate": {
                "file2": ".env.prod.example",
                "behaviour": "force",
            },
        }
    )

    assert resolve_generate_config(cfg).file2 == Path(".env.prod.example")


def test_resolve_generate_behaviour_values_preserved() -> None:
    base = {"global": {"file1": ".env", "file2": ".env.example"}}

    for value in ("fail", "force", "append"):
        resolved = resolve_generate_config(
            parse_config({**base, "generate": {"behaviour": value}})
        )
        assert resolved.behaviour is GenerateBehaviour(value)


def test_resolve_generate_unresolvable_raises() -> None:
    with pytest.raises(ConfigError) as excinfo:
        resolve_generate_config(EnvStencilConfig())

    assert "generate.file1" in str(excinfo.value)


def test_resolve_generate_unresolvable_behaviour_raises() -> None:
    cfg = parse_config({"global": {"file1": ".env", "file2": ".env.example"}})

    with pytest.raises(ConfigError) as excinfo:
        resolve_generate_config(cfg)

    assert "generate.behaviour" in str(excinfo.value)


def test_resolve_generate_from_defaults_is_complete() -> None:
    resolved = resolve_generate_config(default_config())

    assert resolved == ResolvedGenerateConfig(
        file1=Path(".env"),
        file2=Path(".env.example"),
        behaviour=GenerateBehaviour.FAIL,
    )


# --- _find_upwards (milestone 5) ------------------------------


def _mkdirs(base: Path, *parts: str) -> Path:
    """Create `base/parts...` and return the deepest directory."""
    path = base.joinpath(*parts)
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_find_upwards_file_in_cwd(tmp_path: Path) -> None:
    project = _mkdirs(tmp_path, "project")
    target = _write(project / ".envstencil.toml", "")

    assert _find_upwards(".envstencil.toml", project) == target


def test_find_upwards_file_in_parent(tmp_path: Path) -> None:
    project = _mkdirs(tmp_path, "project")
    src = _mkdirs(project, "src")
    target = _write(project / ".envstencil.toml", "")

    assert _find_upwards(".envstencil.toml", src) == target


def test_find_upwards_file_in_distant_ancestor(tmp_path: Path) -> None:
    project = _mkdirs(tmp_path, "project")
    module = _mkdirs(project, "src", "package", "module")
    target = _write(project / "pyproject.toml", "")

    assert _find_upwards("pyproject.toml", module) == target


def test_find_upwards_returns_none_when_absent(tmp_path: Path) -> None:
    start = _mkdirs(tmp_path, "a", "b", "c")

    assert _find_upwards(".envstencil.toml", start) is None


def test_find_upwards_uses_closest_occurrence(tmp_path: Path) -> None:
    project = _mkdirs(tmp_path, "project")
    app = _mkdirs(project, "app")
    src = _mkdirs(app, "src")
    _write(project / ".envstencil.toml", "")
    closest = _write(app / ".envstencil.toml", "")

    assert _find_upwards(".envstencil.toml", src) == closest


def test_find_upwards_stops_at_root_without_looping(tmp_path: Path) -> None:
    # A name that never exists must terminate at the filesystem root.
    assert _find_upwards("definitely-not-here.toml", tmp_path) is None


def test_find_upwards_stops_at_existing_directory_candidate(
    tmp_path: Path,
) -> None:
    project = _mkdirs(tmp_path, "project")
    src = _mkdirs(project, "src")
    # closest ".envstencil.toml" is a directory; an ancestor has a real file
    _mkdirs(src, ".envstencil.toml")
    _write(project / ".envstencil.toml", "")

    found = _find_upwards(".envstencil.toml", src)

    assert found == src / ".envstencil.toml"
    assert found.is_dir()


# --- independent upward discovery (milestone 5) --------------


def test_pyproject_and_project_config_discovered_independently(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    workspace = _mkdirs(tmp_path, "workspace")
    project = _mkdirs(workspace, "project")
    src = _mkdirs(project, "src")
    _write(
        workspace / "pyproject.toml",
        "[tool.envstencil.global]\nfile1 = '.env.pp'\n",
    )
    _write(project / ".envstencil.toml", "[global]\nfile2 = '.env.proj'\n")

    pp = load_pyproject_config(src)
    proj = load_project_config(src)

    assert pp.global_.file1 == Path(".env.pp")
    assert proj.global_.file2 == Path(".env.proj")


def test_load_pyproject_finds_ancestor(tmp_path: Path) -> None:
    project = _mkdirs(tmp_path, "project")
    deep = _mkdirs(project, "a", "b")
    _write(
        project / "pyproject.toml",
        "[tool.envstencil.check]\ndiff = true\n",
    )

    assert load_pyproject_config(deep).check.diff is True


def test_load_project_config_finds_ancestor(tmp_path: Path) -> None:
    project = _mkdirs(tmp_path, "project")
    deep = _mkdirs(project, "a", "b")
    _write(project / ".envstencil.toml", "[check]\ndiff = true\n")

    assert load_project_config(deep).check.diff is True


def test_load_project_config_uses_closest_ancestor(tmp_path: Path) -> None:
    project = _mkdirs(tmp_path, "project")
    app = _mkdirs(project, "app")
    src = _mkdirs(app, "src")
    _write(project / ".envstencil.toml", "[check]\ndiff = true\n")
    _write(app / ".envstencil.toml", "[check]\ndiff = false\n")

    assert load_project_config(src).check.diff is False


def test_load_pyproject_ancestor_directory_propagates_error(
    tmp_path: Path,
) -> None:
    project = _mkdirs(tmp_path, "project")
    deep = _mkdirs(project, "a", "b")
    _mkdirs(project, "pyproject.toml")

    with pytest.raises((IsADirectoryError, PermissionError)):
        load_pyproject_config(deep)


# --- precedence with upward discovery (milestone 5) ----------


def test_load_config_project_beats_pyproject_across_directories(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    workspace = _mkdirs(tmp_path, "workspace")
    project = _mkdirs(workspace, "project")
    src = _mkdirs(project, "src")
    _write(
        workspace / "pyproject.toml",
        "[tool.envstencil.check]\ndiff = true\n",
    )
    _write(project / ".envstencil.toml", "[check]\ndiff = false\n")

    assert load_config(cwd=src).check.diff is False


def test_load_config_from_subdir_equals_from_project_root(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    project = _mkdirs(tmp_path, "project")
    deep = _mkdirs(project, "src", "app")
    _write(project / "pyproject.toml", "[tool.envstencil.global]\nfile1='x'\n")
    _write(project / ".envstencil.toml", "[check]\ndiff = true\n")

    assert load_config(cwd=deep) == load_config(cwd=project)
