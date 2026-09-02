from pathlib import Path

import pytest

from envstencil.core import (
    DEFAULT_PLACEHOLDER,
    AppendResult,
    UnsafeEnvLineError,
    UnterminatedQuotedValueError,
    append_missing_variables,
    generate_example,
    get_keys,
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


def _render_file(tmp_path: Path, content: str) -> str:
    env_file = tmp_path / ".env"
    env_file.write_text(content, encoding="utf-8")
    return render_stencil(parse_env_file(env_file))


# --- Valores multi-linha entre aspas --------------------------------------


def test_multiline_double_quoted_value_is_masked(tmp_path: Path) -> None:
    secret = "super-secret"
    rendered = _render_file(
        tmp_path,
        'PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n'
        f"{secret}\n"
        '-----END PRIVATE KEY-----"\n',
    )

    assert f"PRIVATE_KEY={DEFAULT_PLACEHOLDER}\n" in rendered
    assert secret not in rendered
    assert "BEGIN PRIVATE KEY" not in rendered


def test_multiline_parsed_as_single_pair_with_line_span(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        'A=1\nCERT="linha 1\nlinha 2\nlinha 3"\nB=2\n', encoding="utf-8"
    )

    lines = parse_env_file(env_file)
    pairs = [line for line in lines if line.kind == "pair"]

    assert [p.key for p in pairs] == ["A", "CERT", "B"]
    cert = pairs[1]
    assert cert.line_number == 2
    assert cert.end_line_number == 4
    assert pairs[2].line_number == 5  # B= comes after the consumed block


def test_multiline_single_quoted_value_is_masked(tmp_path: Path) -> None:
    rendered = _render_file(tmp_path, "VALUE='linha 1\nlinha 2'\n")

    assert f"VALUE={DEFAULT_PLACEHOLDER}\n" in rendered
    assert "linha 1" not in rendered


def test_unterminated_quoted_value_raises_without_leaking(
    tmp_path: Path,
) -> None:
    secret = "conteudo-secreto-nunca-fechado-0987654321"
    env_file = tmp_path / ".env"
    env_file.write_text(
        f'TOKEN="linha 1\n{secret}\nmais-conteudo\n', encoding="utf-8"
    )
    dest = tmp_path / ".env.example"

    with pytest.raises(UnterminatedQuotedValueError) as excinfo:
        generate_example(env_file, dest)

    assert excinfo.value.line_number == 1
    assert excinfo.value.key == "TOKEN"
    assert "TOKEN" in str(excinfo.value)
    assert secret not in str(excinfo.value)
    assert not dest.exists()


def test_escaped_quote_does_not_close_multiline_value(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        'TEXT="foo \\"bar\\"\nsegunda linha"\nNEXT=ok\n', encoding="utf-8"
    )

    lines = parse_env_file(env_file)
    pairs = [line for line in lines if line.kind == "pair"]

    assert [p.key for p in pairs] == ["TEXT", "NEXT"]
    rendered = render_stencil(lines)
    assert f"TEXT={DEFAULT_PLACEHOLDER}\n" in rendered
    assert f"NEXT={DEFAULT_PLACEHOLDER}\n" in rendered
    assert "segunda linha" not in rendered


def test_inline_comment_after_multiline_value_is_kept(tmp_path: Path) -> None:
    rendered = _render_file(
        tmp_path, 'CERT="linha 1\nlinha 2"  # certificado\n'
    )

    assert f"CERT={DEFAULT_PLACEHOLDER}  # certificado\n" in rendered
    assert "linha 1" not in rendered


def test_keep_directive_above_multiline_value_preserves_it(
    tmp_path: Path,
) -> None:
    rendered = _render_file(
        tmp_path, '# envstencil:keep\nBANNER="linha 1\nlinha 2"\n'
    )

    assert 'BANNER="linha 1\nlinha 2"\n' in rendered
    assert "envstencil" not in rendered.lower()


def test_keep_directive_inline_on_multiline_value_preserves_it(
    tmp_path: Path,
) -> None:
    rendered = _render_file(
        tmp_path, 'BANNER="linha 1\nlinha 2"  # envstencil:keep\n'
    )

    assert 'BANNER="linha 1\nlinha 2"\n' in rendered
    assert "envstencil" not in rendered.lower()


# --- Chaves com ponto e hífen -------------------------------------------


def test_dotted_and_dashed_keys_are_masked(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "MY.APP.KEY=abc\nmy-setting=def\nexport a.b-c=ghi\n", encoding="utf-8"
    )

    lines = parse_env_file(env_file)
    assert [line.key for line in lines if line.kind == "pair"] == [
        "MY.APP.KEY",
        "my-setting",
        "a.b-c",
    ]

    rendered = render_stencil(lines)
    assert f"MY.APP.KEY={DEFAULT_PLACEHOLDER}\n" in rendered
    assert f"my-setting={DEFAULT_PLACEHOLDER}\n" in rendered
    assert f"export a.b-c={DEFAULT_PLACEHOLDER}\n" in rendered
    assert "abc" not in rendered


def test_leading_dash_line_is_still_unknown(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "KEY=ok\n-----BEGIN SOMETHING-----\n", encoding="utf-8"
    )

    with pytest.raises(UnsafeEnvLineError):
        render_stencil(parse_env_file(env_file))


# --- Outros ------------------------------------------------------------


def test_weird_but_valid_pair_is_still_masked(tmp_path: Path) -> None:
    rendered = _render_file(
        tmp_path, "KEY = qualquer coisa estranha $(x) ${y}\n"
    )

    assert f"KEY={DEFAULT_PLACEHOLDER}\n" in rendered
    assert "qualquer coisa estranha" not in rendered


def test_line_numbers_are_consistent_with_crlf(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_bytes(b"A=1\r\nB=2\r\n\r\nquebrada\r\n")

    with pytest.raises(UnsafeEnvLineError) as excinfo:
        render_stencil(parse_env_file(env_file))

    assert excinfo.value.line_number == 4


def test_generate_example_does_not_leave_partial_output(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text('OK=1\nBAD="sem fechar\n', encoding="utf-8")
    dest = tmp_path / ".env.example"

    with pytest.raises(UnterminatedQuotedValueError):
        generate_example(env_file, dest)

    assert not dest.exists()
    assert not (tmp_path / ".env.example.tmp").exists()


# --- append_missing_variables --------------------------------------------


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_append_adds_only_missing_keys_in_env_order(tmp_path: Path) -> None:
    src = _write(tmp_path / ".env", "A=1\nB=2\nC=3\n")
    dest = _write(tmp_path / ".env.example", "A=your_value_here\n")

    result = append_missing_variables(src, dest)

    assert isinstance(result, AppendResult)
    assert result.created is False
    assert result.added_keys == ["B", "C"]
    assert dest.read_text(encoding="utf-8") == (
        "A=your_value_here\n\nB=your_value_here\nC=your_value_here\n"
    )


def test_append_never_duplicates_existing_keys(tmp_path: Path) -> None:
    src = _write(tmp_path / ".env", "A=1\nB=2\n")
    dest = _write(tmp_path / ".env.example", "B=algo\nA=outra\n")

    result = append_missing_variables(src, dest)

    assert result.added_keys == []
    assert dest.read_text(encoding="utf-8") == "B=algo\nA=outra\n"


def test_append_preserves_existing_content_verbatim(tmp_path: Path) -> None:
    existing = (
        "# Banco de dados\n"
        "DATABASE_URL=your_value_here   # conexão principal\n"
        "\n"
        "\n"
        "# Cache (mantido pela equipe)\n"
        "REDIS_URL=CHANGE_ME\n"
    )
    src = _write(
        tmp_path / ".env",
        "DATABASE_URL=x\nREDIS_URL=y\nNEW_ONE=z\n",
    )
    dest = _write(tmp_path / ".env.example", existing)

    append_missing_variables(src, dest)

    out = dest.read_text(encoding="utf-8")
    assert out.startswith(existing)
    assert out == existing + "\nNEW_ONE=your_value_here\n"


def test_append_uses_custom_placeholder(tmp_path: Path) -> None:
    src = _write(tmp_path / ".env", "A=1\nNEW_API_KEY=real-secret\n")
    dest = _write(tmp_path / ".env.example", "A=your_value_here\n")

    append_missing_variables(src, dest, placeholder="CHANGE_ME")

    out = dest.read_text(encoding="utf-8")
    assert "NEW_API_KEY=CHANGE_ME\n" in out
    assert "real-secret" not in out


def test_append_honours_keep_directive(tmp_path: Path) -> None:
    src = _write(
        tmp_path / ".env",
        "A=1\nPORT=8000 # envstencil:keep\n# envstencil:keep\nHOST=local\n",
    )
    dest = _write(tmp_path / ".env.example", "A=your_value_here\n")

    result = append_missing_variables(src, dest)

    assert result.added_keys == ["PORT", "HOST"]
    out = dest.read_text(encoding="utf-8")
    assert "PORT=8000\n" in out
    assert "HOST=local\n" in out
    assert "envstencil" not in out.lower()


def test_append_keeps_env_order_for_new_keys(tmp_path: Path) -> None:
    src = _write(tmp_path / ".env", "Z=1\nM=2\nA=3\n")
    dest = _write(tmp_path / ".env.example", "# vazio de propósito\n")

    result = append_missing_variables(src, dest)

    assert result.added_keys == ["Z", "M", "A"]
    assert dest.read_text(encoding="utf-8").splitlines()[-3:] == [
        "Z=your_value_here",
        "M=your_value_here",
        "A=your_value_here",
    ]


def test_append_no_changes_does_not_rewrite_file(tmp_path: Path) -> None:
    src = _write(tmp_path / ".env", "A=1\nB=2\n")
    dest = _write(
        tmp_path / ".env.example", "B=your_value_here\nA=your_value_here\n"
    )
    before_bytes = dest.read_bytes()
    before_mtime = dest.stat().st_mtime_ns

    result = append_missing_variables(src, dest)

    assert result.added_keys == []
    assert result.created is False
    assert dest.read_bytes() == before_bytes
    assert dest.stat().st_mtime_ns == before_mtime


def test_append_generates_full_stencil_when_destination_missing(
    tmp_path: Path,
) -> None:
    src = _write(tmp_path / ".env", "# grupo\nA=1\nB=2\n")
    dest = tmp_path / ".env.example"

    result = append_missing_variables(src, dest)

    assert result.created is True
    assert result.added_keys == ["A", "B"]
    assert dest.read_text(encoding="utf-8") == (
        "# grupo\nA=your_value_here\nB=your_value_here\n"
    )


def test_append_aborts_on_unknown_line_in_source(tmp_path: Path) -> None:
    src = _write(tmp_path / ".env", "A=1\nlinha invalida sem igual\n")
    dest = _write(tmp_path / ".env.example", "A=your_value_here\n")
    before = dest.read_bytes()

    with pytest.raises(UnsafeEnvLineError):
        append_missing_variables(src, dest)

    assert dest.read_bytes() == before
    assert not (tmp_path / ".env.example.tmp").exists()


def test_append_aborts_on_unknown_line_in_destination(tmp_path: Path) -> None:
    src = _write(tmp_path / ".env", "A=1\nB=2\n")
    dest = _write(
        tmp_path / ".env.example",
        "A=your_value_here\n??? linha estranha\n",
    )
    before = dest.read_bytes()

    with pytest.raises(UnsafeEnvLineError):
        append_missing_variables(src, dest)

    assert dest.read_bytes() == before


def test_append_aborts_on_unterminated_quote_without_leaking(
    tmp_path: Path,
) -> None:
    secret = "segredo-sem-fechamento-13572468"
    src = _write(tmp_path / ".env", f'A=1\nCERT="abre aqui\n{secret}\n')
    dest = _write(tmp_path / ".env.example", "A=your_value_here\n")

    with pytest.raises(UnterminatedQuotedValueError) as excinfo:
        append_missing_variables(src, dest)

    assert secret not in str(excinfo.value)
    assert dest.read_text(encoding="utf-8") == "A=your_value_here\n"


def test_append_masks_multiline_value(tmp_path: Path) -> None:
    src = _write(
        tmp_path / ".env",
        'A=1\nCERT="linha 1\nlinha 2\nlinha 3"\n',
    )
    dest = _write(tmp_path / ".env.example", "A=your_value_here\n")

    result = append_missing_variables(src, dest)

    assert result.added_keys == ["CERT"]
    out = dest.read_text(encoding="utf-8")
    assert "CERT=your_value_here\n" in out
    assert "linha 2" not in out


def test_get_keys_returns_only_pair_keys(tmp_path: Path) -> None:
    lines = parse_env_file(
        _write(tmp_path / ".env", "# c\nA=1\n\nB=2\nexport C.d=3\n")
    )
    assert get_keys(lines) == {"A", "B", "C.d"}


def test_append_separator_when_file_has_no_trailing_newline(
    tmp_path: Path,
) -> None:
    src = _write(tmp_path / ".env", "A=1\nB=2\n")
    dest = tmp_path / ".env.example"
    dest.write_bytes(b"A=your_value_here")  # no trailing newline

    append_missing_variables(src, dest)

    assert dest.read_text(encoding="utf-8") == (
        "A=your_value_here\n\nB=your_value_here\n"
    )


def test_append_does_not_add_extra_blank_when_file_ends_blank(
    tmp_path: Path,
) -> None:
    src = _write(tmp_path / ".env", "A=1\nB=2\n")
    dest = _write(tmp_path / ".env.example", "A=your_value_here\n\n")

    append_missing_variables(src, dest)

    assert dest.read_text(encoding="utf-8") == (
        "A=your_value_here\n\nB=your_value_here\n"
    )


def test_append_into_empty_destination_file(tmp_path: Path) -> None:
    src = _write(tmp_path / ".env", "A=1\n")
    dest = _write(tmp_path / ".env.example", "")

    result = append_missing_variables(src, dest)

    assert result.added_keys == ["A"]
    assert dest.read_text(encoding="utf-8") == "A=your_value_here\n"


def test_append_raises_when_source_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        append_missing_variables(
            tmp_path / "nao-existe.env", tmp_path / ".env.example"
        )


def test_append_deduplicates_repeated_keys_in_source(tmp_path: Path) -> None:
    src = _write(tmp_path / ".env", "NEW=1\nOLD=2\nNEW=3\n")
    dest = _write(tmp_path / ".env.example", "OLD=your_value_here\n")

    result = append_missing_variables(src, dest)

    assert result.added_keys == ["NEW"]
    assert dest.read_text(encoding="utf-8").count("NEW=") == 1


def test_append_ignores_comments_and_blanks_in_source(tmp_path: Path) -> None:
    src = _write(
        tmp_path / ".env",
        "# um comentário\n\nOLD=1\n\n# outro\nNEW=2\n",
    )
    dest = _write(tmp_path / ".env.example", "OLD=your_value_here\n")

    result = append_missing_variables(src, dest)

    assert result.added_keys == ["NEW"]
    assert dest.read_text(encoding="utf-8") == (
        "OLD=your_value_here\n\nNEW=your_value_here\n"
    )
