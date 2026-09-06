"""Command-line interface for envstencil."""

from __future__ import annotations

from pathlib import Path

import click

from .config import (
    ConfigError,
    EnvStencilConfig,
    GenerateBehaviour,
    load_config,
    resolve_check_config,
    resolve_generate_config,
)
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
@click.option(
    "--config",
    "config_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Arquivo de configuração TOML explícito (maior precedência).",
)
@click.pass_context
def main(ctx: click.Context, config_path: Path | None) -> None:
    """envstencil — gera um .env.example seguro a partir do seu .env.

    Fontes de configuração, da menor para a maior precedência: defaults
    internos, config global do usuário, `[tool.envstencil]` do
    `pyproject.toml`, `.envstencil.toml`, o arquivo de `--config`, e por
    último os argumentos/flags passados na linha de comando.
    """
    try:
        config = load_config(cwd=Path.cwd(), explicit_config=config_path)
    except ConfigError as exc:
        raise _InputError(str(exc)) from exc
    except OSError as exc:
        raise _InputError(
            f"Não foi possível ler a configuração: {exc}"
        ) from exc
    ctx.obj = {"config": config}


# --- generate --------------------------------------------------------


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


def _resolve_generate_behaviour(
    configured: GenerateBehaviour, force: bool, append: bool
) -> GenerateBehaviour:
    """Fold the CLI flags onto the configured behaviour.

    `--force` and `--append` are the only CLI knobs: each explicitly selects
    its behaviour and wins over the config. With neither flag the configured
    value (`fail` / `force` / `append`) is used as-is. There is no CLI way
    to force `fail` when the config asks for `force`/`append`.
    """
    if force and append:
        raise click.UsageError(
            "--append e --force não podem ser usados juntos."
        )
    if force:
        return GenerateBehaviour.FORCE
    if append:
        return GenerateBehaviour.APPEND
    return configured


def _resolve_generate_inputs(
    config: EnvStencilConfig,
    file1: Path | None,
    file2: Path | None,
    output: Path | None,
    force: bool,
    append: bool,
) -> tuple[Path, Path, GenerateBehaviour]:
    """Layer explicit CLI values over the resolved `[generate]`/`[global]`.

    Same shape as `check`: `FILE1`/`FILE2` are positional, `-o/--output` is
    the compatible alias for the second file. Source precedence: explicit
    `FILE1` over config. Destination precedence: explicit `FILE2` > explicit
    `--output` > `FILE1` + ".example" (config's second file is *not* mixed
    in) > configured file. Only a fully omitted pair falls back to the
    configured files. The behaviour is the configured one unless `--force` /
    `--append` override it. The caller has already rejected `FILE2` +
    `--output` together.
    """
    resolved = resolve_generate_config(config)
    src = file1 if file1 is not None else resolved.file1
    if file2 is not None:
        out = file2
    elif output is not None:
        out = output
    elif file1 is not None:
        out = file1.parent / f"{file1.name}.example"
    else:
        out = resolved.file2
    behaviour = _resolve_generate_behaviour(resolved.behaviour, force, append)
    return src, out, behaviour


@main.command()
@click.argument(
    "file1",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    required=False,
)
@click.argument(
    "file2",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    required=False,
)
@click.option(
    "-o",
    "--output",
    "output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Forma alternativa de informar o segundo arquivo (compatibilidade).",
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
    "force",
    is_flag=True,
    default=False,
    help="Regenera e sobrescreve o destino existente (override da config).",
)
@click.option(
    "-a",
    "--append",
    "append",
    is_flag=True,
    default=False,
    help="Preserva o destino e adiciona só as variáveis ausentes (override).",
)
@click.option(
    "-b",
    "--collapse-blank-lines",
    is_flag=True,
    default=False,
    help="Colapsa linhas em branco consecutivas em uma só.",
)
@click.pass_context
def generate(
    ctx: click.Context,
    file1: Path | None,
    file2: Path | None,
    output: Path | None,
    placeholder: str,
    force: bool,
    append: bool,
    collapse_blank_lines: bool,
) -> None:
    """Gera um .env.example seguro a partir de um arquivo dotenv.

    \b
    Sem argumentos:      arquivos da configuração (padrão .env / .env.example)
    Com um argumento:    FILE1 e FILE1 + ".example"
    Com dois argumentos: exatamente FILE1 e FILE2

    `--output` (`-o`) é uma forma alternativa/compatível de informar o
    segundo arquivo; não pode ser combinada com FILE2.

    \b
    O comportamento com um destino já existente vem de `[generate].behaviour`
    (`fail` — padrão —, `force` ou `append`):
        fail    cria só se o destino não existir; se existir, aborta.
        force   regenera e sobrescreve o destino.
        append  preserva o destino e acrescenta só as variáveis que faltam.
    --force e --append são overrides explícitos da CLI (vencem a config);
    não há flag para forçar `fail`.
    """
    if file2 is not None and output is not None:
        raise click.UsageError(
            "não é possível informar FILE2 e --output ao mesmo tempo."
        )

    try:
        src, out, behaviour = _resolve_generate_inputs(
            ctx.obj["config"], file1, file2, output, force, append
        )
    except ConfigError as exc:
        raise _InputError(str(exc)) from exc

    try:
        if behaviour is GenerateBehaviour.APPEND:
            _report_append(
                append_missing_variables(
                    source=src,
                    destination=out,
                    placeholder=placeholder,
                ),
                src,
            )
        else:
            result = generate_example(
                source=src,
                destination=out,
                placeholder=placeholder,
                force=behaviour is GenerateBehaviour.FORCE,
                collapse_blank_lines=collapse_blank_lines,
            )
            click.echo(f"✅ {result} gerado a partir de {src}")
    except EnvParseError as exc:
        raise click.ClickException(str(exc)) from exc
    except FileExistsError as exc:
        raise click.ClickException(str(exc)) from exc
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc


# --- check ----------------------------------------------------------


def _plural_ausente(n: int) -> str:
    return "variável ausente" if n == 1 else "variáveis ausentes"


def _report_check(
    result: EnvComparison,
    first: Path,
    second: Path,
    show_diff: bool,
) -> None:
    """Print the differences (names only, never values)."""
    click.echo(f"⚠ Foram encontradas diferenças entre {first} e {second}.")
    click.echo()

    if show_diff:
        if result.missing_in_source:
            click.echo(f"Ausentes no {first}:")
            for key in result.missing_in_source:
                click.echo(f"  + {key}")
        if result.missing_in_example:
            if result.missing_in_source:
                click.echo()
            click.echo(f"Ausentes no {second}:")
            for key in result.missing_in_example:
                click.echo(f"  - {key}")
        return

    n_first = len(result.missing_in_source)
    n_second = len(result.missing_in_example)
    if n_first:
        click.echo(f"{n_first} {_plural_ausente(n_first)} no {first}.")
    if n_second:
        click.echo(f"{n_second} {_plural_ausente(n_second)} no {second}.")
    click.echo()
    click.echo("Use --diff para ver os detalhes.")


def _resolve_check_inputs(
    config: EnvStencilConfig,
    file1: Path | None,
    file2: Path | None,
    example: Path | None,
    diff: bool | None,
) -> tuple[Path, Path, bool]:
    """Layer explicit CLI values over the resolved `[check]`/`[global]`.

    File precedence: explicit `FILE1`/`FILE2` > explicit `--example` >
    configured files. A lone explicit `FILE1` derives `FILE1.example` (the
    configured second file is *not* mixed in). `--diff` / `--no-diff` win
    over `config`; `None` (neither given) uses `config.check.diff`.
    """
    resolved = resolve_check_config(config)

    first = file1 if file1 is not None else resolved.file1
    if file2 is not None:
        second = file2
    elif example is not None:
        second = example
    elif file1 is not None:
        second = file1.parent / f"{file1.name}.example"
    else:
        second = resolved.file2

    effective_diff = diff if diff is not None else resolved.diff
    return first, second, effective_diff


@main.command()
@click.argument(
    "file1",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    required=False,
)
@click.argument(
    "file2",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    required=False,
)
@click.option(
    "-e",
    "--example",
    "example",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Forma alternativa de informar o segundo arquivo (compatibilidade).",
)
@click.option(
    "--diff/--no-diff",
    "--dif/--no-dif",
    "diff",
    default=None,
    help="Lista as variáveis divergentes (--no-diff só o resumo; padrão: config).",
)
@click.pass_context
def check(
    ctx: click.Context,
    file1: Path | None,
    file2: Path | None,
    example: Path | None,
    diff: bool | None,
) -> None:
    """Compara as variáveis declaradas em dois arquivos dotenv.

    Compara apenas os nomes das chaves — valores nunca são lidos nem
    exibidos. Não modifica nenhum arquivo.

    \b
    Sem argumentos:      arquivos da configuração (padrão .env / .env.example)
    Com um argumento:    FILE1 e FILE1 + ".example"
    Com dois argumentos: exatamente FILE1 e FILE2

    `--example` (`-e`) é uma forma alternativa/compatível de informar o
    segundo arquivo; não pode ser combinada com FILE2. `--diff` /
    `--no-diff` vencem a configuração; sem nenhum dos dois, usa
    `[check].diff`.

    Exit codes: 0 sincronizados, 1 divergências, 2 erro de leitura/parsing.
    """
    if file2 is not None and example is not None:
        raise click.UsageError(
            "não é possível informar FILE2 e --example ao mesmo tempo."
        )

    try:
        first, second, effective_diff = _resolve_check_inputs(
            ctx.obj["config"], file1, file2, example, diff
        )
    except ConfigError as exc:
        raise _InputError(str(exc)) from exc

    try:
        result = compare_env_files(first, second)
    except EnvParseError as exc:
        raise _InputError(str(exc)) from exc
    except FileNotFoundError as exc:
        raise _InputError(str(exc)) from exc

    if result.is_synced:
        click.echo(f"✓ {first} e {second} estão sincronizados.")
        return

    _report_check(result, first, second, effective_diff)
    ctx.exit(1)


if __name__ == "__main__":
    main()
