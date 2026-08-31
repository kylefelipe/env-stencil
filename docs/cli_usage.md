# Modo de uso (CLI)

O `envstencil` expõe um único comando, `generate`, que lê um arquivo `.env` e
escreve um `.env.example` seguro: todos os valores viram um placeholder,
enquanto comentários, linhas em branco e a ordem das chaves são preservados.

## Instalação

{% include "install.md" %}

## Uso básico

Por padrão, o `envstencil` lê o `.env` do diretório atual e escreve um
`.env.example` ao lado dele:

```bash
{{ commands.run }} generate
```

Isso cria um `.env.example` ao lado do `.env`.

{% include "example.md" %}

## Mantendo valores com `# envstencil:keep`

Às vezes um valor no `.env` é um default público, não um segredo (ex.:
`APP_ENV`, `LOG_LEVEL`, `PORT`). Marque a linha e o valor real é mantido no
`.env.example`.

Inline, no próprio par:

```bash
APP_ENV=production  # envstencil:keep
```

Ou na linha **acima** do par (útil quando o par já tem outro comentário):

```bash
# envstencil:keep
LOG_LEVEL=info
```

A diretiva `# envstencil:keep` nunca aparece no arquivo gerado. Se a linha
também tiver um comentário de documentação, só a diretiva é removida (e o
espaço antes do `#` é normalizado para um só):

```bash
# .env
WORKERS=4  # nº de processos  # envstencil:keep

# .env.example
WORKERS=4 # nº de processos
```

## Comentários de documentação

Comentários inline são preservados mesmo nos valores mascarados, então o
`.env.example` continua explicando cada variável:

```bash
# .env
TIMEOUT=30  # segundos até desistir de uma request

# .env.example
TIMEOUT=your_value_here  # segundos até desistir de uma request
```

## Escolhendo origem e destino

```bash
# origem diferente do .env padrão
{{ commands.run }} generate .env.production

# destino explícito
{{ commands.run }} generate .env.production -o .env.production.example
```

Sem `-o`, o destino é `<origem>.example` no mesmo diretório
(`.env` → `.env.example`).

## Placeholder customizado

```bash
{{ commands.run }} generate -p CHANGE_ME
```

## Sobrescrevendo um `.env.example` existente

Por segurança, o comando não sobrescreve um arquivo que já existe:

```console
$ {{ commands.run }} generate
Error: .env.example já existe. Use --force para sobrescrever.
```

Passe `-f` / `--force` para permitir:

```bash
{{ commands.run }} generate --force
```

## Limpando linhas em branco

`-b` / `--collapse-blank-lines` reduz sequências de duas ou mais linhas em
branco a uma só — útil quando remover diretivas `# envstencil:keep` deixa
buracos no arquivo:

```bash
{{ commands.run }} generate -b
```

## Referência das opções

A lista abaixo é gerada automaticamente a partir de
[`envstencil/cli.py`]({{ config.repo_url }}/blob/main/src/envstencil/cli.py).

::: mkdocs-click
    :module: envstencil.cli
    :command: main
    :prog_name: envstencil
    :style: table
    :depth: 2
