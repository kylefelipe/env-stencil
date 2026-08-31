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

{% include "example.md" %}

## Instalação

{% include "install.md" %}

## Uso rápido

Dentro de um projeto com um `.env`:

```bash
{{ commands.run }} generate
```

Isso escreve um `.env.example` ao lado do `.env`.

## Próximos passos

- [**Modo de uso (CLI)**](cli_usage.md) — todas as opções, a diretiva
  `# envstencil:keep`, e exemplos de entrada e saída.
- [**Referência da API**](api/index.md) — usar o `envstencil` como biblioteca
  (`parse_env_file`, `render_stencil`, `generate_example`).
