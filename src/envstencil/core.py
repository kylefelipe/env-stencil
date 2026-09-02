"""Core logic for envstencil: parse .env files and generate a safe .env.example."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PLACEHOLDER = "your_value_here"

# Matches KEY=VALUE lines, tolerating optional `export ` prefix and spaces
# around the `=`. The key must start like a shell identifier but may then
# contain `.` and `-` — both are accepted by common dotenv parsers (npm
# `dotenv` uses `[\w.-]+`, python-dotenv is even more permissive) and show up
# in real files (`my.app.key`, `my-setting`). The `\s*=` anchor keeps the
# match unambiguous: no `=`, no pair.
_KEY_VALUE_RE = re.compile(
    r"^(?P<prefix>export\s+)?"
    r"(?P<key>[A-Za-z_][A-Za-z0-9_.-]*)"
    r"\s*=\s*(?P<value>.*)$"
)

# Opt-in directive that tells envstencil to keep the real value in the stencil
# instead of replacing it with the placeholder. Accepted either as an inline
# comment on the pair itself or as a standalone comment on the line above it.
_KEEP_MARKER_RE = re.compile(r"#\s*envstencil\s*:\s*keep\b", re.IGNORECASE)


def _safe_preview(raw: str) -> str:
    """Return a content-free description of a line for error messages.

    The line's text is deliberately omitted: an unrecognized line may carry
    a secret, and it must never be echoed back verbatim.
    """
    return f"{len(raw.strip())} caractere(s)"


def _quote_closed(body: str, quote: str) -> bool:
    """Whether an already-open `quote` region is closed within `body`.

    `body` is the value text *after* the opening quote. Only the boundary
    matters — the content is never interpreted. For double quotes a
    backslash escapes the next character (so ``\\"`` does not close, and a
    trailing ``\\`` escapes the joined newline); single quotes have no
    escapes. Mirrors the scanning in `_split_inline_comment`.
    """
    i = 0
    n = len(body)
    while i < n:
        ch = body[i]
        if quote == '"' and ch == "\\":
            i += 2
            continue
        if ch == quote:
            return True
        i += 1
    return False


class EnvParseError(ValueError):
    """Base class for `.env` parsing failures that abort generation.

    envstencil is fail-safe: when it cannot be sure of a line's structure it
    stops instead of copying content it does not understand.
    """


class UnsafeEnvLineError(EnvParseError):
    """Raised when a line cannot be safely turned into a stencil entry.

    Attributes:
        line_number: 1-based line where the problem was found.
        raw: The offending line, kept for programmatic use — do not print it.
    """

    def __init__(self, line_number: int, raw: str) -> None:
        self.line_number = line_number
        self.raw = raw
        super().__init__(
            f"Linha {line_number} não reconhecida como sintaxe .env válida "
            f"({_safe_preview(raw)}). Revise a sintaxe do .env: o envstencil "
            f"aborta em vez de copiar linhas que não sabe sanitizar."
        )


class UnterminatedQuotedValueError(EnvParseError):
    """Raised when a quoted value is opened but never closed.

    Attributes:
        key: The variable whose value is unterminated (may be `None`).
        line_number: 1-based line where the value started.
    """

    def __init__(self, key: str | None, line_number: int) -> None:
        self.key = key
        self.line_number = line_number
        alvo = f"para {key}" if key else "para uma chave não identificada"
        super().__init__(
            f"Valor iniciado na linha {line_number} {alvo} possui aspas não "
            f"fechadas. Feche a aspa ou coloque o valor em uma única linha — "
            f"o envstencil aborta em vez de adivinhar onde o valor termina."
        )


def _split_inline_comment(value: str) -> tuple[str, str]:
    """Split a parsed value into ``(value, inline_comment)``.

    An inline comment starts at the first ``#`` that sits outside quotes and is
    either at the start or preceded by whitespace (dotenv convention). The
    returned ``inline_comment`` keeps its leading whitespace and the ``#`` so it
    can be re-appended verbatim; it is ``""`` when there is no inline comment.
    """
    quote = ""
    i = 0
    while i < len(value):
        ch = value[i]
        if quote:
            if ch == "\\" and quote == '"' and i + 1 < len(value):
                i += 2
                continue
            if ch == quote:
                quote = ""
        elif ch in ("'", '"'):
            quote = ch
        elif ch == "#" and (i == 0 or value[i - 1].isspace()):
            head = value[:i].rstrip()
            return head, value[len(head) :]
        i += 1
    return value, ""


def _strip_keep_marker(comment: str) -> str:
    """Remove the `# envstencil:keep` directive from a comment, keeping any other
    documentation text. Returns the leftover as an inline suffix (a single
    `" # ..."`), or ``""`` when the comment was only the directive.
    """
    cleaned = _KEEP_MARKER_RE.sub("", comment).strip()
    if not cleaned.strip("#").strip():
        return ""
    body = cleaned[1:].lstrip() if cleaned.startswith("#") else cleaned
    return f" # {body}"


@dataclass
class EnvLine:
    """Represents one parsed line from a .env file.

    Attributes:
        raw: The original line text, verbatim.
        kind: One of `"comment"`, `"blank"`, `"pair"`, or `"unknown"`.
        key: Variable name, when `kind == "pair"`.
        value: Variable value without any inline comment, when `kind == "pair"`.
        prefix: Leading `"export "` when present, otherwise `""`.
        inline_comment: Trailing `# ...` of a pair, with its leading space.
        keep: Whether the pair is flagged with `# envstencil:keep`.
        line_number: 1-based position where the entry starts in the source
            file (`0` when not produced by `parse_env_file`).
        end_line_number: Last physical line the entry spans, set only for
            multi-line quoted values; `None` otherwise.
    """

    raw: str
    kind: str  # "comment", "blank", "pair", "unknown"
    key: str | None = None
    value: str | None = None
    prefix: str = ""
    inline_comment: str = (
        ""  # trailing `# ...` on a pair (with its leading space)
    )
    keep: bool = False  # pair marked with `# envstencil:keep`
    line_number: int = 0  # 1-based; 0 = not set by parse_env_file
    end_line_number: int | None = None  # last line, for multi-line values


def parse_env_file(path: Path) -> list[EnvLine]:
    """Parse a .env file into ordered EnvLine entries.

    Blank lines and comments are preserved so the structure can be mirrored
    in the output. The `# envstencil:keep` directive is never kept as an
    EnvLine: a standalone directive line is dropped (only its effect
    survives, on the next pair) and an inline directive is stripped from the
    pair's comment.

    A quoted value (single or double) whose quote is not closed on its first
    line consumes the following physical lines until the quote closes, and
    the whole thing becomes one `kind == "pair"` entry.

    Args:
        path: Path to the `.env` file to read.

    Returns:
        The parsed lines, in file order.

    Raises:
        UnterminatedQuotedValueError: If a quoted value never closes.
    """

    lines: list[EnvLine] = []
    text = path.read_text(encoding="utf-8")

    # `splitlines()` handles \n, \r\n and \r consistently: one logical line
    # each. We index explicitly so a multi-line value can pull the lines it
    # needs.
    physical = text.splitlines()

    # Set by a standalone `# envstencil:keep` comment and consumed by the next
    # pair. Blank lines in between are tolerated; any other line clears it.
    pending_keep = False

    i = 0
    while i < len(physical):
        raw_line = physical[i]
        line_number = i + 1
        stripped = raw_line.strip()

        if not stripped:
            lines.append(
                EnvLine(raw=raw_line, kind="blank", line_number=line_number)
            )
            i += 1
            continue

        if stripped.startswith("#"):
            if _KEEP_MARKER_RE.search(stripped):
                pending_keep = True
                remainder = _strip_keep_marker(stripped).lstrip()
                if remainder:
                    lines.append(
                        EnvLine(
                            raw=remainder,
                            kind="comment",
                            line_number=line_number,
                        )
                    )
            else:
                lines.append(
                    EnvLine(
                        raw=raw_line,
                        kind="comment",
                        line_number=line_number,
                    )
                )
            i += 1
            continue

        match = _KEY_VALUE_RE.match(stripped)
        if match:
            raw_value = match.group("value")
            lead = raw_value[0] if raw_value[:1] in ("'", '"') else None

            if lead is not None and not _quote_closed(raw_value[1:], lead):
                collected = [raw_value]
                j = i
                while not _quote_closed("\n".join(collected)[1:], lead):
                    j += 1
                    if j >= len(physical):
                        raise UnterminatedQuotedValueError(
                            match.group("key"), line_number
                        )
                    collected.append(physical[j])
                raw_repr = "\n".join(collected)
                value, inline_comment = _split_inline_comment(raw_repr)
                end_line_number: int | None = j + 1
            else:
                raw_repr = raw_line
                value, inline_comment = _split_inline_comment(raw_value)
                end_line_number = None
                j = i

            has_inline_marker = bool(_KEEP_MARKER_RE.search(inline_comment))
            if has_inline_marker:
                inline_comment = _strip_keep_marker(inline_comment)
            lines.append(
                EnvLine(
                    raw=raw_repr,
                    kind="pair",
                    key=match.group("key"),
                    value=value,
                    prefix=match.group("prefix") or "",
                    inline_comment=inline_comment,
                    keep=pending_keep or has_inline_marker,
                    line_number=line_number,
                    end_line_number=end_line_number,
                )
            )
            pending_keep = False
            i = j + 1
            continue

        lines.append(
            EnvLine(raw=raw_line, kind="unknown", line_number=line_number)
        )
        pending_keep = False
        i += 1

    return lines


def _collapse_blank_lines(rows: list[str]) -> list[str]:
    """Collapse every run of consecutive blank lines down to a single one."""
    collapsed: list[str] = []
    prev_blank = False
    for row in rows:
        is_blank = not row.strip()
        if is_blank and prev_blank:
            continue
        collapsed.append(row)
        prev_blank = is_blank
    return collapsed


def _assert_no_unknown(lines: list[EnvLine]) -> None:
    """Abort on the first `kind == "unknown"` entry (fail-safe)."""
    for line in lines:
        if line.kind == "unknown":
            raise UnsafeEnvLineError(line.line_number, line.raw)


def _atomic_write(destination: Path, content: str) -> None:
    """Write `content` to `destination` via a temp file + `os.replace`.

    A failure never leaves `destination` half-written or a stray `.tmp`.
    """
    tmp = destination.with_name(destination.name + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    try:
        os.replace(tmp, destination)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise


def get_keys(lines: list[EnvLine]) -> set[str]:
    """Return the set of variable names among `kind == "pair"` entries."""
    return {line.key for line in lines if line.kind == "pair" and line.key}


def render_stencil(
    lines: list[EnvLine],
    placeholder: str = DEFAULT_PLACEHOLDER,
    collapse_blank_lines: bool = False,
) -> str:
    """Render parsed EnvLine entries into a .env.example body.

    Every value is replaced with `placeholder` while comments and structure
    are kept. Inline comments documenting a pair are preserved. Pairs flagged
    with `# envstencil:keep` keep their real value (multi-line values keep
    their real newlines), and the directive itself never appears in the
    output.

    Generation is fail-safe: an `"unknown"` line (one the parser could not
    classify) is never copied — it aborts with `UnsafeEnvLineError`.

    Args:
        lines: Parsed entries from
            [`parse_env_file`][envstencil.core.parse_env_file].
        placeholder: Text that replaces each value.
        collapse_blank_lines: If `True`, reduce every run of consecutive
            blank lines to a single one.

    Returns:
        The rendered `.env.example` content, ending with a newline.

    Raises:
        UnsafeEnvLineError: If any line is `kind == "unknown"`.
    """

    _assert_no_unknown(lines)

    output_lines: list[str] = []

    for line in lines:
        if line.kind in ("comment", "blank"):
            output_lines.append(line.raw)
        elif line.kind == "pair":
            rendered_value = line.value if line.keep else placeholder
            output_lines.append(
                f"{line.prefix}{line.key}={rendered_value}{line.inline_comment}"
            )

    if collapse_blank_lines:
        output_lines = _collapse_blank_lines(output_lines)

    return "\n".join(output_lines) + "\n"


def generate_example(
    source: Path,
    destination: Path,
    placeholder: str = DEFAULT_PLACEHOLDER,
    force: bool = False,
    collapse_blank_lines: bool = False,
) -> Path:
    """Read `source` and write a stencil to `destination`.

    Args:
        source: Path to the source `.env` file.
        destination: Path of the `.env.example` to write.
        placeholder: Text that replaces each value.
        force: If `True`, overwrite `destination` when it already exists.
        collapse_blank_lines: If `True`, collapse consecutive blank lines.

    Returns:
        The `destination` path.

    Raises:
        FileNotFoundError: If `source` does not exist.
        FileExistsError: If `destination` exists and `force` is `False`.
        EnvParseError: If `source` has a line that cannot be sanitized
            (`UnsafeEnvLineError`) or a quoted value that never closes
            (`UnterminatedQuotedValueError`). Nothing is written or
            overwritten in that case.
    """

    if not source.exists():
        raise FileNotFoundError(f"Arquivo de origem não encontrado: {source}")

    if destination.exists() and not force:
        raise FileExistsError(
            f"{destination} já existe. Use --force para sobrescrever ou "
            f"--append para adicionar apenas as novas variáveis."
        )

    # Read → parse → render fully before touching the destination, then swap
    # atomically. A parsing error aborts before any file is created, and the
    # destination is never left half-written.
    lines = parse_env_file(source)
    content = render_stencil(
        lines,
        placeholder=placeholder,
        collapse_blank_lines=collapse_blank_lines,
    )
    _atomic_write(destination, content)
    return destination


@dataclass
class AppendResult:
    """Outcome of `append_missing_variables`.

    Attributes:
        destination: The `.env.example` path.
        added_keys: Keys added to it, in `.env` order (empty when nothing
            changed).
        created: `True` when the destination did not exist and a full
            stencil was generated instead of appending.
    """

    destination: Path
    added_keys: list[str]
    created: bool


def _append_block(original: str, block: str) -> str:
    """Return `original` with `block` appended after exactly one blank line.

    `original` is kept byte-for-byte; only a separator sized to leave a
    single blank line between the last existing line and the block is added
    (none extra when the file already ends with a blank line).
    """
    if not original.strip():
        return block
    if original.endswith("\n\n"):
        separator = ""
    elif original.endswith("\n"):
        separator = "\n"
    else:
        separator = "\n\n"
    return original + separator + block


def append_missing_variables(
    source: Path,
    destination: Path,
    placeholder: str = DEFAULT_PLACEHOLDER,
) -> AppendResult:
    """Add to `destination` only the `.env` keys it does not have yet.

    The existing `.env.example` is preserved byte-for-byte (comments, order,
    spacing, manual grouping); the new variables are appended at the end,
    masked with `placeholder`, in the order they appear in `source`. Keys are
    compared by name, never by line content, and never duplicated.

    If `destination` does not exist, a full stencil is generated instead
    (same as `generate_example` without flags on a missing target). If every
    key is already present, nothing is written and the file is left
    untouched.

    Args:
        source: Path to the source `.env` file.
        destination: Path of the `.env.example` to update.
        placeholder: Text that replaces each new value.

    Returns:
        An `AppendResult` describing what happened.

    Raises:
        FileNotFoundError: If `source` does not exist.
        EnvParseError: If `source` or an existing `destination` has a line
            that cannot be parsed safely. Nothing is written in that case.
    """
    if not source.exists():
        raise FileNotFoundError(f"Arquivo de origem não encontrado: {source}")

    source_lines = parse_env_file(source)
    _assert_no_unknown(source_lines)

    if not destination.exists():
        content = render_stencil(source_lines, placeholder=placeholder)
        _atomic_write(destination, content)
        added = [
            line.key
            for line in source_lines
            if line.kind == "pair" and line.key
        ]
        return AppendResult(destination, added, created=True)

    dest_lines = parse_env_file(destination)
    _assert_no_unknown(dest_lines)
    existing = get_keys(dest_lines)

    missing: list[EnvLine] = []
    seen: set[str] = set()
    for line in source_lines:
        if line.kind != "pair" or not line.key:
            continue
        if line.key in existing or line.key in seen:
            continue
        seen.add(line.key)
        missing.append(line)

    if not missing:
        return AppendResult(destination, [], created=False)

    block = render_stencil(missing, placeholder=placeholder)
    original = destination.read_text(encoding="utf-8")
    _atomic_write(destination, _append_block(original, block))
    return AppendResult(
        destination, [line.key for line in missing], created=False
    )
