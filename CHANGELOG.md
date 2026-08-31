# Changelog

Todas as mudanças relevantes deste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
e este projeto segue o [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [Unreleased]

### Security

- Linhas do `.env` que o parser não reconhece deixam de ser copiadas para o
  `.env.example`. A geração agora falha de forma segura — erro claro, código de
  saída diferente de zero no CLI e nenhum arquivo escrito ou sobrescrito —,
  evitando que conteúdo potencialmente sensível vaze para o stencil.

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

[Unreleased]: https://github.com/kylefelipe/env-stencil/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/kylefelipe/env-stencil/releases/tag/v0.1.0
