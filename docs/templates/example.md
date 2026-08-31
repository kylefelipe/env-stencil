**Entrada — `.env`:**

```bash
# Banco de dados
DATABASE_URL=postgres://user:pass@localhost:5432/app
POOL_SIZE=10  # tamanho do pool

APP_ENV=production  # envstencil:keep

# envstencil:keep
LOG_LEVEL=info
SECRET_KEY=s3cr3t-nao-compartilhe
TIMEOUT=30  # segundos até desistir de uma request
```

**Saída — `.env.example`:**

```bash
# Banco de dados
DATABASE_URL=your_value_here
POOL_SIZE=your_value_here  # tamanho do pool

APP_ENV=production

LOG_LEVEL=info
SECRET_KEY=your_value_here
TIMEOUT=your_value_here  # segundos até desistir de uma request
```

Repare que:

- Cada valor foi trocado pelo placeholder (`your_value_here` por padrão).
- Comentários e linhas em branco continuam onde estavam.
- `APP_ENV` e `LOG_LEVEL` mantiveram o valor real (diretiva `# envstencil:keep`),
  e a diretiva não aparece na saída.
- O comentário de documentação de `POOL_SIZE` e `TIMEOUT` foi preservado.
