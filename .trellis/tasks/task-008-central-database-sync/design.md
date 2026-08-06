# Design — 中央資料庫與跨裝置進度同步

## Architecture

```text
裝置 A / 裝置 B / 手機瀏覽器
  ├─ memory state：目前畫面資料
  ├─ LocalStorage：最後成功同步快取／一次性匯入來源
  └─ 同源 API + HttpOnly session
             │
             ▼
study-system FastAPI server (:8765)
  ├─ 現有 auth session 與帳號隔離
  ├─ GET/PUT /api/data（study document）
  ├─ GET/POST /api/philosophy/*（philosophy document）
  ├─ migration：legacy JSON → SQLite
  └─ health / backup diagnostics
             │
             ▼
SQLite（中央唯一真相來源）
  └─ user_documents(username, document_key, revision, data_json, ...)
```

主要原則：server-auth 模式下，前端不再用本地內容和伺服器內容做猜測式合併；先取得中央版本，成功寫入後才更新本機快取。

## SQLite 資料模型

使用一張可擴充的 document table，避免把目前前端 state 大幅拆成多張表：

```sql
CREATE TABLE IF NOT EXISTS user_documents (
  username       TEXT NOT NULL,
  document_key   TEXT NOT NULL,
  schema_version INTEGER NOT NULL DEFAULT 1,
  revision       INTEGER NOT NULL DEFAULT 0,
  data_json      TEXT NOT NULL,
  created_at     TEXT NOT NULL,
  updated_at     TEXT NOT NULL,
  PRIMARY KEY (username, document_key)
);

CREATE INDEX IF NOT EXISTS idx_user_documents_updated
  ON user_documents (username, updated_at);
```

目前只允許兩個 `document_key`：

- `study`：`getDefaultData()` 對應的學習資料。
- `philosophy`：現有哲學 progress JSON。

`username` 只由已驗證的 session 取得，不由 URL、query string 或 request body 決定。若未來帳號改成正式 users table，可再將欄位改為 `user_id`。

SQLite 初始化設定：

- DB 路徑由 `STUDY_DB_PATH` 指定，預設放在 `/home/pieye/.hermes/home/study-system.sqlite3`。
- 啟用 WAL、foreign key（若日後加入 users table）與 busy timeout。
- 寫入使用 transaction；更新時先確認 `(username, document_key, revision)`，成功後 revision +1。
- JSON payload 限制大小，並在 server 端再次移除 `fetched_content` 等非持久欄位。

## API 契約

### Study data

```http
GET /api/data
```

回應：

```json
{
  "status": "ok",
  "document": "study",
  "revision": 12,
  "schema_version": 2,
  "updated_at": "2026-07-26T12:34:56+08:00",
  "data": { "version": 2, "items": [], "logs": [] }
}
```

```http
PUT /api/data
Content-Type: application/json

{
  "base_revision": 12,
  "data": { "version": 2, "items": [], "logs": [] }
}
```

成功回傳新的 `revision`。若 `base_revision` 不是目前 revision，回傳 `409` 並附上目前中央版本，前端不可直接覆蓋。

現有 `POST /api/data` 可在遷移期間保留為相容別名，但也必須要求 `base_revision`；不得保留無版本的任意覆蓋寫入。

### Philosophy data

- `GET /api/philosophy/progress`：讀取登入者中央哲學 document。
- `POST /api/philosophy/complete`：沿用目前 request 欄位，新增 `base_revision`，在同一個 transaction 內更新 lesson、profile、next lesson 與 revision。
- `/api/chat` 與 `/api/sync-courses` 的哲學 context 改從 repository 讀取 DB，不直接讀使用者 progress JSON。

### Error contract

| 狀態 | 意義 | 前端行為 |
|---|---|---|
| 401 | session 不存在或失效 | 回登入頁，不讀寫其他資料 |
| 409 | 另一裝置先更新 | 保留待送變更、重新載入 server state、提示使用者重新套用 |
| 413 | payload 過大 | 顯示資料過大，不寫入快取 |
| 503 | DB 暫時不可用 | 顯示離線／未同步，禁止宣稱成功 |
| 500 | 未預期伺服器錯誤 | 保留最後成功快取並顯示失敗 |

## Frontend synchronization lifecycle

### 啟動

1. 呼叫現有 `/api/auth/me`。
2. server-auth 成功後呼叫 `GET /api/data` 與哲學 progress API。
3. 若中央有資料，以中央資料取代本機 state，再寫入最後成功快取。
4. 若中央沒有資料，執行 server-side legacy migration；若仍為空，顯示一次性本機資料匯入提示。
5. 完成後顯示 `✅ 已同步 · revision N`。

### 寫入

將現有所有 `saveData()` 呼叫集中到一個同步 repository：

1. 複製目前 state，建立不可變的 pending snapshot。
2. 使用最後成功的 `revision` 呼叫 versioned PUT。
3. 成功：以 server response 的 state／revision 更新 memory 與 LocalStorage cache。
4. 失敗：不更新最後成功快取，復原或保留 pending snapshot，顯示具體錯誤。
5. 同一時間只允許一個 study write；後續操作排入前端短佇列或暫時停用按鈕，避免連續點擊造成版本競賽。

### 重新取得

- 頁面回到前景時檢查最新 revision。
- 提供「立即同步」按鈕。
- 可用 30–60 秒短輪詢作為 MVP 的跨裝置更新提示；不要求即時 WebSocket。
- 若有未送出的 pending snapshot，先顯示衝突，不自動丟棄或合併。

### 衝突

保留 `lastServerState`、`pendingState` 與 `baseRevision`。收到 409 時：

1. 將中央 state 載入畫面。
2. 顯示「其他裝置已更新」與「重新套用本次變更」選項。
3. 使用者確認後重新以最新 revision 送出；未確認前不得覆蓋中央資料。

這取代目前 `mergeServerData()` 以陣列長度、XP 最大值推測資料完整性的做法。XP 可能同時增加或消費，不能用 `Math.max` 當作通用衝突解決。

## LocalStorage 與遷移

### Server-side JSON migration

啟動 repository 時針對每個 document 執行冪等 migration：

1. DB 已存在該 username/document 且 revision > 0：DB 優先，不讀回舊檔覆蓋。
2. DB 沒有資料：先讀 `study-system-users/<username>.json`。
3. `pieye` 沒有 user file 時，才使用 legacy `study-system-data.json`。
4. 哲學 document 依序讀使用者檔，再讀 legacy `philosophy-progress.json`。
5. 成功匯入後建立 revision 1；原始檔案不刪除，並記錄 migration timestamp。

### Browser LocalStorage import

中央資料已存在時，LocalStorage 只能透過設定頁的「匯入此裝置資料」明確操作：

- 顯示本機與中央的最後更新時間、項目數、紀錄數與 XP。
- 匯入前要求確認，並先保留本機 cache backup。
- MVP 可提供「以本機資料建立下一版」或「取消」；不做不可逆的自動覆蓋。
- 匯入成功後所有裝置都以中央 revision 為準。

## Security and privacy

- 延用 HttpOnly session；所有資料 endpoint 呼叫 `_require_authenticated_user()`。
- username 只來自 session，並使用參數化 SQL。
- AI API Key 維持既有獨立 LocalStorage，server 不接收。
- 不把完整 Teacher conversation 放入 study document；既有 Obsidian vault 寫入流程維持在 server。
- DB 檔案權限限於服務使用者；文件提供備份檔權限注意事項。

## Operations

- `STUDY_DB_PATH`：SQLite 路徑。
- `/api/health` 增加 `database: {ok, path, writable, schema_version}`。
- 備份前可執行 SQLite checkpoint，備份 DB 檔與 `-wal`／`-shm` 一致性由操作說明處理。
- 既有 JSON 不刪除，保留 rollback 來源。
- 如需緊急回退，提供 `STUDY_SYNC_MODE=legacy` 讓服務暫時讀舊 JSON；前端需明示 legacy／未同步狀態。

## Risks

| 風險 | 緩解 |
|---|---|
| 舊裝置仍送無版本 POST | 保留短期相容 endpoint，但拒絕無 `base_revision` 的覆蓋寫入。 |
| 兩台裝置同時修改 | SQLite transaction + revision + 409；前端保留 pending 變更。 |
| DB 損壞 | WAL、health check、定期備份、保留 legacy JSON。 |
| 離線期間誤以為完成 | server 不可用時阻止寫入並顯示未同步。 |
| 哲學檔案與 DB 分叉 | 所有讀寫改走 repository，檔案只作一次性 migration／rollback。 |
