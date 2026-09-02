# Modo de uso (CLI)

O `envstencil` expõe um único comando, `generate`, que lê um arquivo `.env` e
escreve um `.env.example` seguro: todos os valores viram um placeholder,
enquanto comentários, linhas em branco e a ordem das chaves são preservados.

## Instalação

{% include "install.md" %}

## Uso básico

Por padrão, o `envstencil` lê o `.env` do diretório atual e escreve um
`.env.example` ao lado dele:

```bash
{{ commands.run }} generate
```

Isso cria um `.env.example` ao lado do `.env`.

{% include "example.md" %}

## Mantendo valores com `# envstencil:keep`

Às vezes um valor no `.env` é um default público, não um segredo (ex.:
`APP_ENV`, `LOG_LEVEL`, `PORT`). Marque a linha e o valor real é mantido no
`.env.example`.

Inline, no próprio par:

```bash
APP_ENV=production  # envstencil:keep
```

Ou na linha **acima** do par (útil quando o par já tem outro comentário):

```bash
# envstencil:keep
LOG_LEVEL=info
```

A diretiva `# envstencil:keep` nunca aparece no arquivo gerado. Se a linha
também tiver um comentário de documentação, só a diretiva é removida (e o
espaço antes do `#` é normalizado para um só):

```bash
# .env
WORKERS=4  # nº de processos  # envstencil:keep

# .env.example
WORKERS=4 # nº de processos
```

## Comentários de documentação

Comentários inline são preservados mesmo nos valores mascarados, então o
`.env.example` continua explicando cada variável:

```bash
# .env
TIMEOUT=30  # segundos até desistir de uma request

# .env.example
TIMEOUT=your_value_here  # segundos até desistir de uma request
```

## Valores multi-linha

Valores entre aspas (simples ou duplas) que ocupam várias linhas reais são
reconhecidos como **um único par** e mascarados normalmente — nenhuma linha
interna aparece na saída:

```bash
# .env
PRIVATE_KEY="-----BEGIN PRIVATE KEY-----
conteudo-secreto
-----END PRIVATE KEY-----"  # chave local

# .env.example
PRIVATE_KEY=your_value_here  # chave local
```

O comentário depois da aspa final é preservado. `# envstencil:keep` também
funciona (inline ou na linha acima) e, nesse caso, o valor multi-linha é
mantido por inteiro.

Se a aspa **nunca fecha**, a geração aborta com erro — o envstencil não tenta
adivinhar onde o valor termina.

## Sintaxe suportada

O envstencil entende o suficiente da sintaxe dotenv para localizar pares com
segurança:

- `KEY=valor`, com `export` opcional;
- chaves `[A-Za-z_][A-Za-z0-9_.-]*` — aceita `.` e `-` (ex.: `my.app.key`,
  `my-setting`);
- aspas simples e duplas, inclusive multi-linha; dentro de aspas duplas, `\"`
  não encerra o valor;
- comentários `#`, de linha inteira e inline, preservados;
- diretiva `# envstencil:keep`.

**Não** são interpretados: expansão de `${VAR}`, execução de comandos,
interpolação de shell, heredoc, nem o conteúdo do valor em si (que é sempre
mascarado). Qualquer linha fora dessa sintaxe **interrompe a geração** em vez
de ser copiada para o `.env.example`.

## Escolhendo origem e destino

```bash
# origem diferente do .env padrão
{{ commands.run }} generate .env.production

# destino explícito
{{ commands.run }} generate .env.production -o .env.production.example
```

Sem `-o`, o destino é `<origem>.example` no mesmo diretório
(`.env` → `.env.example`).

## Placeholder customizado

```bash
{{ commands.run }} generate -p CHANGE_ME
```

## Atualizando um `.env.example` existente

Há três modos, todos pelo mesmo comando:

| Comando | Comportamento |
| ------- | ------------- |
| `{{ commands.run }} generate` | cria o arquivo **só se ele ainda não existir**; se existir, aborta sem tocar em nada |
| `{{ commands.run }} generate --force` | **regenera e sobrescreve** o `.env.example` por completo |
| `{{ commands.run }} generate --append` | **preserva** o `.env.example` e acrescenta ao final só as chaves do `.env` que ainda faltam |

Sem flags, num arquivo que já existe:

```console
$ {{ commands.run }} generate
Error: .env.example já existe. Use --force para sobrescrever ou --append para adicionar apenas as novas variáveis.
```

### `--append`

Compara pela **chave** (nunca pelo conteúdo da linha) e nunca duplica uma
variável já presente. O conteúdo existente — comentários, ordem, placeholders,
espaços, seções feitas pela equipe — não é reformatado; as novas entradas
entram no fim, na ordem em que aparecem no `.env`, mascaradas com o
placeholder (a diretiva `# envstencil:keep` continua valendo).

```bash
# .env
DATABASE_URL=postgres://user:pass@localhost/db
REDIS_URL=redis://localhost:6379
SMTP_HOST=smtp.example.com
SMTP_PASSWORD=super-secret
```

```bash
# .env.example  (antes)
# Database
DATABASE_URL=your_value_here

# Cache
REDIS_URL=your_value_here
```

```console
$ {{ commands.run }} generate --append
✅ .env.example atualizado.

2 novas variáveis adicionadas:
  + SMTP_HOST
  + SMTP_PASSWORD
```

```bash
# .env.example  (depois)
# Database
DATABASE_URL=your_value_here

# Cache
REDIS_URL=your_value_here

SMTP_HOST=your_value_here
SMTP_PASSWORD=your_value_here
```

Se **nenhuma** variável estiver faltando, o arquivo não é reescrito:

```console
$ {{ commands.run }} generate --append
✓ .env.example já está atualizado.
```

Se o `.env.example` **ainda não existir**, `--append` gera o arquivo completo,
como um `generate` normal. `--append` e `--force` não podem ser usados juntos.

## Limpando linhas em branco

`-b` / `--collapse-blank-lines` reduz sequências de duas ou mais linhas em
branco a uma só — útil quando remover diretivas `# envstencil:keep` deixa
buracos no arquivo:

```bash
{{ commands.run }} generate -b
```

## Referência das opções

A lista abaixo é gerada automaticamente a partir de
[`envstencil/cli.py`]({{ config.repo_url }}/blob/main/src/envstencil/cli.py).

::: mkdocs-click
    :module: envstencil.cli
    :command: main
    :prog_name: envstencil
    :style: table
    :depth: 2
