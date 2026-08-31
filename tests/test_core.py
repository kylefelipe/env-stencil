from pathlib import Path

import pytest

from envstencil.core import (
    DEFAULT_PLACEHOLDER,
    UnsafeEnvLineError,
    generate_example,
    parse_env_file,
    render_stencil,
)

SAMPLE_ENV = """\
# Configuração do banco de dados
DATABASE_URL=postgres://user:pass@localhost:5432/mydb

# API keys
STRIPE_SECRET_KEY=sk_live_abc123
export PATH_EXTRA=/usr/local/bin

DEBUG=true
"""


def test_parse_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(SAMPLE_ENV, encoding="utf-8")

    lines = parse_env_file(env_file)
    kinds = [line.kind for line in lines]

    assert "comment" in kinds
    assert "blank" in kinds
    assert "pair" in kinds

    pairs = {line.key: line.value for line in lines if line.kind == "pair"}
    assert pairs["DATABASE_URL"] == "postgres://user:pass@localhost:5432/mydb"
    assert pairs["STRIPE_SECRET_KEY"] == "sk_live_abc123"
    assert pairs["PATH_EXTRA"] == "/usr/local/bin"
    assert pairs["DEBUG"] == "true"


def test_render_stencil_replaces_values_with_placeholder(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(SAMPLE_ENV, encoding="utf-8")

    lines = parse_env_file(env_file)
    rendered = render_stencil(lines)

    assert f"DATABASE_URL={DEFAULT_PLACEHOLDER}" in rendered
    assert f"STRIPE_SECRET_KEY={DEFAULT_PLACEHOLDER}" in rendered
    assert "export PATH_EXTRA=" in rendered
    assert "sk_live_abc123" not in rendered
    assert "# Configuração do banco de dados" in rendered


def test_render_stencil_custom_placeholder(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("SECRET=abc123\n", encoding="utf-8")

    lines = parse_env_file(env_file)
    rendered = render_stencil(lines, placeholder="CHANGE_ME")

    assert "SECRET=CHANGE_ME" in rendered


def test_generate_example_creates_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(SAMPLE_ENV, encoding="utf-8")
    dest = tmp_path / ".env.example"

    result = generate_example(env_file, dest)

    assert result == dest
    assert dest.exists()
    assert "sk_live_abc123" not in dest.read_text(encoding="utf-8")


def test_generate_example_raises_if_source_missing(tmp_path: Path) -> None:
    missing = tmp_path / ".env"
    dest = tmp_path / ".env.example"

    with pytest.raises(FileNotFoundError):
        generate_example(missing, dest)


def test_generate_example_raises_if_destination_exists(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("KEY=value\n", encoding="utf-8")
    dest = tmp_path / ".env.example"
    dest.write_text("existing content\n", encoding="utf-8")

    with pytest.raises(FileExistsError):
        generate_example(env_file, dest)


KEEP_ENV = """\
# Ambiente da aplicação
APP_ENV=development  # envstencil:keep

# envstencil:keep
LOG_LEVEL=info

DATABASE_URL=postgres://user:pass@localhost:5432/mydb
"""


def test_parse_marks_keep_pairs(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(KEEP_ENV, encoding="utf-8")

    keep = {
        line.key: line.keep
        for line in parse_env_file(env_file)
        if line.kind == "pair"
    }

    assert keep == {"APP_ENV": True, "LOG_LEVEL": True, "DATABASE_URL": False}


def test_render_keeps_marked_values_and_never_emits_the_directive(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(KEEP_ENV, encoding="utf-8")

    rendered = render_stencil(parse_env_file(env_file))

    assert "APP_ENV=development" in rendered
    assert "LOG_LEVEL=info" in rendered
    assert f"DATABASE_URL={DEFAULT_PLACEHOLDER}" in rendered
    assert "user:pass@localhost" not in rendered
    assert "envstencil" not in rendered.lower()


def test_inline_directive_strips_but_keeps_other_doc_text(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "WORKERS=4  # nº de processos  # envstencil:keep\n", encoding="utf-8"
    )

    rendered = render_stencil(parse_env_file(env_file))

    assert "WORKERS=4 # nº de processos\n" in rendered
    assert "envstencil" not in rendered.lower()


def test_directive_before_doc_leaves_single_space(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "CORE_3=6 # envstencil:keep # Teste de documentação\n",
        encoding="utf-8",
    )

    rendered = render_stencil(parse_env_file(env_file))

    assert "CORE_3=6 # Teste de documentação\n" in rendered
    assert "envstencil" not in rendered.lower()


def test_keep_marker_is_case_insensitive_and_spacing_tolerant(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("PORT=8000 #Envstencil : Keep\n", encoding="utf-8")

    rendered = render_stencil(parse_env_file(env_file))

    assert "PORT=8000\n" in rendered
    assert "envstencil" not in rendered.lower()


def test_standalone_keep_marker_only_applies_to_next_pair(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# envstencil:keep\nFIRST=kept\nSECOND=masked\n", encoding="utf-8"
    )

    rendered = render_stencil(parse_env_file(env_file))

    assert "FIRST=kept" in rendered
    assert f"SECOND={DEFAULT_PLACEHOLDER}" in rendered
    assert "envstencil" not in rendered.lower()


def test_inline_comment_is_kept_on_masked_pair(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL=postgres://user:pass@localhost/db  # URL de conexão do banco\n",
        encoding="utf-8",
    )

    lines = parse_env_file(env_file)
    pair = next(line for line in lines if line.kind == "pair")
    assert pair.value == "postgres://user:pass@localhost/db"
    assert pair.inline_comment == "  # URL de conexão do banco"

    rendered = render_stencil(lines)
    assert (
        f"DATABASE_URL={DEFAULT_PLACEHOLDER}  # URL de conexão do banco"
        in rendered
    )
    assert "user:pass@localhost" not in rendered


def test_hash_inside_quotes_is_not_an_inline_comment(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text('TOKEN="abc#def"\n', encoding="utf-8")

    pair = next(
        line for line in parse_env_file(env_file) if line.kind == "pair"
    )

    assert pair.value == '"abc#def"'
    assert pair.inline_comment == ""


def test_collapse_blank_lines_reduces_runs_to_one(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("A=1\n\n\n\nB=2\n\n\nC=3\n", encoding="utf-8")

    lines = parse_env_file(env_file)

    assert render_stencil(lines).count("\n\n\n") > 0
    collapsed = render_stencil(lines, collapse_blank_lines=True)
    assert "\n\n\n" not in collapsed
    assert (
        f"A={DEFAULT_PLACEHOLDER}\n\nB={DEFAULT_PLACEHOLDER}\n\nC={DEFAULT_PLACEHOLDER}\n"
        == collapsed
    )


def test_collapse_blank_lines_is_opt_in(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("A=1\n\n\nB=2\n", encoding="utf-8")

    rendered = render_stencil(parse_env_file(env_file))

    assert (
        f"A={DEFAULT_PLACEHOLDER}\n\n\nB={DEFAULT_PLACEHOLDER}\n" == rendered
    )


def test_generate_example_collapse_blank_lines(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("A=1\n\n\n\nB=2\n", encoding="utf-8")
    dest = tmp_path / ".env.example"

    generate_example(env_file, dest, collapse_blank_lines=True)

    assert "\n\n\n" not in dest.read_text(encoding="utf-8")


def test_generate_example_force_overwrites(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("KEY=value\n", encoding="utf-8")
    dest = tmp_path / ".env.example"
    dest.write_text("existing content\n", encoding="utf-8")

    result = generate_example(env_file, dest, force=True)

    assert f"KEY={DEFAULT_PLACEHOLDER}" in result.read_text(encoding="utf-8")


# --- Linhas não reconhecidas (fail-safe) -----------------------------------


def test_parse_env_file_tracks_line_numbers(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(SAMPLE_ENV, encoding="utf-8")

    lines = parse_env_file(env_file)

    assert [line.line_number for line in lines] == list(
        range(1, len(lines) + 1)
    )


def test_unknown_line_aborts_and_writes_nothing(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL=secret\nisto nao e uma linha dotenv valida\n",
        encoding="utf-8",
    )
    dest = tmp_path / ".env.example"

    with pytest.raises(UnsafeEnvLineError):
        generate_example(env_file, dest)

    assert not dest.exists()


def test_unknown_line_does_not_overwrite_existing_output(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("KEY=ok\n??? linha invalida\n", encoding="utf-8")
    dest = tmp_path / ".env.example"
    dest.write_text("conteudo anterior\n", encoding="utf-8")

    with pytest.raises(UnsafeEnvLineError):
        generate_example(env_file, dest, force=True)

    assert dest.read_text(encoding="utf-8") == "conteudo anterior\n"


def test_render_stencil_rejects_unknown_line(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("KEY=ok\n<<<lixo>>>\n", encoding="utf-8")

    with pytest.raises(UnsafeEnvLineError):
        render_stencil(parse_env_file(env_file))


def test_multiline_secret_like_content_aborts_without_leaking(
    tmp_path: Path,
) -> None:
    secret = "super-secret-content"
    env_file = tmp_path / ".env"
    env_file.write_text(
        'PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n'
        f"{secret}\n"
        '-----END PRIVATE KEY-----"\n',
        encoding="utf-8",
    )
    dest = tmp_path / ".env.example"

    with pytest.raises(UnsafeEnvLineError) as excinfo:
        generate_example(env_file, dest)

    assert secret not in str(excinfo.value)
    assert not dest.exists()


def test_unsafe_error_reports_the_offending_line_number(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# comentário\nKEY=ok\n\nlinha quebrada aqui\n", encoding="utf-8"
    )

    with pytest.raises(UnsafeEnvLineError) as excinfo:
        render_stencil(parse_env_file(env_file))

    assert excinfo.value.line_number == 4
    assert "4" in str(excinfo.value)


def test_unsafe_error_message_hides_sensitive_value(tmp_path: Path) -> None:
    secret = "AKIAIOSFODNN7EXAMPLE-conteudo-super-sensivel-1234567890"
    env_file = tmp_path / ".env"
    env_file.write_text(f"linha invalida com {secret}\n", encoding="utf-8")

    with pytest.raises(UnsafeEnvLineError) as excinfo:
        render_stencil(parse_env_file(env_file))

    assert secret not in str(excinfo.value)
