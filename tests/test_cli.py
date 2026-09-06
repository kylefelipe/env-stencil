from pathlib import Path

from click.testing import CliRunner

from envstencil.cli import main


def test_generate_creates_sanitized_example(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text("SECRET=abc123\n", encoding="utf-8")

    result = CliRunner().invoke(main, ["generate"])

    assert result.exit_code == 0
    assert (
        Path(".env.example").read_text(encoding="utf-8")
        == "SECRET=your_value_here\n"
    )


def test_generate_aborts_on_unsafe_line(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    secret = "conteudo-super-sensivel-987654321"
    Path(".env").write_text(
        f"DATABASE_URL=ok\nlinha invalida com {secret}\n", encoding="utf-8"
    )

    result = CliRunner().invoke(main, ["generate"])

    assert result.exit_code != 0
    assert not Path(".env.example").exists()
    assert "Linha 2" in result.output
    assert secret not in result.output


def test_generate_unsafe_line_keeps_existing_output(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text("KEY=ok\n??? invalido\n", encoding="utf-8")
    Path(".env.example").write_text("anterior\n", encoding="utf-8")

    result = CliRunner().invoke(main, ["generate", "--force"])

    assert result.exit_code != 0
    assert Path(".env.example").read_text(encoding="utf-8") == "anterior\n"


def test_generate_aborts_on_unterminated_quote(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    secret = "linha-secreta-sem-fechamento-13572468"
    Path(".env").write_text(
        f'OK=1\nCERT="comeca aqui\n{secret}\n', encoding="utf-8"
    )

    result = CliRunner().invoke(main, ["generate"])

    assert result.exit_code != 0
    assert not Path(".env.example").exists()
    assert not Path(".env.example.tmp").exists()
    assert "linha 2" in result.output
    assert "CERT" in result.output
    assert secret not in result.output


def test_generate_masks_multiline_value(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text(
        'KEY="linha 1\nlinha 2\nlinha 3"\n', encoding="utf-8"
    )

    result = CliRunner().invoke(main, ["generate"])

    assert result.exit_code == 0
    out = Path(".env.example").read_text(encoding="utf-8")
    assert out == "KEY=your_value_here\n"


# --- generate --append -------------------------------------------------


def test_append_reports_added_keys_without_values(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text(
        "A=1\nSMTP_HOST=smtp.example.com\nSMTP_PASSWORD=super-secret\n",
        encoding="utf-8",
    )
    Path(".env.example").write_text("A=your_value_here\n", encoding="utf-8")

    result = CliRunner().invoke(main, ["generate", "--append"])

    assert result.exit_code == 0
    assert "SMTP_HOST" in result.output
    assert "SMTP_PASSWORD" in result.output
    assert "2 novas variáveis adicionadas" in result.output
    assert "super-secret" not in result.output
    assert "smtp.example.com" not in result.output


def test_append_singular_message_for_one_key(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text("A=1\nNEW=2\n", encoding="utf-8")
    Path(".env.example").write_text("A=your_value_here\n", encoding="utf-8")

    result = CliRunner().invoke(main, ["generate", "--append"])

    assert result.exit_code == 0
    assert "1 nova variável adicionada" in result.output
    assert "+ NEW" in result.output


def test_append_no_changes_message_and_no_rewrite(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text("A=1\nB=2\n", encoding="utf-8")
    Path(".env.example").write_text(
        "B=your_value_here\nA=your_value_here\n", encoding="utf-8"
    )
    before = Path(".env.example").read_bytes()

    result = CliRunner().invoke(main, ["generate", "--append"])

    assert result.exit_code == 0
    assert "já está atualizado" in result.output
    assert Path(".env.example").read_bytes() == before


def test_generate_no_flags_on_existing_target_suggests_both_options(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text("A=1\n", encoding="utf-8")
    Path(".env.example").write_text("conteudo manual\n", encoding="utf-8")

    result = CliRunner().invoke(main, ["generate"])

    assert result.exit_code != 0
    assert "--force" in result.output
    assert "--append" in result.output
    assert (
        Path(".env.example").read_text(encoding="utf-8") == "conteudo manual\n"
    )


def test_append_and_force_together_fail(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text("A=1\n", encoding="utf-8")

    result = CliRunner().invoke(main, ["generate", "--append", "--force"])

    assert result.exit_code != 0
    assert "juntos" in result.output


def test_append_generates_when_target_missing(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text("A=1\nB=2\n", encoding="utf-8")

    result = CliRunner().invoke(main, ["generate", "--append"])

    assert result.exit_code == 0
    assert Path(".env.example").read_text(encoding="utf-8") == (
        "A=your_value_here\nB=your_value_here\n"
    )


# --- envstencil check ------------------------------------------------


def test_check_synced_exit_zero(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text("A=secret\nB=secret\n", encoding="utf-8")
    Path(".env.example").write_text(
        "A=your_value_here\nB=your_value_here\n", encoding="utf-8"
    )

    result = CliRunner().invoke(main, ["check"])

    assert result.exit_code == 0
    assert "sincronizados" in result.output


def test_check_differences_without_diff(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text("A=1\nLOCAL_DEBUG=1\n", encoding="utf-8")
    Path(".env.example").write_text(
        "A=x\nSMTP_HOST=x\nSMTP_PASSWORD=super-secret\n", encoding="utf-8"
    )

    result = CliRunner().invoke(main, ["check"])

    assert result.exit_code == 1
    assert "2 variáveis ausentes no .env." in result.output
    assert "1 variável ausente no .env.example." in result.output
    assert "--diff" in result.output
    assert "super-secret" not in result.output
    # summary should not need to spell out every key
    assert "SMTP_HOST" not in result.output


def test_check_differences_with_diff_lists_keys_in_order(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text("A=1\nLOCAL_DEBUG=1\n", encoding="utf-8")
    Path(".env.example").write_text(
        "A=x\nSMTP_HOST=x\nSMTP_PORT=x\nSMTP_PASSWORD=my-secret-999\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(main, ["check", "--diff"])

    assert result.exit_code == 1
    assert "  + SMTP_HOST" in result.output
    assert "  + SMTP_PORT" in result.output
    assert "  + SMTP_PASSWORD" in result.output
    assert "  - LOCAL_DEBUG" in result.output
    assert result.output.index("SMTP_HOST") < result.output.index("SMTP_PORT")
    assert "my-secret-999" not in result.output


def test_check_dif_alias_matches_diff(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text("A=1\n", encoding="utf-8")
    Path(".env.example").write_text("A=x\nB=x\n", encoding="utf-8")

    with_diff = CliRunner().invoke(main, ["check", "--diff"])
    with_alias = CliRunner().invoke(main, ["check", "--dif"])

    assert with_alias.exit_code == with_diff.exit_code == 1
    assert with_alias.output == with_diff.output


def test_check_example_option_still_works(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    Path("a.env").write_text("A=1\nX=2\n", encoding="utf-8")
    Path("b.env").write_text("A=x\n", encoding="utf-8")

    result = CliRunner().invoke(
        main, ["check", "a.env", "--example", "b.env", "--diff"]
    )

    assert result.exit_code == 1
    assert "  - X" in result.output


def test_check_one_positional_derives_second_file(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".env.production").write_text("A=1\n", encoding="utf-8")
    Path(".env.production.example").write_text("A=x\nQ=y\n", encoding="utf-8")

    result = CliRunner().invoke(main, ["check", ".env.production"])

    assert result.exit_code == 1
    assert (
        "diferenças entre .env.production e .env.production.example"
        in result.output
    )


def test_check_two_positionals_compared_exactly(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    Path("a.env").write_text("A=1\nB=2\n", encoding="utf-8")
    Path("b.env").write_text("A=x\nB=y\n", encoding="utf-8")
    # a "a.env.example" that must be ignored when two args are given
    Path("a.env.example").write_text("A=x\nZZZ=x\n", encoding="utf-8")

    result = CliRunner().invoke(main, ["check", "a.env", "b.env"])

    assert result.exit_code == 0
    assert "a.env e b.env estão sincronizados" in result.output
    assert "ZZZ" not in result.output


def test_check_two_positionals_with_diff_no_values(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    Path("a.env").write_text(
        "A=1\nSMTP_PASSWORD=super-secret-42\n", encoding="utf-8"
    )
    Path("b.env").write_text("A=x\nLOCAL_DEBUG=x\n", encoding="utf-8")

    result = CliRunner().invoke(main, ["check", "a.env", "b.env", "--diff"])

    assert result.exit_code == 1
    assert "  + LOCAL_DEBUG" in result.output
    assert "  - SMTP_PASSWORD" in result.output
    assert "super-secret-42" not in result.output


def test_check_file2_and_example_together_is_error(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    for name in ("a.env", "b.env", "c.env"):
        Path(name).write_text("A=1\n", encoding="utf-8")

    result = CliRunner().invoke(
        main, ["check", "a.env", "b.env", "--example", "c.env"]
    )

    assert result.exit_code == 2
    assert "FILE2" in result.output
    assert "--example" in result.output


def test_check_parse_error_exits_two(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text(
        "A=1\nlinha invalida com segredo AKIA123\n", encoding="utf-8"
    )
    Path(".env.example").write_text("A=x\n", encoding="utf-8")

    result = CliRunner().invoke(main, ["check"])

    assert result.exit_code == 2
    assert "AKIA123" not in result.output


def test_check_missing_file_exits_two(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".env.example").write_text("A=x\n", encoding="utf-8")

    result = CliRunner().invoke(main, ["check"])

    assert result.exit_code == 2
    assert "não encontrado" in result.output


def test_check_does_not_create_or_touch_files(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text("A=1\nB=2\n", encoding="utf-8")
    Path(".env.example").write_text("A=x\n", encoding="utf-8")
    before = sorted(p.name for p in tmp_path.iterdir())

    CliRunner().invoke(main, ["check"])
    CliRunner().invoke(main, ["check", "--diff"])

    assert sorted(p.name for p in tmp_path.iterdir()) == before


# --- --config global option --------------------


def test_config_option_accepted_with_help(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "whatever.toml").write_text("[check]\ndiff = true\n", "utf-8")

    result = CliRunner().invoke(main, ["--config", "whatever.toml", "--help"])

    assert result.exit_code == 0
    assert "--config" in result.output


def test_config_missing_file_fails_without_traceback(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text("A=1\n", encoding="utf-8")
    Path(".env.example").write_text("A=x\n", encoding="utf-8")

    result = CliRunner().invoke(main, ["--config", "nao-existe.toml", "check"])

    assert result.exit_code != 0
    assert "Error" in result.output
    assert "Traceback" not in result.output


def test_config_invalid_toml_fails_without_traceback(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text("A=1\n", encoding="utf-8")
    Path(".env.example").write_text("A=x\n", encoding="utf-8")
    Path("broken.toml").write_text("[check\ndiff = true\n", encoding="utf-8")

    result = CliRunner().invoke(main, ["--config", "broken.toml", "check"])

    assert result.exit_code != 0
    assert "Traceback" not in result.output
    assert "Invalid TOML configuration" in result.output


def test_config_valid_changes_check_behaviour(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text("A=1\nB=2\n", encoding="utf-8")
    Path(".env.example").write_text("A=x\n", encoding="utf-8")
    Path("cfg.toml").write_text("[check]\ndiff = true\n", encoding="utf-8")

    without = CliRunner().invoke(main, ["check"])
    with_config = CliRunner().invoke(main, ["--config", "cfg.toml", "check"])

    assert without.exit_code == with_config.exit_code == 1
    assert "Use --diff" in without.output  # no config -> summary only
    assert "  - B" in with_config.output  # config diff=true -> listed


# --- check + config integration (milestone 4) -----------------


def _files(
    tmp_path: Path,
    a_content: str,
    b_content: str,
    a: str = ".env",
    b: str = ".env.example",
) -> None:
    (tmp_path / a).write_text(a_content, encoding="utf-8")
    (tmp_path / b).write_text(b_content, encoding="utf-8")


def test_check_zero_positionals_use_config_files(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _files(tmp_path, "A=1\n", "A=x\n", a=".env.local", b=".env.local.example")
    Path(".envstencil.toml").write_text(
        '[global]\nfile1 = ".env.local"\nfile2 = ".env.local.example"\n',
        encoding="utf-8",
    )

    result = CliRunner().invoke(main, ["check"])

    assert result.exit_code == 0
    assert (
        ".env.local e .env.local.example estão sincronizados" in result.output
    )


def test_check_one_positional_ignores_config_file2(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    Path("custom.env").write_text("A=1\n", encoding="utf-8")
    Path("custom.env.example").write_text("A=x\n", encoding="utf-8")
    Path(".env.example").write_text("SHOULD=not-be-used\n", encoding="utf-8")
    Path(".envstencil.toml").write_text(
        '[global]\nfile2 = ".env.example"\n', encoding="utf-8"
    )

    result = CliRunner().invoke(main, ["check", "custom.env"])

    assert result.exit_code == 0
    assert "custom.env e custom.env.example" in result.output


def test_check_two_positionals_beat_config(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    Path("a.env").write_text("A=1\n", encoding="utf-8")
    Path("b.env").write_text("A=x\n", encoding="utf-8")
    Path(".envstencil.toml").write_text(
        '[global]\nfile1 = ".env"\nfile2 = ".env.example"\n', encoding="utf-8"
    )

    result = CliRunner().invoke(main, ["check", "a.env", "b.env"])

    assert result.exit_code == 0
    assert "a.env e b.env estão sincronizados" in result.output


def test_check_example_beats_config_file2(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text("A=1\n", encoding="utf-8")
    Path("real.example").write_text("A=x\n", encoding="utf-8")
    Path(".envstencil.toml").write_text(
        '[global]\nfile2 = ".env.example"\n', encoding="utf-8"
    )

    result = CliRunner().invoke(main, ["check", "--example", "real.example"])

    assert result.exit_code == 0
    assert ".env e real.example estão sincronizados" in result.output


def test_check_file2_and_example_conflict_still_errors(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    for name in ("a.env", "b.env", "c.env"):
        Path(name).write_text("A=1\n", encoding="utf-8")

    result = CliRunner().invoke(
        main, ["check", "a.env", "b.env", "--example", "c.env"]
    )

    assert result.exit_code == 2
    assert "FILE2" in result.output


def test_check_config_diff_true_is_applied(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _files(tmp_path, "A=1\nB=2\n", "A=x\n")
    Path(".envstencil.toml").write_text(
        "[check]\ndiff = true\n", encoding="utf-8"
    )

    result = CliRunner().invoke(main, ["check"])

    assert result.exit_code == 1
    assert "  - B" in result.output


def test_check_config_diff_false_is_applied(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _files(tmp_path, "A=1\nB=2\n", "A=x\n")
    Path(".envstencil.toml").write_text(
        "[check]\ndiff = false\n", encoding="utf-8"
    )

    result = CliRunner().invoke(main, ["check"])

    assert result.exit_code == 1
    assert "Use --diff" in result.output
    assert "  - B" not in result.output


def test_check_cli_diff_beats_config_false(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _files(tmp_path, "A=1\nB=2\n", "A=x\n")
    Path(".envstencil.toml").write_text(
        "[check]\ndiff = false\n", encoding="utf-8"
    )

    result = CliRunner().invoke(main, ["check", "--diff"])

    assert result.exit_code == 1
    assert "  - B" in result.output


def test_check_cli_no_diff_beats_config_true(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _files(tmp_path, "A=1\nB=2\n", "A=x\n")
    Path(".envstencil.toml").write_text(
        "[check]\ndiff = true\n", encoding="utf-8"
    )

    result = CliRunner().invoke(main, ["check", "--no-diff"])

    assert result.exit_code == 1
    assert "  - B" not in result.output
    assert "Use --diff" in result.output


def test_check_explicit_config_changes_real_behaviour(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _files(tmp_path, "A=1\nB=2\n", "A=x\n")
    Path("ci.toml").write_text("[check]\ndiff = true\n", encoding="utf-8")

    result = CliRunner().invoke(main, ["--config", "ci.toml", "check"])

    assert result.exit_code == 1
    assert "  - B" in result.output


def test_check_pyproject_config_changes_real_behaviour(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _files(tmp_path, "A=1\nB=2\n", "A=x\n")
    Path("pyproject.toml").write_text(
        "[tool.envstencil.check]\ndiff = true\n", encoding="utf-8"
    )

    result = CliRunner().invoke(main, ["check"])

    assert result.exit_code == 1
    assert "  - B" in result.output


def test_check_user_config_changes_real_behaviour(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    cfg = tmp_path / "xdg" / "envstencil" / "config.toml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text("[check]\ndiff = true\n", encoding="utf-8")
    _files(tmp_path, "A=1\nB=2\n", "A=x\n")

    result = CliRunner().invoke(main, ["check"])

    assert result.exit_code == 1
    assert "  - B" in result.output


def test_check_no_config_keeps_default_behaviour(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    _files(tmp_path, "A=1\nB=2\n", "A=x\n")

    result = CliRunner().invoke(main, ["check"])

    assert result.exit_code == 1
    assert "Use --diff" in result.output
    assert "  - B" not in result.output


# --- generate + config integration (milestone 4) -------------


def test_generate_uses_config_files_as_defaults(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".env.prod").write_text("A=secret\n", encoding="utf-8")
    Path(".envstencil.toml").write_text(
        '[global]\nfile1 = ".env.prod"\nfile2 = "out.example"\n',
        encoding="utf-8",
    )

    result = CliRunner().invoke(main, ["generate"])

    assert result.exit_code == 0
    assert (
        Path("out.example").read_text(encoding="utf-8")
        == "A=your_value_here\n"
    )
    assert not Path(".env.example").exists()


def test_generate_explicit_source_beats_config(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text("A=secret\n", encoding="utf-8")
    Path(".env.prod").write_text("Z=secret\n", encoding="utf-8")
    Path(".envstencil.toml").write_text(
        '[global]\nfile1 = ".env.prod"\nfile2 = "out.example"\n',
        encoding="utf-8",
    )

    result = CliRunner().invoke(main, ["generate", ".env"])

    assert result.exit_code == 0
    assert (
        Path(".env.example").read_text(encoding="utf-8")
        == "A=your_value_here\n"
    )


def test_generate_config_force_true_overwrites(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text("A=secret\n", encoding="utf-8")
    Path(".env.example").write_text("velho\n", encoding="utf-8")
    Path(".envstencil.toml").write_text(
        "[generate]\nforce = true\n", encoding="utf-8"
    )

    result = CliRunner().invoke(main, ["generate"])

    assert result.exit_code == 0
    assert (
        Path(".env.example").read_text(encoding="utf-8")
        == "A=your_value_here\n"
    )


def test_generate_config_force_false_aborts_on_existing(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text("A=secret\n", encoding="utf-8")
    Path(".env.example").write_text("velho\n", encoding="utf-8")
    Path(".envstencil.toml").write_text(
        "[generate]\nforce = false\n", encoding="utf-8"
    )

    result = CliRunner().invoke(main, ["generate"])

    assert result.exit_code != 0
    assert Path(".env.example").read_text(encoding="utf-8") == "velho\n"


def test_generate_cli_force_beats_config_false(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text("A=secret\n", encoding="utf-8")
    Path(".env.example").write_text("velho\n", encoding="utf-8")
    Path(".envstencil.toml").write_text(
        "[generate]\nforce = false\n", encoding="utf-8"
    )

    result = CliRunner().invoke(main, ["generate", "--force"])

    assert result.exit_code == 0
    assert (
        Path(".env.example").read_text(encoding="utf-8")
        == "A=your_value_here\n"
    )


def test_generate_cli_no_force_beats_config_true(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text("A=secret\n", encoding="utf-8")
    Path(".env.example").write_text("velho\n", encoding="utf-8")
    Path(".envstencil.toml").write_text(
        "[generate]\nforce = true\n", encoding="utf-8"
    )

    result = CliRunner().invoke(main, ["generate", "--no-force"])

    assert result.exit_code != 0
    assert Path(".env.example").read_text(encoding="utf-8") == "velho\n"


def test_generate_explicit_config_changes_real_behaviour(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text("A=secret\n", encoding="utf-8")
    Path(".env.example").write_text("velho\n", encoding="utf-8")
    Path("ci.toml").write_text("[generate]\nforce = true\n", encoding="utf-8")

    result = CliRunner().invoke(main, ["--config", "ci.toml", "generate"])

    assert result.exit_code == 0
    assert (
        Path(".env.example").read_text(encoding="utf-8")
        == "A=your_value_here\n"
    )


def test_generate_pyproject_config_changes_real_behaviour(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text("A=secret\n", encoding="utf-8")
    Path(".env.example").write_text("velho\n", encoding="utf-8")
    Path("pyproject.toml").write_text(
        "[tool.envstencil.generate]\nforce = true\n", encoding="utf-8"
    )

    result = CliRunner().invoke(main, ["generate"])

    assert result.exit_code == 0
    assert (
        Path(".env.example").read_text(encoding="utf-8")
        == "A=your_value_here\n"
    )


def test_generate_user_config_changes_real_behaviour(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    cfg = tmp_path / "xdg" / "envstencil" / "config.toml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text("[generate]\nforce = true\n", encoding="utf-8")
    Path(".env").write_text("A=secret\n", encoding="utf-8")
    Path(".env.example").write_text("velho\n", encoding="utf-8")

    result = CliRunner().invoke(main, ["generate"])

    assert result.exit_code == 0
    assert (
        Path(".env.example").read_text(encoding="utf-8")
        == "A=your_value_here\n"
    )


def test_generate_no_config_keeps_default_behaviour(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    Path(".env").write_text("A=secret\n", encoding="utf-8")
    Path(".env.example").write_text("velho\n", encoding="utf-8")

    result = CliRunner().invoke(main, ["generate"])

    assert result.exit_code != 0
    assert Path(".env.example").read_text(encoding="utf-8") == "velho\n"


# --- full precedence (milestone 4) --------------------------


def test_full_precedence_cli_beats_every_config_layer_check(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    user = tmp_path / "xdg" / "envstencil" / "config.toml"
    user.parent.mkdir(parents=True)
    user.write_text("[check]\ndiff = false\n", encoding="utf-8")
    Path("pyproject.toml").write_text(
        "[tool.envstencil.check]\ndiff = true\n", encoding="utf-8"
    )
    Path(".envstencil.toml").write_text(
        "[check]\ndiff = false\n", encoding="utf-8"
    )
    Path("ci.toml").write_text("[check]\ndiff = true\n", encoding="utf-8")
    _files(tmp_path, "A=1\nB=2\n", "A=x\n")

    # ci.toml would give diff=true, but --no-diff (CLI) wins -> summary only
    result = CliRunner().invoke(
        main, ["--config", "ci.toml", "check", "--no-diff"]
    )

    assert result.exit_code == 1
    assert "  - B" not in result.output
    assert "Use --diff" in result.output


def test_full_precedence_cli_beats_every_config_layer_generate(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    user = tmp_path / "xdg" / "envstencil" / "config.toml"
    user.parent.mkdir(parents=True)
    user.write_text("[generate]\nforce = true\n", encoding="utf-8")
    Path("pyproject.toml").write_text(
        "[tool.envstencil.generate]\nforce = false\n", encoding="utf-8"
    )
    Path(".envstencil.toml").write_text(
        "[generate]\nforce = true\n", encoding="utf-8"
    )
    Path("ci.toml").write_text("[generate]\nforce = true\n", encoding="utf-8")
    Path(".env").write_text("A=secret\n", encoding="utf-8")
    Path(".env.example").write_text("velho\n", encoding="utf-8")

    # every layer up to ci.toml says force=true, but --no-force (CLI) wins
    result = CliRunner().invoke(
        main, ["--config", "ci.toml", "generate", "--no-force"]
    )

    assert result.exit_code != 0
    assert Path(".env.example").read_text(encoding="utf-8") == "velho\n"
