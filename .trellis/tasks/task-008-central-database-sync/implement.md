# Implement — 中央資料庫與跨裝置進度同步

## Checklist（建議順序）

### Phase 1 — Repository 與資料庫

- [x] 建立 SQLite repository／初始化函式，支援 `STUDY_DB_PATH`。
- [x] 建立 `user_documents` schema、index、WAL、busy timeout 與 migration version。
- [x] 實作 `get_document()`、`put_document()`、`document_exists()` 與 transaction helper。
- [x] 加入 payload schema 驗證、大小限制與 `fetched_content` 清理。

### Phase 2 — 舊資料遷移

- [x] 將 `study-system-users/<username>.json` 遷移至 `study` document。
- [x] 將 `pieye` 的 legacy `study-system-data.json` 遷移至 `study` document。
- [x] 將使用者哲學 progress JSON 遷移至 `philosophy` document。
- [x] 遷移必須冪等、保留原始檔案，並測試「DB 已有較新資料」不被舊檔覆蓋。
- [x] 提供本機 LocalStorage 摘要與一次性匯入確認；匯入成功後以中央版本為準。

### Phase 3 — 後端 API

- [x] 將 `GET /api/data` 改為回傳 `data + revision + schema_version + updated_at`。
- [x] 新增版本化 `PUT /api/data`；`base_revision` 不符時回 409。
- [x] 保留短期 `POST /api/data` 相容別名，但禁止無版本寫入。
- [x] 將 `/api/philosophy/complete` 改為 transaction 寫入 SQLite，新增 `base_revision`。
- [x] 新增 `GET /api/philosophy/progress`，並讓 `/api/chat`、`/api/sync-courses` 讀取中央 document。
- [x] 更新 `/api/health` 回報 DB 可用性、可寫性、路徑與 schema 狀態。

### Phase 4 — 前端權威來源改造

- [x] 將 `loadAuthenticatedData()` 改為中央資料優先；成功載入後覆寫本機 cache。
- [x] 重構 `saveData()` 為單一 versioned sync repository，移除靜默 `catch(() => {})`。
- [x] 所有完成學習、習慣、願望與佇列 CRUD 都經過中央寫入成功確認。
- [x] 實作寫入鎖／短佇列，避免快速連點造成多次 stale revision。
- [x] 移除 `mergeServerData()` 的猜測式合併邏輯。
- [x] 加入「已同步／同步中／未同步／版本衝突／立即同步」狀態 UI。
- [x] 頁面回到前景、手動同步與短輪詢時檢查中央 revision。
- [x] 後端不可用時顯示唯讀快取，禁止未同步變更或明確提示尚未保存。

### Phase 5 — 哲學與機密資料

- [x] 哲學 Teacher context 改從中央 repository 讀取。
- [x] 哲學完成流程使用中央 revision，衝突時不靜默覆蓋。
- [x] 驗證 AI Provider 設定與 API Key 仍只在 username-scoped LocalStorage。
- [x] 確認 `/api/data` 與哲學 API response 不接收或回傳 API Key。

### Phase 6 — 文件、部署與驗證

- [x] 更新 `start.sh`／部署說明，記錄 `STUDY_DB_PATH` 與 DB 目錄權限。
- [x] 加入 `.gitignore` 規則，避免 SQLite DB、WAL、SHM 與本機備份進入 Git。
- [x] 撰寫 DB 備份、checkpoint、還原與 legacy rollback 流程（`docs/central-sync-operations.md`）。
- [x] 完成 API、migration、隔離與 409 情境測試。
- [x] 驗證 API 的同帳號隔離、不同帳號隔離、409 衝突與 health 狀態。

## Suggested validation

```bash
# 語法與靜態檢查
.venv/bin/python -m py_compile server.py

# 啟動服務後檢查
curl -fsS http://127.0.0.1:8765/api/health

# 兩個 cookie jar 模擬兩台裝置：登入同一帳號、GET 相同 revision
# 裝置 A PUT revision N → 成功取得 N+1
# 裝置 B 仍用 revision N PUT → 必須得到 409，不能覆蓋 A

# 重啟服務後再次 GET，資料與 revision 必須保留
```

瀏覽器驗證：

1. 兩個瀏覽器 profile 使用同一帳號登入。
2. Profile A 完成今日學習、勾選習慣、兌換一個願望。
3. Profile B 執行「立即同步」或重新整理，確認 XP、logs、習慣與願望完全一致。
4. 兩邊同時操作同一份舊資料，確認一邊成功、一邊看到版本衝突且沒有靜默丟資料。
5. 以另一帳號登入，確認看不到第一個帳號的資料。

## Risky files

- `server.py`：SQLite、migration、API 與 session user isolation。
- `index.html`：所有目前的 state mutation 與 LocalStorage／server sync 流程。
- `start.sh`：服務啟動目錄與 DB 環境設定。
- `.gitignore`：避免中央 DB 與備份誤提交。

## Rollback points

- 實作前備份現有 `study-system-data.json`、`study-system-users/` 與哲學 progress 檔案。
- 新 DB 只新增、不刪除 legacy JSON；migration 失敗時可回到舊檔。
- 保留 `STUDY_SYNC_MODE=legacy` 的緊急退路，但 UI 必須標示「非中央同步」。
- SQLite 損壞時先停服務、複製現場 DB 檔，再以已驗證 backup 還原；不得直接刪除現場資料。

## Before implementation starts

- [x] PRD 已定義中央資料庫、同步權威、遷移、衝突與驗收標準。
- [x] Design 已定義 SQLite schema、API contract、前端 lifecycle 與 rollback。
- [x] Implement checklist 已拆成 repository、migration、API、前端、哲學、部署與驗證階段。
- [ ] 使用者確認規劃後，才開始修改 `server.py` 與 `index.html`。
