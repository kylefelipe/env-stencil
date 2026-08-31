<p align="center">
  <img src="images/logos/envstencil-wordmark.svg" alt="EnvStencil" width="320">
</p>

<p align="center">
  Gere um <code>.env.example</code> seguro a partir do seu <code>.env</code>, automaticamente.
</p>

# EnvStencil

Sempre quando estamos desenvolendo, é comum a gente criar um arquivo `.env` com as variáveis de ambiente necessárias e depois ter de gerar um arquivo `.env.example` para que outros desenvolvedores possam criar o seu próprio `.env` a partir dele.

O problema é que essa é uma tarefa muito chata e repetitiva, então o `envstencil` foi criado para automatizar esse processo.

Caso o arquivo `.env` contenha variáveis que não precisam ser sobreescritas no `.env.example`, você pode adicionar o comentário `# envstencil:keep` na linha da variável que deseja manter ou na linha anterior.

## Instalação

- Utilizando o poetry

    ```bash
    poetry install
    ```

- Utilizando o pip

    ```bash
    pip install -e .
    ```

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

- Utilizando o poetry (2.0+)

    ```bash
    # instala o projeto + o extra "dev" (pytest)
    poetry install --extras dev
    poetry run pytest
    ```

- Utilizando o pip

    ```bash
    pip install -e ".[dev]"
    pytest
    ```
