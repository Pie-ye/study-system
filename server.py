"""
study-system 後端伺服器
- 提供靜態檔案服務
- Teacher 對話代理（預設走 CLIProxy OAuth 訂閱 AI：Grok / GPT）
- Obsidian 筆記寫入
"""

import os, json, asyncio, re, base64, hashlib, hmac, secrets, sqlite3
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import httpx

# === CONFIG ===
# All host paths are overridable so the same code runs under systemd or Docker.
VAULT_ROOT = Path(
    os.environ.get("VAULT_ROOT", "/home/pieye/Container/Obsidian Vault")
).expanduser()
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE = os.environ.get("DEEPSEEK_BASE", "https://api.deepseek.com/v1")
CLIPROXY_BASE = os.environ.get("CLIPROXY_BASE", "http://127.0.0.1:8317/v1").rstrip("/")
CLIPROXY_KEY_FILE = Path(
    os.environ.get(
        "CLIPROXY_KEY_FILE",
        str(Path.home() / ".config/cliproxy/api_key"),
    )
).expanduser()
DEFAULT_PROVIDER = os.environ.get("STUDY_AI_PROVIDER", "grok")
DEFAULT_MODEL = os.environ.get("STUDY_AI_MODEL", "grok-4.5")

# OpenAI-compatible routes. openai/grok use host CLIProxy OAuth subscriptions.
# deepseek keeps direct API-key path. anthropic/gemini are not oauth-wired yet.
AI_PROVIDER_ROUTES = {
    "openai": {
        "name": "OpenAI (訂閱)",
        "auth_mode": "oauth",
        "base_url": CLIPROXY_BASE,
        "default_model": "gpt-5.6-luna",
        "models": {
            "gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna",
            "gpt-5.5", "gpt-5.4", "gpt-5.4-mini",
        },
    },
    "grok": {
        "name": "Grok (訂閱)",
        "auth_mode": "oauth",
        "base_url": CLIPROXY_BASE,
        "default_model": "grok-4.5",
        "models": {
            "grok-4.5", "grok-4.3", "grok-4.20-0309-reasoning",
            "grok-4.20-0309-non-reasoning", "grok-4.20-multi-agent-0309",
            "grok-3-mini", "grok-3-mini-fast",
        },
    },
    "deepseek": {
        "name": "DeepSeek",
        "auth_mode": "api-key",
        "base_url": DEEPSEEK_BASE.rstrip("/"),
        "default_model": "deepseek-v4-pro",
        "models": {"deepseek-v4-pro", "deepseek-v4-flash"},
    },
}


def _load_cliproxy_api_key() -> str:
    env = (os.environ.get("CLIPROXY_API_KEY") or "").strip()
    if env:
        return env
    try:
        return CLIPROXY_KEY_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _resolve_ai_route(provider: str | None, model: str | None) -> tuple[str, dict, str, str]:
    """Return (provider_id, route, model_id, bearer_token)."""
    pid = (provider or DEFAULT_PROVIDER or "grok").strip().lower()
    if pid not in AI_PROVIDER_ROUTES:
        raise HTTPException(status_code=400, detail=f"unsupported provider: {pid}")
    route = AI_PROVIDER_ROUTES[pid]
    mid = (model or "").strip() or route["default_model"]
    if mid not in route["models"]:
        # Allow exact default even if list drifts; otherwise reject unknown ids.
        if mid != route["default_model"]:
            raise HTTPException(status_code=400, detail=f"unsupported model for {pid}: {mid}")
    if route["auth_mode"] == "oauth":
        token = _load_cliproxy_api_key()
        if not token:
            raise HTTPException(status_code=503, detail="CLIProxy API key missing on server")
        return pid, route, mid, token
    if pid == "deepseek":
        token = (DEEPSEEK_API_KEY or "").strip()
        if not token:
            raise HTTPException(status_code=503, detail="DeepSeek API key missing on server")
        return pid, route, mid, token
    raise HTTPException(status_code=501, detail=f"provider {pid} is not available yet")


@asynccontextmanager
async def lifespan(_app):
    _init_study_database()
    _sync_default_user_credentials()
    yield


app = FastAPI(lifespan=lifespan)

# Serve static files
app.mount("/static", StaticFiles(directory="."), name="static")

# === MODELS ===
AI_EFFORT_LEVELS = ("medium", "high", "xhigh")
DEFAULT_EFFORT = os.environ.get("STUDY_AI_EFFORT", "medium").strip().lower()
if DEFAULT_EFFORT not in AI_EFFORT_LEVELS:
    DEFAULT_EFFORT = "medium"


def _normalize_effort(value: str | None) -> str:
    raw = (value or DEFAULT_EFFORT or "medium").strip().lower()
    # Common typos / aliases from UI copy
    aliases = {
        "mideum": "medium",
        "meduim": "medium",
        "mid": "medium",
        "med": "medium",
        "x-high": "xhigh",
        "extra_high": "xhigh",
        "extrahigh": "xhigh",
        "max": "xhigh",
    }
    raw = aliases.get(raw, raw)
    if raw not in AI_EFFORT_LEVELS:
        raise HTTPException(status_code=400, detail=f"unsupported effort: {value}")
    return raw


class ChatRequest(BaseModel):
    messages: list[dict]
    item: dict | None = None  # { title, category, link, note, fetched_content }
    provider: str | None = None  # openai | grok | deepseek
    model: str | None = None
    effort: str | None = None  # medium | high | xhigh → reasoning_effort

class NoteRequest(BaseModel):
    path: str   # relative to vault, e.g. "Hermes筆記/學習/技術架構/xxx.md"
    content: str

class FetchRequest(BaseModel):
    url: str

class LearnCompleteRequest(BaseModel):
    path: str          # note path in vault
    title: str         # item title
    messages: list     # full conversation [{role, content}]
    note_content: str  # user's edited note text
    llm_summary: str   # Teacher's summary (last assistant message)

# === TEACHER SYSTEM PROMPT ===
TEACHER_SYSTEM = """
你是一位名叫 Teacher 的學習引導者。你的任務是主動引導使用者學習，不需等待他們發問。

## 核心原則

1. **主動講解** — 直接開始講解，不要問「你對這個了解多少」或「你有什麼問題」
2. **開放式測驗** — 只出簡答題與申論題，完全不出選擇題（A/B/C/D 選項）
3. **啟發創意** — 每堂課至少出一題發想題，鼓勵橫向思考
4. **即時反饋** — 對使用者的回答給予具體回饋，指出對的地方和可改進方向
5. **進度告知** — 課程結束時明確說「第 N 課完成，明天繼續第 N+1 課」

## 語言與語氣

- 主要使用繁體中文，專有名詞與技術術語可保留英文
- 語氣溫暖且有結構，像一個好的導師
- 適當使用 emoji 讓氣氛輕鬆，但不過度

## 教學流程

### 第一階段：核心教學（主動講解）
直接開始講解核心概念。第一句話就要進入主題，例如：
「今天要學的是 [主題]。核心是 [一句話總結]。先從 [第一個概念] 開始。」

每個概念講解完後，直接出一題簡答或申論題來驗證理解。
**不要問「你理解了嗎？」**——直接出題，從答案判斷。

### 第二階段：發想與延伸
每堂課至少包含一題發想題，鼓勵創意思考。

### 第三階段：重點整理與進度告知
在對話最後，整理一份結構化的重點摘要：

```
## 重點整理

### 核心概念
- ...

### 今日發想
- ...

### 明日預告
- ...
```

然後必須明確告知進度：
📚 第 N 課完成。明天繼續第 N+1 課。

### 第四階段：課程方向微調（每堂課結尾必做）
進度告知之後，用一句話溫柔詢問（不要施壓、不要多題連問）：

【課程調整】
最近有沒有特別想學／想探討的內容？
有的話用一句話告訴我；沒有就回「沒有」或按完成即可。
我會把它排進之後的課，不會打斷你現在的進度節奏。

若使用者在對話中已經提出想學的主題，確認並說明會寫入下一課方向，不必再重複逼問。

## 格式約定

當你想出簡答題時：
【簡答題】
題目：[問題]
請用你自己的話解釋。

當你想出申論題時：
【申論題】
題目：[問題]
請寫下你的想法，越多越好。

當你想出發想題時：
【發想題】
題目：[開放式問題]
如果是你，你會怎麼設計？有沒有不同的做法？

## 重要限制

- 不要問「你對這個了解多少」或「你有什麼問題」
- 不要出選擇題（A/B/C/D 選項）
- 不要問「你理解了嗎？」——直接出題驗證
- 不要一次丟出大量資訊 — 每次聚焦在一個概念
- 如果使用者答錯，不要直接給答案，先引導他們思考
- 使用者說「我不知道」時，給一個提示或類比幫助他們
- 課程結束時必須明確告知進度，不要留懸念
- 課程結束時必須留下「課程調整」入口，讓使用者可改下一課方向
- 若系統提供「使用者指定下一課主題」或「待排入主題」，優先採用，不要無視
""".strip()

# === CHAT ===
def _extract_stream_content(chunk: object) -> str:
    """Extract visible assistant text from OpenAI-compatible stream chunks.

    CLIProxy/Grok may emit reasoning_content before content, and some
    OpenAI-compatible gateways return content as a list of text parts. Only
    visible answer text belongs in the Teacher transcript.
    """
    if not isinstance(chunk, dict):
        return ""
    choices = chunk.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    choice = choices[0]
    if not isinstance(choice, dict):
        return ""
    delta = choice.get("delta")
    if not isinstance(delta, dict):
        delta = choice.get("message")
    if not isinstance(delta, dict):
        return ""
    content = delta.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    return ""


@app.post("/api/chat")
async def chat(req: ChatRequest, request: Request):
    username = _require_authenticated_user(request)
    philosophy_document = _get_document(username, "philosophy")
    messages = [{"role": "system", "content": TEACHER_SYSTEM}]

    # Add item context
    if req.item:
        ctx = f"## 本次學習主題\n- 標題：{req.item.get('title','')}"
        if req.item.get("category"):
            ctx += f"\n- 類別：{req.item['category']}"
        if req.item.get("link"):
            ctx += f"\n- 連結：{req.item['link']}"
        if req.item.get("note"):
            ctx += f"\n- 備註：{req.item['note']}"
        if req.item.get("fetched_content"):
            ctx += f"\n\n## 課程內容（從網址抓取）\n以下是你今天要學的課程的實際內容。請根據這份內容來引導學習：\n\n{req.item['fetched_content']}"
        if req.item.get("memory_summary"):
            ctx += f"\n\n## 學習者背景（從長期記憶讀取）\n以下是關於這個學習者的相關記憶，幫助你了解他/她的背景與偏好：\n\n{req.item['memory_summary']}\n\n請根據這些背景資訊調整教學方式。"
        # Inject philosophy course context if applicable
        if req.item.get("category") == "哲學" and philosophy_document:
            try:
                phil = philosophy_document["data"]
                profile = phil.get("user_profile", {})
                ctx += "\n\n## 哲學課程背景"
                if profile.get("discussed_topics_set"):
                    ctx += f"\n- 已討論過的主題：{'、'.join(profile['discussed_topics_set'])}"
                if profile.get("thinking_style"):
                    ctx += f"\n- 思維風格：{profile['thinking_style']}"
                if profile.get("tension_zones"):
                    ctx += f"\n- 矛盾張力區：{'、'.join(profile['tension_zones'])}"
                if profile.get("preferred_depth"):
                    ctx += f"\n- 偏好深度：{profile['preferred_depth']}"
                if profile.get("recurring_themes"):
                    ctx += f"\n- 反覆主題：{'、'.join(profile['recurring_themes'])}"
                pending = phil.get("pending_topics") or []
                open_pending = [p for p in pending if isinstance(p, dict) and not p.get("consumed")]
                if open_pending:
                    topics = "；".join(
                        str(p.get("topic", "")).strip() for p in open_pending[-5:] if str(p.get("topic", "")).strip()
                    )
                    if topics:
                        ctx += f"\n- 使用者指定、待排入的主題：{topics}"
                planned = (phil.get("lessons") or {}).get(
                    str(phil.get("next_lesson", "")).zfill(2)
                    if str(phil.get("next_lesson", "")).isdigit()
                    else str(phil.get("next_lesson", ""))
                )
                item_title = str(req.item.get("title") or "")
                if planned and planned not in ("待生成",) and planned not in item_title:
                    ctx += f"\n- 本課預設主題：{planned}"
                ctx += (
                    "\n\n請根據以上背景開始這一課的蘇格拉底式討論。"
                    "若本課已有明確主題（標題或預設主題），直接圍繞該主題深入，不要改開無關 classic 問題。"
                    "哲學課不要用選擇題；用反思與日常連結。"
                )
            except Exception:
                pass
        # Cross-course curriculum requests stored on the item / note field
        if req.item.get("curriculum_request"):
            ctx += f"\n\n## 使用者為本課指定的方向\n{req.item['curriculum_request']}\n請優先依此方向調整教學重點。"
        pending_note = str(req.item.get("note") or "")
        if pending_note.startswith("下一課方向：") or "【課程調整】" in pending_note:
            ctx += f"\n\n## 課程調整備註\n{pending_note}"
        messages.append({"role": "user", "content": ctx + "\n\n請開始引導我學習這個主題。"})

    # Add conversation history
    for m in req.messages:
        messages.append({"role": m["role"], "content": m["content"]})

    provider_id, route, model_id, bearer = _resolve_ai_route(req.provider, req.model)
    effort = _normalize_effort(req.effort)
    endpoint = f"{route['base_url']}/chat/completions"
    # Higher effort = more reasoning budget; keep output cap generous for teaching.
    max_tokens = {"medium": 4096, "high": 6144, "xhigh": 8192}[effort]
    request_json = {
        "model": model_id,
        "messages": messages,
        "stream": True,
        "temperature": 0.7,
        "max_tokens": max_tokens,
    }
    # OAuth subscription models (GPT/Grok via CLIProxy) honor reasoning_effort.
    # DeepSeek API-key path ignores unknown fields safely on most gateways; only send for oauth.
    if route.get("auth_mode") == "oauth":
        request_json["reasoning_effort"] = effort

    async def stream():
        answer_content_seen = False
        stream_error_seen = False
        async with httpx.AsyncClient(timeout=180.0 if effort != "medium" else 120.0) as client:
            try:
                async with client.stream(
                    "POST",
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {bearer}",
                        "Content-Type": "application/json",
                    },
                    json=request_json,
                ) as resp:
                    if resp.status_code >= 400:
                        err_body = await resp.aread()
                        err_text = err_body.decode("utf-8", errors="replace")[:300]
                        yield f"data: {json.dumps({'error': f'{provider_id} HTTP {resp.status_code}: {err_text}'})}\n\n"
                        yield "data: [DONE]\n\n"
                        return
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data = line[6:].strip()
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            # Some gateways surface top-level error objects mid-stream.
                            if isinstance(chunk, dict) and chunk.get("error"):
                                err = chunk["error"]
                                msg = err.get("message") if isinstance(err, dict) else str(err)
                                stream_error_seen = True
                                yield f"data: {json.dumps({'error': msg or 'upstream error'})}\n\n"
                                break
                            content = _extract_stream_content(chunk)
                            if content:
                                answer_content_seen = True
                                yield f"data: {json.dumps({'content': content})}\n\n"
                        except json.JSONDecodeError:
                            continue
            except httpx.RequestError as exc:
                stream_error_seen = True
                yield f"data: {json.dumps({'error': f'{provider_id} request failed: {exc}'})}\n\n"
        if not answer_content_seen and not stream_error_seen:
            yield f"data: {json.dumps({'error': f'{provider_id} returned no answer content'})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Study-AI-Provider": provider_id,
            "X-Study-AI-Model": model_id,
            "X-Study-AI-Effort": effort,
        },
    )


@app.get("/api/ai/status")
async def ai_status(request: Request):
    """Report which subscription OAuth route the Teacher will use."""
    _require_authenticated_user(request)
    cliproxy_key = bool(_load_cliproxy_api_key())
    cliproxy_ok = False
    cliproxy_models: list[str] = []
    cliproxy_error = None
    if cliproxy_key:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(
                    f"{CLIPROXY_BASE}/models",
                    headers={"Authorization": f"Bearer {_load_cliproxy_api_key()}"},
                )
                if resp.status_code < 400:
                    cliproxy_ok = True
                    payload = resp.json()
                    cliproxy_models = sorted(
                        m.get("id", "") for m in payload.get("data", []) if m.get("id")
                    )
                else:
                    cliproxy_error = f"HTTP {resp.status_code}"
        except Exception as exc:  # noqa: BLE001 — surface probe failure
            cliproxy_error = str(exc)[:200]
    providers = []
    for pid, route in AI_PROVIDER_ROUTES.items():
        ready = False
        if route["auth_mode"] == "oauth":
            ready = cliproxy_ok
        elif pid == "deepseek":
            ready = bool((DEEPSEEK_API_KEY or "").strip())
        providers.append({
            "id": pid,
            "name": route["name"],
            "auth_mode": route["auth_mode"],
            "default_model": route["default_model"],
            "models": sorted(route["models"]),
            "ready": ready,
        })
    return {
        "status": "ok",
        "default_provider": DEFAULT_PROVIDER,
        "default_model": DEFAULT_MODEL,
        "default_effort": DEFAULT_EFFORT,
        "efforts": list(AI_EFFORT_LEVELS),
        "cliproxy": {
            "base_url": CLIPROXY_BASE,
            "key_configured": cliproxy_key,
            "reachable": cliproxy_ok,
            "error": cliproxy_error,
            "model_count": len(cliproxy_models),
        },
        "providers": providers,
    }

# === NOTE ===
@app.post("/api/note")
async def save_note(req: NoteRequest, request: Request):
    _require_authenticated_user(request)
    # Security: ensure path is within vault
    raw = (req.path or "").strip().replace("\\", "/")
    # Windows-safe: strip spaces on both sides + trailing dots per segment
    # (e.g. category "AI / Agent" produces segments "AI " and " Agent")
    raw = "/".join(seg.strip(" ").rstrip(".") for seg in raw.split("/") if seg.strip())
    if not raw or raw.endswith("/"):
        return JSONResponse({"status": "error", "message": "path must be a file"}, status_code=400)
    safe_path = raw.replace("..", "").lstrip("/")
    if not safe_path or not safe_path.endswith(".md"):
        return JSONResponse({"status": "error", "message": "path must end with .md"}, status_code=400)
    full_path = (VAULT_ROOT / safe_path).resolve()
    try:
        full_path.relative_to(VAULT_ROOT.resolve())
    except ValueError:
        return JSONResponse({"status": "error", "message": "path outside vault"}, status_code=400)

    # Create parent directories
    full_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        full_path.write_text(req.content, encoding="utf-8")
        return JSONResponse({"status": "ok", "path": str(full_path.relative_to(VAULT_ROOT.resolve()))})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

# === COURSE SYNC — read progress JSONs from Hermes ===
HERMES_HOME = Path(os.environ.get("HERMES_HOME", "/home/pieye/.hermes")).expanduser()
# STUDY_DATA_ROOT lets Docker mount only the study data tree without full Hermes.
STUDY_DATA_ROOT = Path(
    os.environ.get("STUDY_DATA_ROOT", str(HERMES_HOME / "home"))
).expanduser()
USERS_PATH = STUDY_DATA_ROOT / "study-system-users.json"
STUDY_DATA_PATH = STUDY_DATA_ROOT / "study-system-data.json"
STUDY_DATA_DIR = STUDY_DATA_ROOT / "study-system-users"
USER_PROGRESS_DIR = STUDY_DATA_ROOT / "study-system-user-progress"
STUDY_DB_PATH = Path(
    os.environ.get("STUDY_DB_PATH", str(STUDY_DATA_ROOT / "study-system.sqlite3"))
).expanduser()
STUDY_DB_SCHEMA_VERSION = 1
STUDY_DOCUMENT_KEYS = {"study", "philosophy"}
STUDY_MAX_DOCUMENT_BYTES = 4 * 1024 * 1024
SESSION_COOKIE = "study_system_session"
SESSION_TTL_SECONDS = 60 * 60 * 24 * 7

# === LOCAL AUTH — server-side credential (FO-1 T2, 2026-08-06) ===
# The legacy client-visible LOCAL_AUTH_SALT / LOCAL_AUTH_PASSWORD_HASH constants were
# removed from index.html. Verification now happens here, server-side only, and the
# credential is derived from LOCAL_AUTH_PASSWORD in the service environment file.
LOCAL_AUTH_PASSWORD = os.environ.get("LOCAL_AUTH_PASSWORD", "").strip()


def _local_auth_salt() -> str:
    # Deterministic salt derived from the configured local-auth password so the
    # credential stays stable across restarts without persisting extra material.
    return hashlib.sha256(("study-system-local-auth:" + LOCAL_AUTH_PASSWORD).encode("utf-8")).hexdigest()[:16]


def _local_auth_hash() -> str:
    if not LOCAL_AUTH_PASSWORD:
        return ""
    digest = hashlib.pbkdf2_hmac(
        "sha256", LOCAL_AUTH_PASSWORD.encode("utf-8"), _local_auth_salt().encode("utf-8"), 200_000
    )
    return base64.b64encode(digest).decode("ascii")


def _sync_default_user_credentials() -> None:
    """Reconcile the default user's stored credential with LOCAL_AUTH_PASSWORD (FO-1 T2)."""
    if not LOCAL_AUTH_PASSWORD:
        return
    _ensure_users_file()
    try:
        payload = json.loads(USERS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    users = payload.get("users")
    if not isinstance(users, list):
        return
    new_salt, new_hash = _local_auth_salt(), _local_auth_hash()
    changed = False
    for user in users:
        if isinstance(user, dict) and user.get("username") == DEFAULT_USER["username"]:
            if user.get("password_salt") != new_salt or user.get("password_hash") != new_hash:
                user["password_salt"] = new_salt
                user["password_hash"] = new_hash
                changed = True
            break
    if changed:
        USERS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

# The first account is provisioned automatically. Additional accounts can be
# added to USERS_PATH by an administrator later; there is intentionally no
# public registration endpoint in this phase.
# The default user's credential is derived at runtime from LOCAL_AUTH_PASSWORD
# (FO-1 T2): no credential-derived literals in source. If the env value is
# unset, provisioning fails closed (no valid hash).
DEFAULT_USER = {
    "username": "pieye",
    "display_name": "pieye",
    "enabled": True,
    "password_salt": _local_auth_salt(),
    "password_hash": _local_auth_hash(),
}


SESSIONS: dict[str, str] = {}


class RevisionConflict(Exception):
    def __init__(self, current: dict | None):
        self.current = current
        super().__init__("document revision conflict")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _db_connect() -> sqlite3.Connection:
    STUDY_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(STUDY_DB_PATH), timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def _init_study_database() -> None:
    with _db_connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_documents (
                username TEXT NOT NULL,
                document_key TEXT NOT NULL,
                schema_version INTEGER NOT NULL DEFAULT 1,
                revision INTEGER NOT NULL DEFAULT 0,
                data_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (username, document_key)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_user_documents_updated
            ON user_documents (username, updated_at)
            """
        )


def _validate_document_key(document_key: str) -> str:
    if document_key not in STUDY_DOCUMENT_KEYS:
        raise ValueError("unsupported document")
    return document_key


def _sanitize_document(data: object) -> dict:
    if not isinstance(data, dict) or isinstance(data, list):
        raise ValueError("document data must be a JSON object")
    clone = json.loads(json.dumps(data, ensure_ascii=False))
    if isinstance(clone.get("items"), list):
        for item in clone["items"]:
            if isinstance(item, dict):
                item.pop("fetched_content", None)
    encoded = json.dumps(clone, ensure_ascii=False, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > STUDY_MAX_DOCUMENT_BYTES:
        raise ValueError("document is too large")
    return clone


def _row_to_document(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    try:
        data = json.loads(row["data_json"])
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("stored document is invalid JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("stored document is not an object")
    return {
        "document": row["document_key"],
        "revision": int(row["revision"]),
        "schema_version": int(row["schema_version"]),
        "updated_at": row["updated_at"],
        "data": data,
    }


def _read_json_file(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return _sanitize_document(value)
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def _legacy_document_data(username: str, document_key: str) -> dict | None:
    """Find the old JSON source used only when the SQLite row does not exist."""
    if document_key == "study":
        user_path = _user_data_path(username)
        value = _read_json_file(user_path)
        if value is not None:
            return value
        if username == DEFAULT_USER["username"]:
            return _read_json_file(STUDY_DATA_PATH)
        return None
    if document_key == "philosophy":
        user_path = _user_philosophy_path(username)
        value = _read_json_file(user_path)
        if value is not None:
            return value
        if username == DEFAULT_USER["username"]:
            return _read_json_file(PHILOSOPHY_PROGRESS_PATH)
    return None


def _get_document(username: str, document_key: str, migrate: bool = True) -> dict | None:
    _validate_document_key(document_key)
    _init_study_database()
    with _db_connect() as conn:
        row = conn.execute(
            "SELECT * FROM user_documents WHERE username = ? AND document_key = ?",
            (username, document_key),
        ).fetchone()
        if row is not None:
            return _row_to_document(row)

        if not migrate:
            return None
        legacy = _legacy_document_data(username, document_key)
        if legacy is None:
            return None
        now = _now_iso()
        encoded = json.dumps(legacy, ensure_ascii=False, separators=(",", ":"))
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            """
            INSERT OR IGNORE INTO user_documents
              (username, document_key, schema_version, revision, data_json, created_at, updated_at)
            VALUES (?, ?, ?, 1, ?, ?, ?)
            """,
            (username, document_key, STUDY_DB_SCHEMA_VERSION, encoded, now, now),
        )
        row = conn.execute(
            "SELECT * FROM user_documents WHERE username = ? AND document_key = ?",
            (username, document_key),
        ).fetchone()
        return _row_to_document(row)


def _document_exists(username: str, document_key: str) -> bool:
    return _get_document(username, document_key, migrate=False) is not None


def _put_document(username: str, document_key: str, data: object, base_revision: int) -> dict:
    _validate_document_key(document_key)
    if not isinstance(base_revision, int) or isinstance(base_revision, bool) or base_revision < 0:
        raise ValueError("base_revision must be a non-negative integer")
    clean_data = _sanitize_document(data)
    encoded = json.dumps(clean_data, ensure_ascii=False, separators=(",", ":"))
    _init_study_database()

    with _db_connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT * FROM user_documents WHERE username = ? AND document_key = ?",
            (username, document_key),
        ).fetchone()
        current = _row_to_document(row)
        current_revision = current["revision"] if current else 0
        if current_revision != base_revision:
            raise RevisionConflict(current)

        now = _now_iso()
        next_revision = current_revision + 1
        if row is None:
            conn.execute(
                """
                INSERT INTO user_documents
                  (username, document_key, schema_version, revision, data_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (username, document_key, STUDY_DB_SCHEMA_VERSION, next_revision, encoded, now, now),
            )
        else:
            conn.execute(
                """
                UPDATE user_documents
                SET schema_version = ?, revision = ?, data_json = ?, updated_at = ?
                WHERE username = ? AND document_key = ? AND revision = ?
                """,
                (
                    STUDY_DB_SCHEMA_VERSION,
                    next_revision,
                    encoded,
                    now,
                    username,
                    document_key,
                    current_revision,
                ),
            )
        saved = conn.execute(
            "SELECT * FROM user_documents WHERE username = ? AND document_key = ?",
            (username, document_key),
        ).fetchone()
        return _row_to_document(saved)  # type: ignore[return-value]


def _document_response(document: dict | None) -> JSONResponse:
    if document is None:
        return JSONResponse(
            {
                "status": "ok",
                "document": "study",
                "revision": 0,
                "schema_version": STUDY_DB_SCHEMA_VERSION,
                "updated_at": None,
                "data": None,
            }
        )
    return JSONResponse({"status": "ok", **document})


def _conflict_response(document_key: str, conflict: RevisionConflict) -> JSONResponse:
    current = conflict.current
    return JSONResponse(
        {
            "status": "conflict",
            "document": document_key,
            "message": "中央資料已被其他裝置更新",
            "current": current,
        },
        status_code=409,
    )


class LoginRequest(BaseModel):
    username: str
    password: str


def _ensure_users_file() -> None:
    """Create the administrator-managed account file with the initial user."""
    if USERS_PATH.exists():
        return
    USERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    USERS_PATH.write_text(
        json.dumps({"version": 1, "registration_open": False, "users": [DEFAULT_USER]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _load_users() -> list[dict]:
    _ensure_users_file()
    try:
        payload = json.loads(USERS_PATH.read_text(encoding="utf-8"))
        users = payload.get("users", []) if isinstance(payload, dict) else []
        return [user for user in users if isinstance(user, dict) and user.get("enabled", True)]
    except (OSError, json.JSONDecodeError):
        return [DEFAULT_USER]


def _password_hash(password: str, salt: str) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000)
    return base64.b64encode(digest).decode("ascii")


def _find_authenticated_user(request: Request) -> str | None:
    token = request.cookies.get(SESSION_COOKIE)
    return SESSIONS.get(token) if token else None


def _require_authenticated_user(request: Request) -> str:
    username = _find_authenticated_user(request)
    if not username:
        raise HTTPException(status_code=401, detail="請先登入")
    return username


def _user_data_path(username: str) -> Path:
    # Usernames are validated at login/account provisioning boundaries. Keep
    # this function defensive because it controls a filesystem path.
    safe_username = re.sub(r"[^a-zA-Z0-9_.-]", "_", username)
    return STUDY_DATA_DIR / f"{safe_username}.json"


def _user_philosophy_path(username: str) -> Path:
    safe_username = re.sub(r"[^a-zA-Z0-9_.-]", "_", username)
    return USER_PROGRESS_DIR / f"{safe_username}-philosophy.json"


def _resolve_philosophy_path(username: str) -> Path:
    user_path = _user_philosophy_path(username)
    if user_path.exists():
        return user_path
    # Preserve the existing single-user philosophy data as pieye's migration source.
    if username == DEFAULT_USER["username"] and PHILOSOPHY_PROGRESS_PATH.exists():
        return PHILOSOPHY_PROGRESS_PATH
    return user_path


@app.post("/api/auth/login")
async def login(req: LoginRequest, response: Response):
    username = req.username.strip()
    if not re.fullmatch(r"[a-zA-Z0-9_.-]{1,64}", username) or len(req.password) > 256:
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")

    account = next((user for user in _load_users() if user.get("username") == username), None)
    if not account:
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")

    actual = _password_hash(req.password, str(account.get("password_salt", "")))
    expected = str(account.get("password_hash", ""))
    if not hmac.compare_digest(actual, expected):
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")

    token = secrets.token_urlsafe(32)
    SESSIONS[token] = username
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=os.environ.get("STUDY_SYSTEM_COOKIE_SECURE", "0") == "1",
        path="/",
    )
    return {"status": "ok", "user": {"username": username, "display_name": account.get("display_name", username)}}


@app.get("/api/auth/me")
async def auth_me(request: Request):
    username = _find_authenticated_user(request)
    if not username:
        return {"status": "ok", "authenticated": False}
    account = next((user for user in _load_users() if user.get("username") == username), None)
    if not account:
        return {"status": "ok", "authenticated": False}
    return {"status": "ok", "authenticated": True, "user": {"username": username, "display_name": account.get("display_name", username)}}


@app.post("/api/auth/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        SESSIONS.pop(token, None)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"status": "ok"}
COURSE_PROGRESS_FILES = {
    "ai-agents-for-beginners": STUDY_DATA_ROOT / "ai-agents-course-progress.json",
    "awesome-architecture": STUDY_DATA_ROOT / "awesome-architecture-progress.json",
    "build-your-own-x": STUDY_DATA_ROOT / "build-your-own-x-progress.json",
    "philosophy": STUDY_DATA_ROOT / "philosophy-progress.json",
}
@app.post("/api/auth/verify")
async def auth_verify(req: LoginRequest):
    """Server-side verification for the static/local auth mode (FO-1 T2).

    Replaces the removed client-side hash check in index.html. Validates against
    the same user store as /api/auth/login but does NOT issue a session cookie;
    the frontend enters offline/local mode on success.
    """
    username = req.username.strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,32}", username) or len(req.password) > 256:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    account = next((user for user in _load_users() if user.get("username") == username), None)
    if not account:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    actual = _password_hash(req.password, str(account.get("password_salt", "")))
    expected = str(account.get("password_hash", ""))
    if not expected or not hmac.compare_digest(actual, expected):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {
        "status": "ok",
        "user": {
            "username": username,
            "display_name": account.get("display_name", username),
            "authMode": "local",
        },
    }


@app.get("/api/sync-courses")
async def sync_courses_preview(request: Request):
    username = _require_authenticated_user(request)
    """回傳所有可同步的課程與章節（不回寫，僅預覽）"""
    courses = {}
    for key, path in COURSE_PROGRESS_FILES.items():
        try:
            if key == "philosophy":
                philosophy_document = _get_document(username, "philosophy")
                # A new account can see the first virtual lesson before its
                # first completion is written to the central document.
                progress = philosophy_document["data"] if philosophy_document else {
                    "course": "philosophy",
                    "next_lesson": 1,
                    "completed": [],
                    "skipped": [],
                    "lessons": {},
                }
            else:
                if not path.exists():
                    courses[key] = {"error": "progress file not found"}
                    continue
                progress = json.loads(path.read_text(encoding="utf-8"))
            completed_raw = progress.get("completed", [])
            skipped_raw = progress.get("skipped", [])
            all_done = set(str(c) for c in list(completed_raw) + list(skipped_raw))
            # Build expanded set for matching lesson keys (which may be "01" or 1)
            completed_set = set()
            for c in all_done:
                completed_set.add(str(c))
                completed_set.add(str(c).zfill(2))
            lessons = progress.get("lessons", {})
            items = []
            if not lessons and key == "philosophy":
                # Create virtual first lesson for empty philosophy course
                next_num = str(progress.get("next_lesson", 1)).zfill(2)
                items.append({
                    "num": next_num,
                    "title": f"🎯 哲學探索 第{next_num}課",
                    "category": "哲學",
                    "link": "",
                    "completed": False,
                })
            for num, title in lessons.items():
                num_str = str(num).zfill(2)
                is_completed = num_str in completed_set or num in completed_set

                if key == "ai-agents-for-beginners":
                    link = f"https://github.com/microsoft/ai-agents-for-beginners/tree/main/{title}/"
                    category = "AI / Agent"
                    item_title = f"AI Agents 第{num_str}課：{title}"
                elif key == "awesome-architecture":
                    # slug is the Chinese title
                    import urllib.parse
                    slug = urllib.parse.quote(title)
                    link = f"https://raw.githubusercontent.com/study8677/awesome-architecture/main/tutorial/{num_str}-{slug}.md"
                    category = "技術架構"
                    item_title = f"Awesome Architecture 第{num_str}章：{title}"
                elif key == "build-your-own-x":
                    lesson_links = progress.get("lesson_links", {})
                    link = lesson_links.get(num_str) or progress.get(
                        "source_base", "https://github.com/codecrafters-io/build-your-own-x"
                    )
                    category = "Build Your Own X"
                    item_title = f"Build Your Own X 第{num_str}課：{title}"
                elif key == "philosophy":
                    link = ""
                    category = "哲學"
                    # Always keep lesson number in title so progress parsing never falls back to 1
                    if not title or title == "待生成":
                        item_title = f"🎯 哲學探索 第{num_str}課"
                    else:
                        item_title = f"🎯 哲學探索 第{num_str}課：{title}"
                else:
                    link = ""
                    category = "其他"
                    item_title = title

                items.append({
                    "num": num_str,
                    "title": item_title,
                    "category": category,
                    "link": link,
                    "completed": is_completed,
                })
            central_status = _overlay_central_course_status(username, key, items)
            completed_count = len(all_done) if lessons else 0
            next_lesson = progress.get("next_lesson", 1)
            if central_status is not None:
                completed_count, central_next = central_status
                if central_next is not None:
                    next_lesson = central_next

            courses[key] = {
                "course": progress.get("course", key),
                "total": len(lessons) if lessons else (len(items) if items else 0),
                "completed_count": completed_count,
                "next": next_lesson,
                "items": items,
            }
        except Exception as e:
            courses[key] = {"error": str(e)}
    return JSONResponse({"status": "ok", "courses": courses})

# === MEMORY CONTEXT — read Hermes mem0 memories ===
MEMORY_COLLECTION = None
MEMORY_EMBEDDER = None

def _get_memory_collection():
    global MEMORY_COLLECTION
    if MEMORY_COLLECTION is None:
        import chromadb
        chroma_path = Path(
            os.environ.get(
                "CHROMA_PATH",
                str(HERMES_HOME / "mem0" / "chroma-jina"),
            )
        ).expanduser()
        client = chromadb.PersistentClient(path=str(chroma_path))
        MEMORY_COLLECTION = client.get_collection("hermes_mem0_jina")
    return MEMORY_COLLECTION

def _get_memory_embedder():
    global MEMORY_EMBEDDER
    if MEMORY_EMBEDDER is None:
        from fastembed import TextEmbedding
        MEMORY_EMBEDDER = TextEmbedding(model_name="jinaai/jina-embeddings-v2-base-zh", max_length=512)
    return MEMORY_EMBEDDER

class MemoryContextRequest(BaseModel):
    query: str = ""         # search query (topic title)
    max_results: int = 5

@app.post("/api/memory-context")
async def memory_context(req: MemoryContextRequest, request: Request):
    _require_authenticated_user(request)
    try:
        collection = _get_memory_collection()
        if collection.count() == 0:
            return JSONResponse({"status": "ok", "memories": [], "note": "no memories stored"})

        # Embed the query using the same model Hermes uses
        embedder = _get_memory_embedder()
        query_text = req.query or "學習"
        # fastembed returns a generator
        embeddings = list(embedder.embed([query_text]))
        query_vec = embeddings[0].tolist()

        # Search ChromaDB with pre-computed embedding
        results = collection.query(
            query_embeddings=[query_vec],
            n_results=req.max_results,
        )

        memories = []
        if results["ids"] and len(results["ids"][0]) > 0:
            for i in range(len(results["ids"][0])):
                doc = results["documents"][0][i] if results["documents"] else ""
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                memories.append({
                    "id": results["ids"][0][i],
                    "content": (doc or meta.get("data", "") or meta.get("text_lemmatized", ""))[:500],  # trim
                    "metadata": meta,
                    "score": float(1 - results["distances"][0][i]) if results.get("distances") else 0,
                })

        summary = _summarize_memories(memories, query_text) if memories else ""
        return JSONResponse({"status": "ok", "memories": memories, "summary": summary, "count": len(memories)})

    except Exception as e:
        return JSONResponse({"status": "error", "message": f"memory query failed: {str(e)}"}, status_code=500)

def _summarize_memories(memories, query):
    """Condense memory results into a brief context paragraph for Teacher."""
    if not memories:
        return ""
    texts = [m["content"] for m in memories[:3]]
    combined = "；".join(texts)
    return f"（從 Hermes 記憶中查到與「{query}」相關的資訊：{combined}）"

# === PHILOSOPHY COURSE ===
PHILOSOPHY_PROGRESS_PATH = STUDY_DATA_ROOT / "philosophy-progress.json"

class PhilosophyCompleteRequest(BaseModel):
    lesson_num: int
    question: str
    user_summary: str
    topics_raised: list[str] = []
    depth_rating: int = 3
    base_revision: int = 0
    # Optional: user-requested direction for the *next* lesson after this one.
    requested_next_topic: str = ""
    # Optional: free-form notes about life context to fold into user_profile.
    tension_zones: list[str] = []
    recurring_themes: list[str] = []


class CurriculumAdjustRequest(BaseModel):
    """Record a learner-requested topic for upcoming lessons (any course)."""
    topic: str
    course_key: str = "philosophy"  # philosophy | ai-agents-for-beginners | awesome-architecture | general
    lesson_num: int | None = None  # the lesson just completed, if any
    base_revision: int = 0  # philosophy document revision when course_key=philosophy
    apply_to_next: bool = True


def _default_philosophy_progress() -> dict:
    return {
        "course": "philosophy",
        "title": "自適應哲學課程",
        "next_lesson": 1,
        "completed": [],
        "skipped": [],
        "lessons": {},
        "lessons_detail": {},
        "pending_topics": [],
        "user_profile": {
            "discussed_topics_set": [],
            "recurring_themes": [],
            "tension_zones": [],
            "thinking_style": None,
            "preferred_depth": "moderate",
            "last_updated": None,
        },
    }


def _append_unique_strings(target: list, values: list[str], limit: int = 40) -> list:
    seen = {str(x).strip() for x in target if str(x).strip()}
    for raw in values:
        text = str(raw or "").strip()
        if not text or text in seen:
            continue
        target.append(text)
        seen.add(text)
    if len(target) > limit:
        del target[:-limit]
    return target


def _queue_pending_topic(progress: dict, topic: str, source: str = "user") -> dict:
    topic = str(topic or "").strip()
    if not topic:
        return progress
    pending = progress.setdefault("pending_topics", [])
    # De-dupe open topics with same text
    for item in pending:
        if isinstance(item, dict) and not item.get("consumed") and item.get("topic") == topic:
            return progress
    pending.append({
        "topic": topic,
        "source": source,
        "created_at": __import__("datetime").datetime.now().strftime("%Y-%m-%d"),
        "consumed": False,
    })
    # Keep last 20 entries
    if len(pending) > 20:
        progress["pending_topics"] = pending[-20:]
    return progress


def _consume_pending_into_next_lesson(progress: dict, next_lesson_num: int) -> str | None:
    """If next lesson is placeholder, promote the oldest open pending topic."""
    next_key = str(next_lesson_num).zfill(2)
    lessons = progress.setdefault("lessons", {})
    current_title = lessons.get(next_key)
    pending = progress.setdefault("pending_topics", [])
    open_item = next((p for p in pending if isinstance(p, dict) and not p.get("consumed") and p.get("topic")), None)
    if open_item is None:
        return current_title if current_title and current_title != "待生成" else None
    topic = str(open_item["topic"]).strip()
    if not current_title or current_title == "待生成":
        lessons[next_key] = topic
        open_item["consumed"] = True
        open_item["consumed_lesson"] = next_lesson_num
        return topic
    return current_title


def _course_lesson_key(value: object) -> str:
    """Normalize lesson identifiers such as 1, '1', and '01'."""
    text = str(value).strip()
    try:
        return f"{int(text):02d}"
    except (TypeError, ValueError):
        return text


def _overlay_central_course_status(username: str, course_key: str, items: list[dict]) -> tuple[int, int | None] | None:
    """Use central study items as the authoritative completion state.

    The legacy Hermes progress JSON files are still used as the course map,
    but their completion fields can lag behind the cross-device SQLite
    document.  Overlay only when this user's central document has matching
    course items, preserving the legacy preview for accounts without data.
    """
    document = _get_document(username, "study", migrate=False)
    if not document:
        return None
    stored_items = document.get("data", {}).get("items", [])
    if not isinstance(stored_items, list):
        return None

    by_lesson: dict[str, dict] = {}
    by_title: dict[str, dict] = {}
    for stored in stored_items:
        if not isinstance(stored, dict):
            continue
        if stored.get("courseKey") == course_key and stored.get("lessonNum") is not None:
            by_lesson[_course_lesson_key(stored["lessonNum"])] = stored
        title = stored.get("title")
        if isinstance(title, str) and title:
            by_title[title] = stored

    matched = 0
    for item in items:
        stored = by_lesson.get(_course_lesson_key(item.get("num")))
        if stored is None:
            stored = by_title.get(item.get("title", ""))
        if stored is None:
            continue
        item["completed"] = bool(stored.get("completedAt"))
        matched += 1

    if not matched:
        return None
    completed_count = sum(1 for item in items if item.get("completed"))
    next_item = next((item for item in items if not item.get("completed")), None)
    next_lesson = int(next_item["num"]) if next_item and str(next_item.get("num", "")).isdigit() else None
    return completed_count, next_lesson


@app.get("/api/philosophy/progress")
async def philosophy_progress(request: Request):
    username = _require_authenticated_user(request)
    document = _get_document(username, "philosophy")
    if document is None:
        return JSONResponse({
            "status": "ok",
            "document": "philosophy",
            "revision": 0,
            "schema_version": STUDY_DB_SCHEMA_VERSION,
            "updated_at": None,
            "data": _default_philosophy_progress(),
        })
    return JSONResponse({"status": "ok", **document})

@app.post("/api/philosophy/complete")
async def philosophy_complete(req: PhilosophyCompleteRequest, request: Request):
    username = _require_authenticated_user(request)
    """Update the authenticated user's central philosophy document."""
    try:
        document = _get_document(username, "philosophy")
        current_revision = document["revision"] if document else 0
        if current_revision != req.base_revision:
            raise RevisionConflict(document)
        progress = json.loads(json.dumps(
            document["data"] if document else _default_philosophy_progress(),
            ensure_ascii=False,
        ))
    except RevisionConflict as conflict:
        return _conflict_response("philosophy", conflict)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)

    lesson_key = str(req.lesson_num).zfill(2)
    
    # Update lessons and lessons_detail
    progress.setdefault("lessons", {})
    progress.setdefault("lessons_detail", {})
    progress["lessons"][lesson_key] = req.question
    
    detail = {
        "date": __import__('datetime').datetime.now().strftime("%Y-%m-%d"),
        "question": req.question,
        "user_summary": req.user_summary,
        "topics_raised": req.topics_raised,
        "depth_rating": req.depth_rating,
    }
    progress["lessons_detail"][lesson_key] = detail

    # Mark completed
    if req.lesson_num not in progress.get("completed", []) and lesson_key not in progress.get("completed", []):
        progress.setdefault("completed", []).append(req.lesson_num)

    # Advance to next lesson
    progress["next_lesson"] = req.lesson_num + 1

    # Generate next lesson title: prefer explicit request, else pending queue, else placeholder
    next_key = str(req.lesson_num + 1).zfill(2)
    next_title = "待生成"
    requested = str(req.requested_next_topic or "").strip()
    if requested and requested not in ("沒有", "无", "無", "no", "none", "-", "跳過", "略過"):
        progress.setdefault("lessons", {})[next_key] = requested
        _queue_pending_topic(progress, requested, source="post_lesson")
        # Mark the just-queued item as consumed for this next lesson
        for p in reversed(progress.get("pending_topics", [])):
            if isinstance(p, dict) and p.get("topic") == requested and not p.get("consumed"):
                p["consumed"] = True
                p["consumed_lesson"] = req.lesson_num + 1
                break
        next_title = requested
    else:
        promoted = _consume_pending_into_next_lesson(progress, req.lesson_num + 1)
        if promoted:
            next_title = promoted
        else:
            progress.setdefault("lessons", {})[next_key] = progress.get("lessons", {}).get(next_key) or "待生成"
            next_title = progress["lessons"][next_key]

    # Update user profile
    profile = progress.setdefault("user_profile", {})
    existing_topics = set(profile.setdefault("discussed_topics_set", []))
    for t in req.topics_raised:
        existing_topics.add(t)
    profile["discussed_topics_set"] = list(existing_topics)
    _append_unique_strings(profile.setdefault("tension_zones", []), list(req.tension_zones or []))
    _append_unique_strings(profile.setdefault("recurring_themes", []), list(req.recurring_themes or []))
    profile["last_updated"] = __import__('datetime').datetime.now().strftime("%Y-%m-%d")

    if req.depth_rating > 3:
        profile["preferred_depth"] = "deep"
    elif req.depth_rating >= 2:
        profile["preferred_depth"] = "moderate"

    try:
        saved = _put_document(username, "philosophy", progress, req.base_revision)
        return JSONResponse({
            "status": "ok",
            "document": "philosophy",
            "revision": saved["revision"],
            "updated_at": saved["updated_at"],
            "next_lesson": req.lesson_num + 1,
            "next_title": next_title,
            "data": saved["data"],
        })
    except RevisionConflict as conflict:
        return _conflict_response("philosophy", conflict)
    except ValueError as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=400)
    except Exception as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)


@app.post("/api/curriculum/adjust")
async def curriculum_adjust(req: CurriculumAdjustRequest, request: Request):
    """Queue a learner-requested topic; for philosophy, optionally pin next lesson title."""
    username = _require_authenticated_user(request)
    topic = str(req.topic or "").strip()
    if not topic or topic in ("沒有", "无", "無", "no", "none", "-", "跳過", "略過"):
        return JSONResponse({"status": "ok", "skipped": True, "message": "未調整"})

    course_key = (req.course_key or "philosophy").strip()

    if course_key == "philosophy":
        try:
            document = _get_document(username, "philosophy")
            current_revision = document["revision"] if document else 0
            if current_revision != req.base_revision:
                raise RevisionConflict(document)
            progress = json.loads(json.dumps(
                document["data"] if document else _default_philosophy_progress(),
                ensure_ascii=False,
            ))
        except RevisionConflict as conflict:
            return _conflict_response("philosophy", conflict)
        except Exception as exc:
            return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)

        _queue_pending_topic(progress, topic, source="curriculum_adjust")
        next_num = int(progress.get("next_lesson") or 1)
        next_title = topic
        if req.apply_to_next:
            next_key = str(next_num).zfill(2)
            progress.setdefault("lessons", {})[next_key] = topic
            for p in reversed(progress.get("pending_topics", [])):
                if isinstance(p, dict) and p.get("topic") == topic and not p.get("consumed"):
                    p["consumed"] = True
                    p["consumed_lesson"] = next_num
                    break
        profile = progress.setdefault("user_profile", {})
        _append_unique_strings(profile.setdefault("recurring_themes", []), [topic])
        profile["last_updated"] = __import__("datetime").datetime.now().strftime("%Y-%m-%d")

        try:
            saved = _put_document(username, "philosophy", progress, req.base_revision)
            # Keep legacy file in sync for sync-courses preview fallback
            try:
                PHILOSOPHY_PROGRESS_PATH.write_text(
                    json.dumps(saved["data"], ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
            except OSError:
                pass
            return JSONResponse({
                "status": "ok",
                "course_key": "philosophy",
                "next_lesson": next_num,
                "next_title": next_title if req.apply_to_next else None,
                "revision": saved["revision"],
                "data": saved["data"],
            })
        except RevisionConflict as conflict:
            return _conflict_response("philosophy", conflict)
        except Exception as exc:
            return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)

    # Non-philosophy: stamp the course progress JSON next lesson title when possible
    path = COURSE_PROGRESS_FILES.get(course_key)
    if path and path.exists():
        try:
            progress = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)
        progress.setdefault("pending_topics", [])
        progress["pending_topics"].append({
            "topic": topic,
            "created_at": __import__("datetime").datetime.now().strftime("%Y-%m-%d"),
            "consumed": False,
        })
        if req.apply_to_next:
            next_num = int(progress.get("next_lesson") or 1)
            lessons = progress.setdefault("lessons", {})
            # lessons may map num->slug; keep a parallel titles map
            titles = progress.setdefault("lesson_overrides", {})
            titles[str(next_num).zfill(2)] = topic
            progress["next_lesson_focus"] = topic
        try:
            path.write_text(json.dumps(progress, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except OSError as exc:
            return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)
        return JSONResponse({
            "status": "ok",
            "course_key": course_key,
            "next_lesson": progress.get("next_lesson"),
            "next_title": progress.get("next_lesson_focus"),
            "data": progress,
        })

    return JSONResponse({
        "status": "ok",
        "course_key": course_key,
        "queued": True,
        "topic": topic,
        "message": "已記錄主題（此課程無獨立進度檔，請於下一課 note 使用）",
    })


# === DATA PERSISTENCE — store/load study data from server ===

@app.get("/api/data")
async def load_data(request: Request):
    """Load the authenticated user's central study document."""
    username = _require_authenticated_user(request)
    try:
        return _document_response(_get_document(username, "study"))
    except (OSError, sqlite3.Error, ValueError) as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)

async def _save_data_request(req: Request) -> JSONResponse:
    username = _require_authenticated_user(req)
    try:
        body = await req.json()
        if not isinstance(body, dict) or not isinstance(body.get("data"), dict):
            return JSONResponse(
                {
                    "status": "error",
                    "message": "body must contain a data object and base_revision",
                },
                status_code=400,
            )
        base_revision = body.get("base_revision")
        if not isinstance(base_revision, int) or isinstance(base_revision, bool) or base_revision < 0:
            return JSONResponse(
                {"status": "error", "message": "base_revision must be a non-negative integer"},
                status_code=400,
            )
        saved = _put_document(username, "study", body["data"], base_revision)
        return JSONResponse({"status": "ok", **saved})
    except RevisionConflict as conflict:
        return _conflict_response("study", conflict)
    except ValueError as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=400)
    except (OSError, sqlite3.Error) as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=503)
    except Exception as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)


@app.put("/api/data")
async def save_data(req: Request):
    """Persist study data with optimistic revision locking."""
    return await _save_data_request(req)


@app.post("/api/data")
async def save_data_compat(req: Request):
    """Temporary compatibility alias; unversioned legacy payloads are rejected."""
    return await _save_data_request(req)

# === FETCH URL CONTENT ===
@app.post("/api/fetch-content")
async def fetch_content(req: FetchRequest, request: Request):
    _require_authenticated_user(request)
    url = req.url.strip()
    if not url:
        return JSONResponse({"status": "error", "message": "empty URL"}, status_code=400)

    # Only allow http/https
    if not url.startswith(("http://", "https://")):
        return JSONResponse({"status": "error", "message": "invalid URL"}, status_code=400)

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; StudySystem/1.0)"
            })
            resp.raise_for_status()
            html = resp.text
    except Exception as e:
        return JSONResponse({"status": "error", "message": f"fetch failed: {str(e)}"}, status_code=502)

    # Strip HTML tags, extract meaningful text
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '\n', text)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = '\n'.join(line.strip() for line in text.splitlines() if line.strip())
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Trim to reasonable size (keep first 10000 chars)
    max_chars = 10000
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[... 內容過長已截斷，原始長度 {} 字元]".format(len(html))

    if len(text.strip()) < 50:
        return JSONResponse({"status": "error", "message": "could not extract meaningful content"}, status_code=422)

    return JSONResponse({"status": "ok", "content": text.strip(), "source": url})

# === LEARN COMPLETE — save conversation to vault ===
@app.post("/api/learn/complete")
async def learn_complete(req: LearnCompleteRequest, request: Request):
    _require_authenticated_user(request)
    safe_path = req.path.replace("..", "").lstrip("/")
    if not safe_path.endswith(".md"):
        safe_path += ".md"
    full_path = VAULT_ROOT / safe_path
    full_path.parent.mkdir(parents=True, exist_ok=True)

    # Build note with conversation transcript
    transcript_lines = []
    for m in req.messages:
        role = "🧑 你" if m["role"] == "user" else "👩‍🏫 Teacher"
        transcript_lines.append(f"\n### {role}\n{m['content']}\n")

    transcript = "\n---\n".join(transcript_lines)

    content = f"""# {req.title} — 學習記錄

## 基本資訊
- **日期**：{Path(safe_path).stem.split('-')[0] if '-' in Path(safe_path).stem else '（自動記錄）'}
- **主題**：{req.title}
- **建立時間**：{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## 我的筆記

{req.note_content or '（無筆記內容）'}

---

## 對話記錄
{transcript}

---

## 教師總結
{req.llm_summary or '（無總結）'}
"""

    try:
        # Check if note already exists — if so, append conversation
        if full_path.exists():
            existing = full_path.read_text(encoding="utf-8")
            # Append conversation section if not already there
            if "## 對話記錄" not in existing:
                content = existing + "\n\n---\n" + content
            else:
                # Replace the conversation section
                parts = existing.split("## 對話記錄")
                content = parts[0] + "## 對話記錄" + "（更新於 " + __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M') + "）\n" + transcript + "\n"
                if len(parts) > 1 and "## " in parts[1]:
                    # Keep any sections after conversation
                    after = parts[1].split("## ", 1)
                    if len(after) > 1:
                        content += "\n## " + after[1]

        full_path.write_text(content, encoding="utf-8")
        rel_path = str(full_path.relative_to(VAULT_ROOT))
        return JSONResponse({"status": "ok", "path": rel_path, "note_saved": True})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

# === VAULT INFO ===
@app.get("/api/vault")
async def vault_info(request: Request):
    _require_authenticated_user(request)
    return {"root": str(VAULT_ROOT), "exists": VAULT_ROOT.exists()}

# === ROOT — serve index.html ===
@app.get("/")
async def root():
    from fastapi.responses import FileResponse
    # Prevent browsers / CDN from serving stale single-page app
    return FileResponse(
        "index.html",
        media_type="text/html",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )

# === HEALTH ===
@app.get("/api/health")
async def health():
    database = {
        "ok": False,
        "path": str(STUDY_DB_PATH),
        "writable": False,
        "schema_version": STUDY_DB_SCHEMA_VERSION,
    }
    try:
        _init_study_database()
        with _db_connect() as conn:
            conn.execute("SELECT 1").fetchone()
        database["ok"] = True
        database["writable"] = os.access(STUDY_DB_PATH, os.W_OK)
    except Exception as exc:
        database["error"] = str(exc)
    return {"status": "ok" if database["ok"] else "degraded", "database": database}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)
