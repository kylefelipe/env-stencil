"""Core logic for envstencil: parse .env files and generate a safe .env.example."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PLACEHOLDER = "your_value_here"

# Matches KEY=VALUE lines, tolerating optional `export ` prefix and spaces
# around the `=`. Keys follow standard shell/dotenv identifier rules.
_KEY_VALUE_RE = re.compile(
    r"^(?P<prefix>export\s+)?(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<value>.*)$"
)

# Opt-in directive that tells envstencil to keep the real value in the stencil
# instead of replacing it with the placeholder. Accepted either as an inline
# comment on the pair itself or as a standalone comment on the line above it.
_KEEP_MARKER_RE = re.compile(r"#\s*envstencil\s*:\s*keep\b", re.IGNORECASE)


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
            return head, value[len(head):]
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
    """Represents one parsed line from a .env file."""

    raw: str
    kind: str  # "comment", "blank", "pair", "unknown"
    key: str | None = None
    value: str | None = None
    prefix: str = ""
    inline_comment: str = ""  # trailing `# ...` on a pair (with its leading space)
    keep: bool = False  # pair marked with `# envstencil:keep`


def parse_env_file(path: Path) -> list[EnvLine]:
    """Parse a .env file into a list of EnvLine entries, preserving order,
    blank lines, and comments so the structure can be mirrored in the output.

    The `# envstencil:keep` directive itself is never kept as an EnvLine: a
    standalone directive line is dropped (only its effect survives, on the next
    pair), and an inline directive is stripped from the pair's comment.
    """
    lines: list[EnvLine] = []
    text = path.read_text(encoding="utf-8")

    # Set by a standalone `# envstencil:keep` comment and consumed by the next
    # pair. Blank lines in between are tolerated; any other line clears it.
    pending_keep = False

    for raw_line in text.splitlines():
        stripped = raw_line.strip()

        if not stripped:
            lines.append(EnvLine(raw=raw_line, kind="blank"))
            continue

        if stripped.startswith("#"):
            if _KEEP_MARKER_RE.search(stripped):
                pending_keep = True
                remainder = _strip_keep_marker(stripped).lstrip()
                if remainder:
                    lines.append(EnvLine(raw=remainder, kind="comment"))
            else:
                lines.append(EnvLine(raw=raw_line, kind="comment"))
            continue

        match = _KEY_VALUE_RE.match(stripped)
        if match:
            value, inline_comment = _split_inline_comment(match.group("value"))
            has_inline_marker = bool(_KEEP_MARKER_RE.search(inline_comment))
            if has_inline_marker:
                inline_comment = _strip_keep_marker(inline_comment)
            lines.append(
                EnvLine(
                    raw=raw_line,
                    kind="pair",
                    key=match.group("key"),
                    value=value,
                    prefix=match.group("prefix") or "",
                    inline_comment=inline_comment,
                    keep=pending_keep or has_inline_marker,
                )
            )
            pending_keep = False
            continue

        lines.append(EnvLine(raw=raw_line, kind="unknown"))
        pending_keep = False

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


def render_stencil(
    lines: list[EnvLine],
    placeholder: str = DEFAULT_PLACEHOLDER,
    collapse_blank_lines: bool = False,
) -> str:
    """Render parsed EnvLine entries into a .env.example body, replacing every
    value with a generic placeholder while keeping comments and structure.

    Inline comments documenting a pair are preserved. Pairs flagged with
    `# envstencil:keep` (inline or on the line above) keep their real value; the
    `envstencil:keep` directive itself never appears in the output.

    When `collapse_blank_lines` is true, runs of consecutive blank lines are
    reduced to a single blank line.
    """
    output_lines: list[str] = []

    for line in lines:
        if line.kind in ("comment", "blank", "unknown"):
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
    """Read `source` (.env) and write a stencil to `destination` (.env.example).

    Raises FileExistsError if destination exists and force is False.
    Raises FileNotFoundError if source does not exist.
    """
    if not source.exists():
        raise FileNotFoundError(f"Arquivo de origem não encontrado: {source}")

    if destination.exists() and not force:
        raise FileExistsError(
            f"{destination} já existe. Use --force para sobrescrever."
        )

    lines = parse_env_file(source)
    content = render_stencil(
        lines,
        placeholder=placeholder,
        collapse_blank_lines=collapse_blank_lines,
    )
    destination.write_text(content, encoding="utf-8")
    return destination
