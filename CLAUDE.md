# envstencil - Claude Guidelines

## 1. Regras críticas (SEMPRE seguir)
- Nunca commitar arquivos `.env` reais ou qualquer valor sensível de exemplo
- Todo valor no `.env.example` gerado deve usar o placeholder configurado (padrão: `your_value_here`) — nunca vazar o valor original. Única exceção: pares explicitamente marcados com `# envstencil:keep` (inline ou na linha de cima), cujo valor real é mantido de propósito
- Fail-safe: linha que o parser não classifica (`kind == "unknown"`) NUNCA é copiada — `render_stencil` aborta com `UnsafeEnvLineError`. Valor entre aspas que não fecha aborta com `UnterminatedQuotedValueError` (ambos herdam de `EnvParseError`). `generate_example` não grava nem sobrescreve nada. Filosofia: entendeu com segurança → sanitiza; não entendeu → aborta. Proibido fallback que copie conteúdo cru
- Erros de parsing nunca imprimem o valor/conteúdo da linha — só `line_number`, `key` (quando estrutural) e, para `unknown`, `_safe_preview` (só o comprimento). Novo caso de parsing exige teste que confirme isso
- `generate_example` e `append_missing_variables` escrevem de forma atômica (`_atomic_write`: temp + `os.replace`); qualquer falha aborta antes da escrita e não deixa `.env.example` pela metade nem `.tmp`
- Projeto é **CLI-only**: nada de GUI/TUI/dashboard/prompts interativos/watch mode
- Manter compatibilidade com Python >= 3.10 (ver `pyproject.toml`, `requires-python`)
- Rodar `poetry run task test` (ou `poetry run pytest`) antes de considerar qualquer mudança em `core.py` concluída

## 2. Visão geral do projeto
- Pacote Python que gera um `.env.example` seguro a partir de um `.env`
- Stack: Python puro (stdlib `re`, `pathlib`, `dataclasses`) + `click` para CLI
- Build/gestão: Poetry 2.x (build-backend `poetry-core`); metadados em `[project]` (PEP 621), grupos `dev`/`doc` em `[tool.poetry.group.*]`, ambos `optional = true` (só instalam com `--with`)
- Estrutura:
  - `src/envstencil/core.py` — parsing do `.env` (`parse_env_file`), geração do stencil (`render_stencil`, `generate_example`) e atualização incremental (`append_missing_variables` → `AppendResult`; helper `get_keys`)
  - `src/envstencil/cli.py` — comando `envstencil generate [SOURCE] [-o OUTPUT] [-p PLACEHOLDER] [-f/--force] [-a/--append] [-b/--collapse-blank-lines]`
  - `tests/test_core.py`, `tests/test_cli.py` — testes com `pytest` (`tmp_path`; CLI via `click.testing.CliRunner`)
  - `docs/` — site MkDocs: `index.md` (landing), `cli_usage.md` (guia do CLI), `contributing.md` (setup/tasks/convenções), `api/` (autodoc de `core`), `templates/` (partials do mkdocs-macros)
  - `.github/workflows/` — `ci.yml` (testes + cobertura no Codecov, em push/PR) e `publica-pypi.yml` (publica no PyPI ao criar GitHub Release)
- Fluxo de dados: arquivo `.env` → `parse_env_file` (lista de `EnvLine`, cada uma com `line_number`/`end_line_number`; um valor entre aspas não fechado na 1ª linha consome as linhas seguintes até fechar e vira um único `pair`) → `render_stencil` (substitui valores por placeholder, preserva comentários/blank lines e valores marcados com `# envstencil:keep`, inclusive multi-linha; aborta com `UnsafeEnvLineError` em linha `unknown`) → grava em `.env.example` (atômico)

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
- Versionamento, changelog e releases: ver seção 6
- Instalar localmente para testar o CLI: `envstencil generate` dentro de um diretório com `.env`
- Ao adicionar uma nova opção de tratamento de valores (ex.: mascarar só secrets), manter `DEFAULT_PLACEHOLDER` como comportamento padrão atual e expor a nova opção via flag no CLI, sem quebrar a API pública de `core.py`

## 4. Convenções
- Manter `EnvLine` como dataclass simples (kind: comment/blank/pair/unknown; campos `inline_comment`, `keep`, `line_number` 1-based, `end_line_number` só para multi-linha). Campo novo entra com default para não quebrar construção existente
- Erros de parsing herdam de `EnvParseError(ValueError)`: `UnsafeEnvLineError` (levantada em `render_stencil`, parser fica inspecionável) e `UnterminatedQuotedValueError` (em `parse_env_file`). O CLI captura `EnvParseError` e converte em `click.ClickException` (exit ≠ 0)
- Multi-linha entre aspas: `parse_env_file` consome linhas físicas via `_quote_closed` (mesma semântica de escape do `_split_inline_comment`) e produz um único `pair`; não usar regex gigante nem interpretar o conteúdo
- Comentário inline que documenta um par (`KEY=valor # descrição`) é separado do valor em `_split_inline_comment` e re-anexado no stencil; só o valor vira placeholder
- Regex de parsing (`_KEY_VALUE_RE`) tolera prefixo `export `, espaços ao redor do `=` e chaves com `.`/`-` (1º char ainda `[A-Za-z_]`). Se a linha casa inequivocamente como par, o valor NÃO é validado semanticamente — só mascarado
- Diretiva `# envstencil:keep` (regex `_KEEP_MARKER_RE`, case-insensitive): vale como comentário inline no par ou como comentário isolado na linha de cima (aplicada ao próximo par, tolerando blank lines)
- A própria diretiva `envstencil:keep` nunca aparece no stencil: linha isolada só com a diretiva é descartada; inline, é removida via `_strip_keep_marker`, que preserva o resto do comentário e normaliza para um único espaço antes do `#`. Par renderizado sempre como `{prefix}{key}={valor_ou_placeholder}{inline_comment}`
- Formatação de saída fica em `render_stencil` (ex.: `collapse_blank_lines` via `_collapse_blank_lines`), opt-in por parâmetro e exposta por flag no CLI; sem a flag, a estrutura do `.env` é espelhada 1:1
- Três modos de `generate`: sem flag cria só se o destino não existir (senão aborta — a mensagem cita `--force` e `--append`); `--force` regenera/sobrescreve tudo; `--append` preserva o destino e só acrescenta chaves ausentes. `--append` nunca implica `--force`; os dois juntos → `click.UsageError`
- `append_missing_variables` (core): compara por **chave** (`get_keys`, só `kind == "pair"`), nunca duplica, novas entradas na ordem do `.env`, mascaradas com o placeholder (respeitando `# envstencil:keep`). Conteúdo existente do `.env.example` é preservado byte-a-byte; separador de no máx. 1 linha em branco antes do bloco novo; nada a adicionar → não reescreve. Destino inexistente → gera o stencil completo. Reusa `parse_env_file` nos dois arquivos (sem 2º parser); `unknown` em qualquer um dos dois → aborta
- CLI de `--append` nunca imprime valores — só nomes de chave (`+ KEY`)
- Mensagens de erro do CLI em português (ver `cli.py`)
- Novas funcionalidades entram primeiro em `core.py` (lógica pura, testável) e depois são expostas via `cli.py`
- Docstrings públicas em estilo Google (`Args:`/`Returns:`/`Raises:`/`Attributes:`), com todo parâmetro anotado documentado — são renderizadas por `mkdocstrings` e qualquer descompasso quebra `mkdocs build --strict`
- Texto `help=` de opção Click sem `<...>`: o `mkdocs-click` renderiza como HTML e engole o trecho entre `<>` (referir o argumento como `SOURCE`, não `<source>`)
- Ao adicionar/alterar flag do CLI: a tabela de opções em `docs/cli_usage.md` é gerada por `mkdocs-click`, mas atualizar a assinatura na seção 2, os exemplos em `docs/cli_usage.md` e o `README.md`
- Guia de contribuidor: `docs/contributing.md` é a versão completa (no site/RTD); `CONTRIBUTING.md` na raiz é um stub curto que o GitHub exibe e aponta pro RTD. Manter os três (com este arquivo) coerentes

## 5. O que evitar
- Não usar `eval`/`exec` para parsear valores do `.env`
- Não adicionar dependências pesadas — o projeto é intencionalmente enxuto (`click` é a única dependência de runtime)
- `--append` só **acrescenta** chaves ausentes: não remove variáveis antigas, não reordena nem reformata o `.env.example`, não edita o `.env`. Comandos `check`/`sync`, watch mode e integração com Git não fazem parte do escopo
- Não sobrescrever `.env.example` sem `--force`

## 6. Versionamento, changelog e releases
- `CHANGELOG.md` (raiz) segue [Keep a Changelog 1.1.0](https://keepachangelog.com/pt-BR/1.1.0/); o projeto segue [Semantic Versioning](https://semver.org/lang/pt-BR/). Tags e releases usam prefixo `v` (`vX.Y.Z`)
- Toda mudança relevante atualiza o `CHANGELOG.md` **no mesmo trabalho/PR que a implementa**. "Relevante" = altera comportamento público, segurança, API, CLI ou funcionalidades. Entra em `## [Unreleased]`, na categoria certa:
  - nova funcionalidade → `Added`; mudança de comportamento → `Changed`; correção de bug → `Fixed`
  - correção relacionada a secrets/exposição → `Security`; remoção → `Removed`; depreciação → `Deprecated`
  - mudança puramente interna, sem impacto perceptível para o usuário → não precisa entrar
- Só registrar o que já existe no código. Feature planejada não entra como `Added`/`Fixed`/etc.; roadmap não é changelog
- Entradas curtas, em português, orientadas ao usuário — descrevem impacto/comportamento, não detalhe interno. Ex.: "Linhas `.env` não reconhecidas interrompem a geração para evitar vazar conteúdo sensível", não "alterado o `if` de `render_stencil`"
- A `version` no `pyproject.toml` só muda ao preparar uma release ou quando pedido explicitamente — nunca durante uma feature comum
- Enquanto `0.x`: patch (`0.x.Y`) para correções pequenas e compatíveis; minor (`0.X.0`) para funcionalidades novas ou mudança relevante de comportamento. Mesmo em `0.x`, avaliar com atenção o que pode afetar quem já usa
- Ao preparar uma release: (1) revisar `[Unreleased]`; (2) definir a versão por SemVer; (3) criar `## [X.Y.Z] - YYYY-MM-DD` e mover as entradas de `[Unreleased]` para lá; (4) recriar `## [Unreleased]` vazio no topo; (5) atualizar os links de comparação no fim do arquivo; (6) bump da `version` no `pyproject.toml`; (7) push no `main` e criar o GitHub Release `vX.Y.Z` — o `publica-pypi.yml` builda, testa e publica no PyPI via Trusted Publishing (OIDC, environment `pypi`); (8) conferir consistência entre `CHANGELOG.md`, `pyproject.toml`, tag/release e documentação
- Antes de dar por concluída qualquer mudança relevante, checar "o `CHANGELOG.md` precisa ser atualizado?" e resolver isso antes de fechar; manter `poetry run task lint` e `poetry run pytest` verdes
