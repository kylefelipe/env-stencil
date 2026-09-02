"""Command-line interface for envstencil."""

from __future__ import annotations

from pathlib import Path

import click

from .core import (
    DEFAULT_PLACEHOLDER,
    AppendResult,
    EnvComparison,
    EnvParseError,
    append_missing_variables,
    compare_env_files,
    generate_example,
)


class _InputError(click.ClickException):
    """A read/parsing/configuration error — exits with code 2."""

    exit_code = 2


@click.group()
@click.version_option()
def main() -> None:
    """envstencil — gera um .env.example seguro a partir do seu .env."""


def _report_append(result: AppendResult, source: Path) -> None:
    """Print a short, value-free summary of an append run."""
    if result.created:
        click.echo(f"✅ {result.destination} gerado a partir de {source}")
        return
    if not result.added_keys:
        click.echo(f"✓ {result.destination} já está atualizado.")
        return

    n = len(result.added_keys)
    click.echo(f"✅ {result.destination} atualizado.")
    click.echo()
    if n == 1:
        click.echo("1 nova variável adicionada:")
    else:
        click.echo(f"{n} novas variáveis adicionadas:")
    for key in result.added_keys:
        click.echo(f"  + {key}")


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
    help="Arquivo de saída (padrão: origem + '.example', no mesmo diretório).",
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
    help="Regenera e sobrescreve o .env.example por completo.",
)
@click.option(
    "-a",
    "--append",
    "append",
    is_flag=True,
    default=False,
    help="Preserva o .env.example e adiciona só as variáveis ausentes.",
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
    append: bool,
    collapse_blank_lines: bool,
) -> None:
    """Gera um .env.example a partir de SOURCE (padrão: .env).

    Sem flags: cria o arquivo apenas se ele ainda não existir (aborta se
    existir). --force regenera e sobrescreve tudo. --append preserva o
    arquivo e acrescenta só as variáveis que faltam.
    """
    if append and force:
        raise click.UsageError(
            "--append e --force não podem ser usados juntos."
        )

    if destination is None:
        destination = source.parent / f"{source.name}.example"

    try:
        if append:
            _report_append(
                append_missing_variables(
                    source=source,
                    destination=destination,
                    placeholder=placeholder,
                ),
                source,
            )
        else:
            result = generate_example(
                source=source,
                destination=destination,
                placeholder=placeholder,
                force=force,
                collapse_blank_lines=collapse_blank_lines,
            )
            click.echo(f"✅ {result} gerado a partir de {source}")
    except EnvParseError as exc:
        raise click.ClickException(str(exc)) from exc
    except FileExistsError as exc:
        raise click.ClickException(str(exc)) from exc
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc


def _plural_ausente(n: int) -> str:
    return "variável ausente" if n == 1 else "variáveis ausentes"


def _report_check(
    result: EnvComparison,
    source: Path,
    example: Path,
    show_diff: bool,
) -> None:
    """Print the differences (names only, never values)."""
    click.echo(f"⚠ Foram encontradas diferenças entre {source} e {example}.")
    click.echo()

    if show_diff:
        if result.missing_in_source:
            click.echo(f"Ausentes no {source}:")
            for key in result.missing_in_source:
                click.echo(f"  + {key}")
        if result.missing_in_example:
            if result.missing_in_source:
                click.echo()
            click.echo(f"Ausentes no {example}:")
            for key in result.missing_in_example:
                click.echo(f"  - {key}")
        return

    n_src = len(result.missing_in_source)
    n_ex = len(result.missing_in_example)
    if n_src:
        click.echo(f"{n_src} {_plural_ausente(n_src)} no {source}.")
    if n_ex:
        click.echo(f"{n_ex} {_plural_ausente(n_ex)} no {example}.")
    click.echo()
    click.echo("Use --diff para ver os detalhes.")


@main.command()
@click.argument(
    "source",
    type=click.Path(dir_okay=False, path_type=Path),
    default=".env",
    required=False,
)
@click.option(
    "-e",
    "--example",
    "example",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Stencil a comparar (padrão: SOURCE + '.example').",
)
@click.option(
    "--diff",
    "--dif",
    "show_diff",
    is_flag=True,
    default=False,
    help="Lista as variáveis divergentes em cada arquivo.",
)
@click.pass_context
def check(
    ctx: click.Context,
    source: Path,
    example: Path | None,
    show_diff: bool,
) -> None:
    """Compara as variáveis de SOURCE e do stencil (só nomes de chave).

    Não modifica nenhum arquivo. Sai com 0 se estiverem sincronizados, 1 se
    houver divergências e 2 em erro de leitura/parsing.
    """
    if example is None:
        example = source.parent / f"{source.name}.example"

    try:
        result = compare_env_files(source, example)
    except EnvParseError as exc:
        raise _InputError(str(exc)) from exc
    except FileNotFoundError as exc:
        raise _InputError(str(exc)) from exc

    if result.is_synced:
        click.echo(f"✓ {source} e {example} estão sincronizados.")
        return

    _report_check(result, source, example, show_diff)
    ctx.exit(1)


if __name__ == "__main__":
    main()
