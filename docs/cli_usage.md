# Modo de uso (CLI)

O `envstencil` expõe um único comando, `generate`, que lê um arquivo `.env` e
escreve um `.env.example` seguro: todos os valores viram um placeholder,
enquanto comentários, linhas em branco e a ordem das chaves são preservados.

## Instalação

**pip** — do PyPI ou direto do git:

```bash
pip install envstencil
pip install git+https://github.com/kylefelipe/env-stencil.git
```

**Poetry** — adiciona `envstencil` como dependência do seu projeto:

```bash
poetry add envstencil
poetry add git+https://github.com/kylefelipe/env-stencil.git
```

Para desenvolvimento: `poetry install` na raiz do repositório.

## Uso básico

Dentro de um projeto que tenha um `.env`:

```bash
envstencil generate
```

Isso cria um `.env.example` ao lado do `.env`.

**Entrada — `.env`:**

```bash
# Banco de dados
DATABASE_URL=postgres://user:pass@localhost:5432/app
POOL_SIZE=10  # tamanho do pool

APP_ENV=production  # envstencil:keep

# envstencil:keep
LOG_LEVEL=info
SECRET_KEY=s3cr3t-nao-compartilhe
TIMEOUT=30  # segundos até desistir de uma request
```

**Saída — `.env.example`:**

```bash
# Banco de dados
DATABASE_URL=your_value_here
POOL_SIZE=your_value_here  # tamanho do pool

APP_ENV=production

LOG_LEVEL=info
SECRET_KEY=your_value_here
TIMEOUT=your_value_here  # segundos até desistir de uma request
```

Repare que:

- Cada valor foi trocado pelo placeholder.
- Comentários e linhas em branco continuam onde estavam.
- `APP_ENV` e `LOG_LEVEL` mantiveram o valor real (têm a diretiva
  `# envstencil:keep`), e a diretiva não aparece na saída.
- O comentário de documentação de `POOL_SIZE` e `TIMEOUT` foi preservado.

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
envstencil generate .env.production

# destino explícito
envstencil generate .env.production -o .env.production.example
```

Sem `-o`, o destino é `<origem>.example` no mesmo diretório
(`.env` → `.env.example`).

## Placeholder customizado

```bash
envstencil generate -p CHANGE_ME
```

## Sobrescrevendo um `.env.example` existente

Por segurança, o comando não sobrescreve um arquivo que já existe:

```console
$ envstencil generate
Error: .env.example já existe. Use --force para sobrescrever.
```

Passe `-f` / `--force` para permitir:

```bash
envstencil generate --force
```

## Limpando linhas em branco

`-b` / `--collapse-blank-lines` reduz sequências de duas ou mais linhas em
branco a uma só — útil quando remover diretivas `# envstencil:keep` deixa
buracos no arquivo:

```bash
envstencil generate -b
```

## Referência das opções

A lista abaixo é gerada automaticamente a partir de
[`envstencil/cli.py`](https://github.com/kylefelipe/env-stencil/blob/main/src/envstencil/cli.py).

::: mkdocs-click
    :module: envstencil.cli
    :command: main
    :prog_name: envstencil
    :style: table
    :depth: 2
