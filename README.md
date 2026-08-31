<p align="center">
  <img src="https://raw.githubusercontent.com/kylefelipe/env-stencil/main/images/logos/envstencil-wordmark.png" alt="EnvStencil" width="320">
</p>

<p align="center">
  Gere um <code>.env.example</code> seguro a partir do seu <code>.env</code>, automaticamente.
</p>

<p align="center">
  📖 <a href="https://env-stencil.readthedocs.io/pt/latest/">Documentação completa</a>
</p>

# EnvStencil

[![Documentation Status](https://app.readthedocs.org/projects/env-stencil/badge/?version=latest)](https://env-stencil.readthedocs.io/en/latest/?badge=latest)
[![CI](https://github.com/kylefelipe/env-stencil/actions/workflows/ci.yml/badge.svg)](https://github.com/kylefelipe/env-stencil/actions/workflows/ci.yml)
[![codecov](https://codecov.io/github/kylefelipe/env-stencil/graph/badge.svg?token=WTXDCQU4O2)](https://codecov.io/github/kylefelipe/env-stencil)
[![PyPI](https://img.shields.io/pypi/v/envstencil)](https://pypi.org/project/envstencil/)


Sempre quando estamos desenvolvendo, é comum a gente criar um arquivo `.env` com as variáveis de ambiente necessárias e depois ter de gerar um arquivo `.env.example` para que outros desenvolvedores possam criar o seu próprio `.env` a partir dele.

O problema é que essa é uma tarefa muito chata e repetitiva, então o `envstencil` foi criado para automatizar esse processo.

Caso o arquivo `.env` contenha variáveis que não precisam ser sobrescritas no `.env.example`, você pode adicionar o comentário `# envstencil:keep` na linha da variável que deseja manter ou na linha anterior.

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

Com o repositório já clonado: `pip install .` (ou `poetry install`).

## Uso

```bash
# Gera .env.example a partir de .env no diretório atual
envstencil generate

# Especificar arquivo de origem e destino
envstencil generate .env.production -o .env.production.example

# Ou, gerando a partir do .env padrão
envstencil generate -o .env.production.example

# Placeholder customizado
envstencil generate --placeholder "CHANGE_ME"

# Sobrescrever arquivo existente
envstencil generate --force
```

## Exemplo

Entrada (`.env`):

```bash
# Banco de dados
DATABASE_URL=postgres://user:pass@localhost:5432/mydb
STRIPE_SECRET_KEY=sk_live_abc123
```

Saída (`.env.example`):

```bash
# Banco de dados
DATABASE_URL=your_value_here
STRIPE_SECRET_KEY=your_value_here
```

## Desenvolvimento

Requer **Poetry 2.0+**. Os grupos `dev` e `doc` são opcionais — `poetry install`
sozinho instala só o runtime:

```bash
poetry install --with dev,doc
```

Tarefas, convenções e fluxo de PR: **[Contribuindo](https://env-stencil.readthedocs.io/pt/latest/contributing/)**.
