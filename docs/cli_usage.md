# Modo de uso (CLI)

O `envstencil` tem dois comandos: `generate`, que lê um arquivo `.env` e
escreve um `.env.example` seguro (todos os valores viram um placeholder,
enquanto comentários, linhas em branco e a ordem das chaves são preservados),
e `check`, que só compara os nomes das variáveis de dois arquivos dotenv.
Origem, destino e o padrão de algumas flags podem vir de um arquivo de
configuração (ver a seção **Configuração**).

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

O `generate` aceita até dois argumentos posicionais, com a mesma estrutura do
`check`:

```bash
{{ commands.run }} generate                       # arquivos da configuração
{{ commands.run }} generate FILE1                 # FILE1  e  FILE1 + ".example"
{{ commands.run }} generate FILE1 FILE2           # exatamente FILE1 e FILE2
```

- **Sem argumento:** origem e destino vêm da configuração (padrão `.env` e
  `.env.example` — ver **Configuração**).
- **Um argumento:** o destino é o primeiro + `.example`, no mesmo diretório
  (`.env.production` → `.env.production.example`); o `file2` da configuração
  **não** é usado.
- **Dois argumentos:** usa exatamente esses dois caminhos — nenhuma convenção
  de sufixo nem valor de configuração é aplicado.

Compatibilidade: `-o` / `--output` continua sendo uma forma alternativa de
informar o segundo arquivo. Não pode ser combinado com `FILE2` (erro de uso).
A precedência do destino é: `FILE2` posicional > `--output` > `FILE1.example`
> configuração.

```bash
{{ commands.run }} generate .env.production
{{ commands.run }} generate .env.production .env.production.example
{{ commands.run }} generate .env.production .env.production.example --force
{{ commands.run }} generate .env.production --output custom.example
```

Caminhos e comportamento (`--force` / `--append` / `[generate].behaviour`)
são resolvidos de forma independente.

## Placeholder customizado

```bash
{{ commands.run }} generate -p CHANGE_ME
```

## Atualizando um `.env.example` existente

O `generate` tem um único conceito de comportamento diante de um destino que
**já existe**, com três valores — `fail`, `force` e `append`:

| Comportamento | O que faz |
| ------------- | --------- |
| `fail` (padrão) | cria o arquivo **só se ele ainda não existir**; se existir, aborta sem tocar em nada |
| `force` | **regenera e sobrescreve** o `.env.example` por completo |
| `append` | **preserva** o `.env.example` e acrescenta ao final só as chaves do `.env` que ainda faltam |

O valor efetivo vem de `[generate].behaviour` na configuração (padrão `fail` —
ver **Configuração**). Na linha de comando, `--force` e `--append` são
**overrides explícitos** que vencem a configuração:

| Comando | Resultado |
| ------- | --------- |
| `{{ commands.run }} generate` | usa o `behaviour` da configuração |
| `{{ commands.run }} generate --force` | `force`, seja qual for a configuração |
| `{{ commands.run }} generate --append` | `append`, seja qual for a configuração |

Não existe `--behaviour` nem `--fail`: por enquanto não há como, pela linha de
comando, voltar a `fail` quando a configuração pede `force` ou `append` — use
`--config` apontando para um arquivo com `behaviour = "fail"`, ou ajuste o
`.envstencil.toml`.

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

## Verificando sincronização

`{{ commands.run }} check` compara **os nomes das variáveis** declaradas em
dois arquivos dotenv e diz se estão em dia. É **somente leitura**: nunca cria,
altera nem corrige nenhum arquivo — e nunca lê nem imprime valores.

### Quais arquivos são comparados

```bash
{{ commands.run }} check                    # .env  e  .env.example
{{ commands.run }} check FILE1              # FILE1  e  FILE1 + ".example"
{{ commands.run }} check FILE1 FILE2        # exatamente FILE1 e FILE2
{{ commands.run }} check FILE1 FILE2 --diff # o mesmo, listando as divergências
```

- **Sem argumento:** os dois arquivos vêm da configuração (padrão `.env` e
  `.env.example` no diretório atual — ver **Configuração**).
- **Um argumento:** o segundo arquivo é o primeiro + `.example` (mesma
  convenção do `generate`); o `file2` da configuração **não** é usado.
- **Dois argumentos:** compara exatamente esses dois — nenhuma convenção nem
  valor de configuração é aplicado.

Compatibilidade: `{{ commands.run }} check FILE1 --example FILE2` (`-e`)
continua funcionando. Não combine `--example` com o segundo posicional. A
precedência do segundo arquivo é: `FILE2` explícito > `--example` > `file2` da
configuração.

### Caso típico: equipe

```text
git pull
↓
o .env.example recebeu chaves novas
↓
o .env local continua sem elas
↓
envstencil check  →  avisa antes de você subir a aplicação
```

Sincronizado:

```console
$ {{ commands.run }} check
✓ .env e .env.example estão sincronizados.
```

Com divergências, a saída resumida diz quantas e sugere `--diff`:

```console
$ {{ commands.run }} check
⚠ Foram encontradas diferenças entre .env e .env.example.

2 variáveis ausentes no .env.
1 variável ausente no .env.example.

Use --diff para ver os detalhes.
```

`--diff` (alias: `--dif`) lista os nomes — `+` para o que o `.env.example`
espera e falta no `.env`, `-` para o que existe no `.env` e não está
documentado. `--no-diff` (`--no-dif`) força só o resumo. Sem nenhum dos dois,
vale o `diff` da configuração (padrão: só o resumo — ver **Configuração**):

```console
$ {{ commands.run }} check --diff
⚠ Foram encontradas diferenças entre .env e .env.example.

Ausentes no .env:
  + SMTP_HOST
  + SMTP_PASSWORD

Ausentes no .env.example:
  - LOCAL_DEBUG
```

Quando o primeiro arquivo tem variáveis que faltam no segundo, o próximo
passo costuma ser `{{ commands.run }} generate --append` — mas `check` nunca
faz isso sozinho.

**Exit codes** (úteis em CI / pre-commit):

| Código | Situação |
| ------ | -------- |
| `0` | os dois arquivos declaram o mesmo conjunto de variáveis |
| `1` | há divergências |
| `2` | erro de leitura/parsing (arquivo ausente, linha não reconhecida, aspa não fechada) |

## Configuração

Os padrões de origem/destino, do comportamento do `generate` (`behaviour`) e
de `--diff` podem vir de um arquivo de configuração TOML, então quem usa o
`envstencil` sempre no mesmo projeto não precisa repetir as flags.

### Fontes, da menor para a maior precedência

1. **Defaults internos** — `.env` / `.env.example`, `behaviour = "fail"`, sem `--diff`.
2. **Config global do usuário** — `$XDG_CONFIG_HOME/envstencil/config.toml`
   (ou `~/.config/envstencil/config.toml`).
3. **`pyproject.toml`** — seção `[tool.envstencil]`.
4. **`.envstencil.toml`**.
5. **Arquivo de `--config`**, quando informado.
6. **Argumentos e flags da linha de comando** — sempre vencem.

Cada camada sobrescreve a anterior campo a campo: definir só `[check] diff`
num arquivo não apaga o `file1` herdado de outra camada. `false` é um valor
explícito e vence `true` de uma camada inferior.

### Onde o `pyproject.toml` e o `.envstencil.toml` são procurados

Os dois são procurados **a partir do diretório atual e depois nos diretórios
pais**, até a raiz do sistema de arquivos. Assim o `envstencil` roda de dentro
de um subdiretório do projeto e ainda encontra a configuração na raiz dele:

```text
projeto/
├── pyproject.toml
├── .envstencil.toml
└── src/
    └── app/         ← `envstencil` rodando aqui usa os arquivos da raiz
```

Detalhes da busca:

- **Cada nome é procurado de forma independente** — o `pyproject.toml` e o
  `.envstencil.toml` podem ser encontrados em diretórios diferentes.
- **Só a ocorrência mais próxima de cada nome é usada.** Vários
  `.envstencil.toml` em diretórios ancestrais **não** são empilhados; o mais
  próximo do diretório atual vence e os demais são ignorados. O mesmo vale
  para o `pyproject.toml`.
- A busca não usa `.git` nem qualquer outra marca de "raiz de projeto" como
  limite — sobe até a raiz do filesystem.
- O arquivo de `--config` e a config global do usuário **não** participam
  dessa busca: `--config` é usado exatamente como informado e a config global
  vem só do caminho XDG.

Exemplo com os dois arquivos em diretórios diferentes:

```text
workspace/
├── pyproject.toml
└── projeto/
    ├── .envstencil.toml
    └── src/            ← rodando aqui
```

Rodando em `workspace/projeto/src`, o `envstencil` usa
`workspace/pyproject.toml` e `workspace/projeto/.envstencil.toml`.

### Seções e chaves

```toml
# .envstencil.toml (ou config.toml do usuário)

[global]           # padrões compartilhados pelos dois comandos
file1 = ".env"             # origem / primeiro arquivo
file2 = ".env.example"     # destino / segundo arquivo

[generate]         # sobrescreve [global] só para o generate
file1 = ".env"
file2 = ".env.example"
behaviour = "fail"         # "fail" (padrão) | "force" | "append"

[check]            # sobrescreve [global] só para o check
file1 = ".env"
file2 = ".env.example"
diff = false
```

Todas as chaves são opcionais. `[generate]` / `[check]` só precisam do que
diferem de `[global]`.

`behaviour` controla o que o `generate` faz quando o destino **já existe**:

- `"fail"` — gera só se não existir; se existir, aborta (padrão).
- `"force"` — regenera e sobrescreve o destino.
- `"append"` — preserva o destino e acrescenta só as variáveis ausentes.

Qualquer outro valor (ou um valor que não seja string) é erro de
configuração. A chave antiga `force = true` **não** é mais aceita.

No `pyproject.toml` as mesmas seções ficam sob `tool.envstencil`:

```toml
[tool.envstencil.global]
file1 = ".env"
file2 = ".env.example"

[tool.envstencil.check]
diff = true

[tool.envstencil.generate]
behaviour = "force"
```

### `--config`

```bash
{{ commands.run }} --config config/ci.toml check
```

O arquivo de `--config` é só mais uma camada (a de maior precedência entre os
arquivos), não substitui as demais. Ao contrário das fontes autodescobertas,
um caminho de `--config` que não existe é um erro.

### Exemplos

`.envstencil.toml` de um projeto cujo dotenv se chama `.env.local`:

```toml
[global]
file1 = ".env.local"
file2 = ".env.local.example"

[check]
diff = true
```

```console
$ {{ commands.run }} check
⚠ Foram encontradas diferenças entre .env.local e .env.local.example.

Ausentes no .env.local:
  + NEW_API_KEY
```

```console
$ {{ commands.run }} check --no-diff   # a flag vence o [check] diff = true
⚠ Foram encontradas diferenças entre .env.local e .env.local.example.

1 variável ausente no .env.local.

Use --diff para ver os detalhes.
```

`pyproject.toml` que sempre regenera o exemplo:

```toml
[tool.envstencil.generate]
behaviour = "force"
```

```console
$ {{ commands.run }} generate            # sobrescreve sem pedir --force
✅ .env.example gerado a partir de .env
$ {{ commands.run }} generate --append   # override da CLI: faz append em vez de sobrescrever
✅ .env.example atualizado.
```

Não há flag para forçar `fail` a partir da CLI; para isso, aponte `--config`
para um arquivo com `behaviour = "fail"` ou ajuste o `.envstencil.toml`.

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
