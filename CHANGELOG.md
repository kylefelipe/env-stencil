# Changelog

Todas as mudanças relevantes deste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
e este projeto segue o [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [Unreleased]

## [0.3.0] - 2026-09-01

### Added

- Nova opção `envstencil generate --append` para adicionar ao `.env.example`
  apenas as variáveis presentes no `.env` que ainda faltam, preservando todo o
  conteúdo existente (comentários, ordem, placeholders, seções). Compara por
  chave, nunca duplica e nunca copia valores (salvo `# envstencil:keep`). Se o
  destino não existir, gera o arquivo completo; se nada faltar, não reescreve.
- Novo comando `envstencil check` para verificar se `.env` e `.env.example`
  declaram o mesmo conjunto de variáveis. É somente leitura, compara só nomes
  de chave (nunca valores) e sai com código diferente de zero quando há
  divergências (útil em CI). A opção `--diff` (alias `--dif`) lista os nomes
  ausentes em cada arquivo.

### Changed

- A mensagem de erro de `generate` quando o `.env.example` já existe agora
  cita as duas saídas: `--force` (regenera) e `--append` (completa).

## [0.2.0] - 2026-08-31

### Added

- Suporte a valores entre aspas (simples ou duplas) que ocupam várias linhas
  reais: são reconhecidos como um único par e mascarados no `.env.example`,
  sem que nenhuma linha interna vaze. Comentário após a aspa final e
  `# envstencil:keep` continuam funcionando.
- Chaves com `.` e `-` (ex.: `my.app.key`, `my-setting`) passam a ser
  reconhecidas e mascaradas.

### Security

- Linhas do `.env` que o parser não reconhece deixam de ser copiadas para o
  `.env.example`. A geração agora falha de forma segura — erro claro, código de
  saída diferente de zero no CLI e nenhum arquivo escrito ou sobrescrito —,
  evitando que conteúdo potencialmente sensível vaze para o stencil.
- Valor entre aspas que nunca é fechado interrompe a geração em vez de
  consumir o resto do arquivo.
- O `.env.example` passa a ser escrito de forma atômica: uma falha durante a
  geração nunca deixa o arquivo pela metade.

## [0.1.0] - 2026-08-31

### Added

- Geração de um `.env.example` a partir de um `.env`, com todos os valores
  substituídos por um placeholder (`envstencil generate [SOURCE]`).
- Placeholder configurável com `-p` / `--placeholder` (padrão:
  `your_value_here`).
- Preservação de comentários, comentários inline, linhas em branco e da ordem
  das chaves no arquivo gerado.
- Suporte ao prefixo `export` em linhas `KEY=valor`.
- Diretiva `# envstencil:keep` (inline no par ou na linha acima) para manter o
  valor real de variáveis que não são segredo; a diretiva não aparece na saída.
- Opção `-f` / `--force` para sobrescrever um `.env.example` existente.
- Opção `-b` / `--collapse-blank-lines` para reduzir sequências de linhas em
  branco a uma só.
- Pacote instalável via `pip` ou `poetry` e publicado no PyPI, expondo o
  comando `envstencil`.
- Documentação no Read the Docs e integração contínua com testes e cobertura.

[Unreleased]: https://github.com/kylefelipe/env-stencil/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/kylefelipe/env-stencil/releases/tag/v0.2.0...v0.3.0
[0.2.0]: https://github.com/kylefelipe/env-stencil/releases/tag/v0.1.0...v0.2.0
[0.1.0]: https://github.com/kylefelipe/env-stencil/releases/tag/v0.1.0
