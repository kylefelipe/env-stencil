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
