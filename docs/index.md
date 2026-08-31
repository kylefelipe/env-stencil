![Logo do Projeto](assets/envstencil-wordmark.png){ width="600px" }

# EnvStencil

> Gere um `.env.example` seguro a partir do seu `.env`, automaticamente.

O **envstencil** lê o seu `.env` e escreve um `.env.example` onde todos os
valores viram um placeholder — comentários, linhas em branco e a ordem das
chaves são preservados. Assim você versiona o template sem nunca vazar um
segredo.

## Por que

Manter o `.env.example` em dia na mão é chato e fácil de esquecer: entra uma
variável nova e ninguém atualiza o exemplo, ou — pior — um valor real vaza num
commit. O `envstencil` gera o arquivo a partir da fonte de verdade: o seu
`.env`.

## Num relance

**`.env`**

```bash
# Banco de dados
DATABASE_URL=postgres://user:pass@localhost:5432/app
POOL_SIZE=10  # tamanho do pool
APP_ENV=production  # envstencil:keep
SECRET_KEY=s3cr3t-nao-compartilhe
```

**`.env.example`** (gerado)

```bash
# Banco de dados
DATABASE_URL=your_value_here
POOL_SIZE=your_value_here  # tamanho do pool
APP_ENV=production
SECRET_KEY=your_value_here
```

- Cada valor vira o placeholder (`your_value_here` por padrão).
- Comentários de documentação e a estrutura do arquivo continuam iguais.
- Linhas marcadas com `# envstencil:keep` mantêm o valor real — para defaults
  públicos como `APP_ENV`, `LOG_LEVEL`, `PORT` — e a diretiva não aparece na
  saída.

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

## Uso rápido

Dentro de um projeto com um `.env`:

```bash
envstencil generate
```

Isso escreve um `.env.example` ao lado do `.env`.

## Próximos passos

- [**Modo de uso (CLI)**](cli_usage.md) — todas as opções, a diretiva
  `# envstencil:keep`, e exemplos de entrada e saída.
- [**Referência da API**](api/index.md) — usar o `envstencil` como biblioteca
  (`parse_env_file`, `render_stencil`, `generate_example`).
