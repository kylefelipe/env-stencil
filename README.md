<p align="center">
  <img src="images/logos/envstencil-wordmark.svg" alt="EnvStencil" width="320">
</p>

<p align="center">
  Gere um <code>.env.example</code> seguro a partir do seu <code>.env</code>, automaticamente.
</p>

# EnvStencil

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

Requer **Poetry 2.0+**. Os grupos `dev` (testes, lint) e `doc` são
instalados por padrão:

```bash
poetry install
```

Tarefas (via [taskipy](https://github.com/taskipy/taskipy)):

```bash
poetry run task test    # pytest -v
poetry run task cov     # cobertura
poetry run task lint    # black --check + isort --check
poetry run task fmt     # aplica isort + black
poetry run task docs    # mkdocs serve
```

Para pular a documentação: `poetry install --without doc`.
