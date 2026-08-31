# Contribuindo

O guia completo — setup do ambiente, tarefas, convenções e fluxo de PR — está
na documentação:

**<https://env-stencil.readthedocs.io/pt/latest/contributing/>**

## O essencial

```bash
poetry install --with dev,doc   # requer Poetry 2.0+
poetry run task fmt             # formata (black + isort)
poetry run task test            # lint + testes + cobertura
```

Abra o PR a partir de um branch novo, com `fmt` e `test` passando, e atualize a
documentação afetada.
