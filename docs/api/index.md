# Referência da API

Além do CLI, o `envstencil` pode ser usado como biblioteca. Toda a lógica
pública vive em [`envstencil.core`](core.md):

| Objeto | Para quê |
| --- | --- |
| [`parse_env_file`][envstencil.core.parse_env_file] | Lê um `.env` e devolve a lista de `EnvLine` (comentários, linhas em branco e pares), já resolvendo a diretiva `# envstencil:keep`. |
| [`render_stencil`][envstencil.core.render_stencil] | Recebe os `EnvLine` e produz o texto do `.env.example`. |
| [`generate_example`][envstencil.core.generate_example] | Orquestra tudo: lê o `source`, valida e escreve o `destination`. |
| [`EnvLine`][envstencil.core.EnvLine] | Dataclass que descreve cada linha parseada. |

## Exemplo

```python
from pathlib import Path

from envstencil.core import generate_example

generate_example(Path(".env"), Path(".env.example"))
```

Para gerar em memória, sem tocar em disco:

```python
from envstencil.core import parse_env_file, render_stencil

linhas = parse_env_file(Path(".env"))
texto = render_stencil(linhas, collapse_blank_lines=True)
```

Para o uso pela linha de comando, veja [Modo de uso (CLI)](../cli_usage.md).
