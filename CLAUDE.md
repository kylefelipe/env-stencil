# envstencil - Claude Guidelines

## 1. Regras críticas (SEMPRE seguir)
- Nunca commitar arquivos `.env` reais ou qualquer valor sensível de exemplo
- Todo valor no `.env.example` gerado deve usar o placeholder configurado (padrão: `your_value_here`) — nunca vazar o valor original. Única exceção: pares explicitamente marcados com `# envstencil:keep` (inline ou na linha de cima), cujo valor real é mantido de propósito
- Fail-safe: linha que o parser não classifica (`kind == "unknown"`) NUNCA é copiada. `render_stencil` aborta com `UnsafeEnvLineError` e `generate_example` não grava nem sobrescreve nada. Filosofia: entendeu com segurança → sanitiza; não entendeu → aborta. Proibido fallback que copie conteúdo cru
- Mensagem de erro sobre linha insegura não imprime o conteúdo da linha — só `line_number` + `_safe_preview` (que devolve apenas o comprimento)
- Manter compatibilidade com Python >= 3.10 (ver `pyproject.toml`, `requires-python`)
- Rodar `poetry run task test` (ou `poetry run pytest`) antes de considerar qualquer mudança em `core.py` concluída

## 2. Visão geral do projeto
- Pacote Python que gera um `.env.example` seguro a partir de um `.env`
- Stack: Python puro (stdlib `re`, `pathlib`, `dataclasses`) + `click` para CLI
- Build/gestão: Poetry 2.x (build-backend `poetry-core`); metadados em `[project]` (PEP 621), grupos `dev`/`doc` em `[tool.poetry.group.*]`, ambos `optional = true` (só instalam com `--with`)
- Estrutura:
  - `src/envstencil/core.py` — parsing do `.env` (`parse_env_file`) e geração do stencil (`render_stencil`, `generate_example`)
  - `src/envstencil/cli.py` — comando `envstencil generate [SOURCE] [-o OUTPUT] [-p PLACEHOLDER] [-f/--force] [-b/--collapse-blank-lines]`
  - `tests/test_core.py`, `tests/test_cli.py` — testes com `pytest` (`tmp_path`; CLI via `click.testing.CliRunner`)
  - `docs/` — site MkDocs: `index.md` (landing), `cli_usage.md` (guia do CLI), `contributing.md` (setup/tasks/convenções), `api/` (autodoc de `core`), `templates/` (partials do mkdocs-macros)
  - `.github/workflows/` — `ci.yml` (testes + cobertura no Codecov, em push/PR) e `publica-pypi.yml` (publica no PyPI ao criar GitHub Release)
- Fluxo de dados: arquivo `.env` → `parse_env_file` (lista de `EnvLine`, cada uma com `line_number`) → `render_stencil` (substitui valores por placeholder, preserva comentários/blank lines e valores marcados com `# envstencil:keep`; aborta com `UnsafeEnvLineError` em linha `unknown`) → grava em `.env.example`

## 3. Como trabalhar aqui
- Ambiente de dev: `poetry install --with dev,doc` (grupos são `optional`; `poetry install` puro traz só o runtime)
- Testes: `poetry run task test` — encadeia `task lint` (pre_test), `pytest -s -x --cov=envstencil -vv` e `coverage html` (post_test)
- Lint/format: `poetry run task lint` (check) / `poetry run task fmt` (aplica) — `black` + `isort`, linha 79, aspas duplas; rodar `fmt` antes de commitar
- `pytest` roda com `--doctest-modules`: qualquer `>>>` em docstring vira teste
- Docs: `poetry run task docs` (`mkdocs serve`); `poetry run mkdocs build --strict` precisa passar sem warning (griffe/links/macros)
- Conteúdo de doc repetido vai para partials em `docs/templates/*.md`, incluídos com `{% include "nome.md" %}` (nome puro — `include_dir` já aponta para `docs/templates`; não viram páginas). Partials atuais: `install.md`, `dev_install.md`, `example.md`
- Nos docs, usar as variáveis macro em vez de hardcode: `{{ config.repo_url }}` (URL do repo) e `{{ commands.run }}` (= `poetry run envstencil`, definido em `mkdocs.yml` → `extra.commands`)
- Após mexer no `pyproject.toml`, rodar `poetry lock` e commitar o `poetry.lock`
- Docs publicadas no Read the Docs (build via `.readthedocs.yaml`, que instala com `poetry install --with doc`); mudança no build de docs precisa refletir nesse arquivo
- Release: bump da `version` em `pyproject.toml` → push no `main` → criar GitHub Release `vX.Y.Z`. O `publica-pypi.yml` builda, testa e publica no PyPI via Trusted Publishing (OIDC, sem token; environment `pypi`)
- Instalar localmente para testar o CLI: `envstencil generate` dentro de um diretório com `.env`
- Ao adicionar uma nova opção de tratamento de valores (ex.: mascarar só secrets), manter `DEFAULT_PLACEHOLDER` como comportamento padrão atual e expor a nova opção via flag no CLI, sem quebrar a API pública de `core.py`

## 4. Convenções
- Manter `EnvLine` como dataclass simples (kind: comment/blank/pair/unknown; campos `inline_comment`, `keep`, `line_number` 1-based). Campo novo entra com default para não quebrar construção existente
- `UnsafeEnvLineError` (subclasse de `ValueError`) é levantada em `render_stencil`, não em `parse_env_file` — o parser continua inspecionável (dá pra listar todas as linhas `unknown`). O CLI captura e converte em `click.ClickException` (exit ≠ 0)
- Comentário inline que documenta um par (`KEY=valor # descrição`) é separado do valor em `_split_inline_comment` e re-anexado no stencil; só o valor vira placeholder
- Regex de parsing (`_KEY_VALUE_RE`) deve continuar tolerando prefixo `export ` e espaços ao redor do `=`
- Diretiva `# envstencil:keep` (regex `_KEEP_MARKER_RE`, case-insensitive): vale como comentário inline no par ou como comentário isolado na linha de cima (aplicada ao próximo par, tolerando blank lines)
- A própria diretiva `envstencil:keep` nunca aparece no stencil: linha isolada só com a diretiva é descartada; inline, é removida via `_strip_keep_marker`, que preserva o resto do comentário e normaliza para um único espaço antes do `#`. Par renderizado sempre como `{prefix}{key}={valor_ou_placeholder}{inline_comment}`
- Formatação de saída fica em `render_stencil` (ex.: `collapse_blank_lines` via `_collapse_blank_lines`), opt-in por parâmetro e exposta por flag no CLI; sem a flag, a estrutura do `.env` é espelhada 1:1
- Mensagens de erro do CLI em português (ver `cli.py`)
- Novas funcionalidades entram primeiro em `core.py` (lógica pura, testável) e depois são expostas via `cli.py`
- Docstrings públicas em estilo Google (`Args:`/`Returns:`/`Raises:`/`Attributes:`), com todo parâmetro anotado documentado — são renderizadas por `mkdocstrings` e qualquer descompasso quebra `mkdocs build --strict`
- Texto `help=` de opção Click sem `<...>`: o `mkdocs-click` renderiza como HTML e engole o trecho entre `<>` (referir o argumento como `SOURCE`, não `<source>`)
- Ao adicionar/alterar flag do CLI: a tabela de opções em `docs/cli_usage.md` é gerada por `mkdocs-click`, mas atualizar a assinatura na seção 2, os exemplos em `docs/cli_usage.md` e o `README.md`
- Guia de contribuidor: `docs/contributing.md` é a versão completa (no site/RTD); `CONTRIBUTING.md` na raiz é um stub curto que o GitHub exibe e aponta pro RTD. Manter os três (com este arquivo) coerentes

## 5. O que evitar
- Não usar `eval`/`exec` para parsear valores do `.env`
- Não adicionar dependências pesadas — o projeto é intencionalmente enxuto (`click` é a única dependência de runtime)
- Não sobrescrever `.env.example` sem `--force`
