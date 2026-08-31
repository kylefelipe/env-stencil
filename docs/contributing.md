# Contribuindo

Obrigado pelo interesse em melhorar o `envstencil`!

## Ambiente

{% include "dev_install.md" %}

## Tarefas

O projeto usa [taskipy](https://github.com/taskipy/taskipy) — rode com
`poetry run task <nome>`:

| Tarefa | O que faz |
| --- | --- |
| `test` | `task lint` + `pytest` + cobertura (`coverage html`) |
| `lint` | `black --check` + `isort --check` |
| `fmt`  | aplica `isort` + `black` |
| `docs` | `mkdocs serve` |

Rode `poetry run task fmt` antes de commitar e `poetry run task test` antes de
abrir o PR.

## Convenções

- Formatação: `black` + `isort`, linha 79, aspas duplas.
- Docstrings públicas em estilo Google (renderizadas pelo mkdocstrings).
- Mensagens de erro do CLI em português.
- Lógica nova entra primeiro em `core.py` (pura, testável) e só depois é
  exposta no `cli.py`.
- `poetry run mkdocs build --strict` precisa passar sem warning.

As regras completas estão em
[`CLAUDE.md`]({{ config.repo_url }}/blob/main/CLAUDE.md).

## Pull request

1. Faça um fork e crie um branch a partir de `main`.
2. `poetry run task fmt` e `poetry run task test` devem passar.
3. Atualize a documentação afetada (`docs/`, `README.md`).
4. Abra o PR descrevendo a mudança.
