# envstencil - Claude Guidelines

## 1. Regras críticas (SEMPRE seguir)
- Nunca commitar arquivos `.env` reais ou qualquer valor sensível de exemplo
- Todo valor no `.env.example` gerado deve usar o placeholder configurado (padrão: `your_value_here`) — nunca vazar o valor original. Única exceção: pares explicitamente marcados com `# envstencil:keep` (inline ou na linha de cima), cujo valor real é mantido de propósito
- Manter compatibilidade com Python >= 3.10 (ver `pyproject.toml`, `requires-python`)
- Rodar `poetry run task test` (ou `poetry run pytest`) antes de considerar qualquer mudança em `core.py` concluída

## 2. Visão geral do projeto
- Pacote Python que gera um `.env.example` seguro a partir de um `.env`
- Stack: Python puro (stdlib `re`, `pathlib`, `dataclasses`) + `click` para CLI
- Build/gestão: Poetry 2.x (build-backend `poetry-core`); metadados em `[project]` (PEP 621), grupos `dev`/`doc` em `[tool.poetry.group.*]`
- Estrutura:
  - `src/envstencil/core.py` — parsing do `.env` (`parse_env_file`) e geração do stencil (`render_stencil`, `generate_example`)
  - `src/envstencil/cli.py` — comando `envstencil generate [SOURCE] [-o OUTPUT] [-p PLACEHOLDER] [-f/--force] [-b/--collapse-blank-lines]`
  - `tests/test_core.py` — testes com `pytest`, usando fixture `tmp_path`
- Fluxo de dados: arquivo `.env` → `parse_env_file` (lista de `EnvLine`) → `render_stencil` (substitui valores por placeholder, preserva comentários/blank lines e valores de pares marcados com `# envstencil:keep`) → grava em `.env.example`

## 3. Como trabalhar aqui
- Ambiente de dev: `poetry install` (grupos `dev` e `doc` entram por padrão; `--without doc` para pular)
- Testes: `poetry run task test` (`pytest -v`); cobertura: `poetry run task cov`
- Lint/format: `poetry run task lint` / `poetry run task fmt` (`blue` + `isort`, linha 79)
- Docs: `poetry run task docs` (`mkdocs serve`)
- Após mexer no `pyproject.toml`, rodar `poetry lock` e commitar o `poetry.lock`
- Instalar localmente para testar o CLI: `envstencil generate` dentro de um diretório com `.env`
- Ao adicionar uma nova opção de tratamento de valores (ex.: mascarar só secrets), manter `DEFAULT_PLACEHOLDER` como comportamento padrão atual e expor a nova opção via flag no CLI, sem quebrar a API pública de `core.py`

## 4. Convenções
- Manter `EnvLine` como dataclass simples (kind: comment/blank/pair/unknown; campos `inline_comment` e `keep`)
- Comentário inline que documenta um par (`KEY=valor # descrição`) é separado do valor em `_split_inline_comment` e re-anexado no stencil; só o valor vira placeholder
- Regex de parsing (`_KEY_VALUE_RE`) deve continuar tolerando prefixo `export ` e espaços ao redor do `=`
- Diretiva `# envstencil:keep` (regex `_KEEP_MARKER_RE`, case-insensitive): vale como comentário inline no par ou como comentário isolado na linha de cima (aplicada ao próximo par, tolerando blank lines)
- A própria diretiva `envstencil:keep` nunca aparece no stencil: linha isolada só com a diretiva é descartada; inline, é removida via `_strip_keep_marker`, que preserva o resto do comentário e normaliza para um único espaço antes do `#`. Par renderizado sempre como `{prefix}{key}={valor_ou_placeholder}{inline_comment}`
- Formatação de saída fica em `render_stencil` (ex.: `collapse_blank_lines` via `_collapse_blank_lines`), opt-in por parâmetro e exposta por flag no CLI; sem a flag, a estrutura do `.env` é espelhada 1:1
- Mensagens de erro do CLI em português (ver `cli.py`)
- Novas funcionalidades entram primeiro em `core.py` (lógica pura, testável) e depois são expostas via `cli.py`

## 5. O que evitar
- Não usar `eval`/`exec` para parsear valores do `.env`
- Não adicionar dependências pesadas — o projeto é intencionalmente enxuto (`click` é a única dependência de runtime)
- Não sobrescrever `.env.example` sem `--force`
