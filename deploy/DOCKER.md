# study-system — Docker runtime

## Start

```bash
cd /home/pieye/Container/study-system

# stop legacy user unit
systemctl --user disable --now study-system.service 2>/dev/null || true

docker compose up --build -d
curl -sS http://127.0.0.1:8765/api/health
```

## Paths (env / mounts)

| Env | Default in container | Host mount |
|-----|----------------------|------------|
| `VAULT_ROOT` | `/vault` | `Obsidian Vault` |
| `HERMES_HOME` | `/hermes` | `~/.hermes` |
| `STUDY_DATA_ROOT` | `/hermes/home` | (inside Hermes home) |
| `STUDY_DB_PATH` | `/hermes/home/study-system.sqlite3` | same |
| `CHROMA_PATH` | `/hermes/mem0/chroma-jina` | same |
| `CLIPROXY_BASE` | `http://cli-proxy-api:8317/v1` | join `cliproxyapi_default` |
| `CLIPROXY_KEY_FILE` | `/secrets/cliproxy/api_key` | `~/.config/cliproxy/api_key` |

Optional env file (host): `~/.hermes/home/.study-system.env` (DeepSeek key, auth password, etc.). Compose `environment:` overrides `CLIPROXY_*` for in-network DNS.

Listens on **127.0.0.1:8765** so homepage-edge `/_svc/study-system/` keeps working.
