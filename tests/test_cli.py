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


def test_check_custom_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".env.production").write_text("A=1\nX=2\n", encoding="utf-8")
    Path(".env.production.example").write_text("A=x\n", encoding="utf-8")

    result = CliRunner().invoke(
        main,
        [
            "check",
            ".env.production",
            "--example",
            ".env.production.example",
            "--diff",
        ],
    )

    assert result.exit_code == 1
    assert "  - X" in result.output
    assert "SMTP" not in result.output


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
