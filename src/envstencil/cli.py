"""Command-line interface for envstencil."""

from __future__ import annotations

from pathlib import Path

import click

from .core import DEFAULT_PLACEHOLDER, generate_example


@click.group()
@click.version_option()
def main() -> None:
    """envstencil — gera um .env.example seguro a partir do seu .env."""


@main.command()
@click.argument(
    "source",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=".env",
    required=False,
)
@click.option(
    "-o",
    "--output",
    "destination",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Caminho do arquivo de saída (padrão: <source>.example ao lado do arquivo).",
)
@click.option(
    "-p",
    "--placeholder",
    default=DEFAULT_PLACEHOLDER,
    show_default=True,
    help="Texto usado para substituir cada valor.",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    default=False,
    help="Sobrescreve o arquivo de destino se ele já existir.",
)
@click.option(
    "-b",
    "--collapse-blank-lines",
    is_flag=True,
    default=False,
    help="Colapsa linhas em branco consecutivas em uma só.",
)
def generate(
    source: Path,
    destination: Path | None,
    placeholder: str,
    force: bool,
    collapse_blank_lines: bool,
) -> None:
    """Gera um .env.example a partir de SOURCE (padrão: .env)."""
    if destination is None:
        destination = source.parent / f"{source.name}.example"

    try:
        result = generate_example(
            source=source,
            destination=destination,
            placeholder=placeholder,
            force=force,
            collapse_blank_lines=collapse_blank_lines,
        )
    except FileExistsError as exc:
        raise click.ClickException(str(exc)) from exc
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"✅ {result} gerado a partir de {source}")


if __name__ == "__main__":
    main()
