# PRD: Task 008 — 中央資料庫與跨裝置進度同步

## 摘要

將 study-system 從「每台裝置各自保存 LocalStorage、伺服器 JSON 盡力同步」改成「伺服器 SQLite 資料庫為唯一真相來源」。同一個帳號在手機、桌機或不同瀏覽器登入後，應讀取同一份學習進度；任何寫入只有在中央資料庫確認成功後才算完成。

本任務包含現有資料的安全遷移、跨裝置版本同步、寫入衝突處理、離線狀態提示，以及哲學課程進度的中央化。AI Provider API Key 仍只保存在瀏覽器，不納入同步。

## 現況與問題

目前系統同時存在兩套資料來源：

- 前端每次操作都寫入瀏覽器 `localStorage`，key 為 `studySystem_v1:<username>`。
- 後端登入可用時，前端延遲呼叫 `POST /api/data`，後端將整包資料寫成每個帳號一個 JSON 檔。
- 啟動時先載入本機資料，再以 `mergeServerData()` 合併伺服器資料。
- 同步失敗目前會靜默忽略；本機登入模式完全不呼叫伺服器資料 API。
- `/api/philosophy/complete` 仍直接修改每個帳號的哲學 progress JSON。

因此不同裝置可能各自形成不同進度；目前沒有 revision、樂觀鎖或單一權威資料來源，無法可靠判斷哪次更新較新。

## 目標

1. 同一帳號的主學習進度在所有裝置保持一致。
2. 以 SQLite 作為伺服器端中央資料庫，服務重啟後資料仍存在。
3. LocalStorage 降級為快取與一次性匯入來源，不再是權威資料。
4. 避免兩台裝置同時寫入時互相靜默覆蓋。
5. 既有 JSON 與本機資料可安全遷移，不刪除原始檔案。
6. 保持繁體中文、手機優先與現有 Teacher／課程功能。

## 需求

| ID | 需求 |
|---|---|
| R1 | 學習資料持久化於 SQLite；至少涵蓋 `items`、`habits`、`wishlist`、`logs`、`xp`、`level`、`streak`、`achievements`、`todayItemId` 與相關狀態。 |
| R2 | 中央資料庫是 server-auth 模式下的唯一真相來源；瀏覽器僅保存最後一次成功同步的快取。 |
| R3 | 同一 username 的多裝置只能讀寫該 username 的資料；不同帳號必須完全隔離。 |
| R4 | 每份使用者文件都有整數 `revision`；寫入必須帶 `base_revision`，版本不符時回傳 `409 Conflict`，不得靜默覆蓋。 |
| R5 | 前端只有收到中央 API 成功回應後，才把操作視為已儲存；失敗時不得顯示成功或把失敗資料當作最新快取。 |
| R6 | 啟動、重新取得前景、手動同步時重新驗證中央版本；必要時提供短輪詢，讓另一裝置的更新可被看見。 |
| R7 | 後端不可用時明確顯示「未同步／離線」；正式 server-auth 流程不得允許使用者誤以為資料已同步。 |
| R8 | 提供一次性匯入本機 LocalStorage 的操作，匯入前顯示資料摘要並要求確認；匯入成功後以中央資料為準。 |
| R9 | 現有 `study-system-data.json`、`study-system-users/<username>.json` 與使用者哲學 progress JSON 可在首次啟動時遷移至 SQLite，原檔案保留作為備份。 |
| R10 | 哲學課程進度也要由中央資料庫讀寫；Teacher context、課程預覽與完成課程不可因裝置不同而分歧。 |
| R11 | AI Provider 設定與 API Key 不得寫入中央資料庫、`/api/data` payload、log 或同步快取。 |
| R12 | 提供資料庫 health check、備份／還原說明與可設定的 DB 路徑。 |

## 產品決策

| # | 決策 | 選擇 |
|---|---|---|
| D1 | 中央儲存 | SQLite；優先使用 Python 標準庫 `sqlite3`，不新增不必要的服務依賴。 |
| D2 | 真相來源 | Server-auth 模式以 SQLite 為準；LocalStorage 只作快取及明確確認後的匯入來源。 |
| D3 | 帳號隔離 | 沿用現有 HttpOnly session 與 username；資料查詢一律從 session 取得 username，不接受前端傳入的 user path。 |
| D4 | 寫入協議 | 版本化整包 JSON document + optimistic locking；MVP 不做 WebSocket 或 CRDT。 |
| D5 | 衝突策略 | 409 時保留未成功的本機變更、載入伺服器最新資料並明確提示使用者重新套用；禁止使用目前的「取較長陣列／取較大 XP」猜測式合併。 |
| D6 | 離線策略 | 最後成功資料可唯讀查看；變更操作需等中央服務恢復，避免產生另一個未同步真相。 |
| D7 | 外部課程檔 | AI Agents／Awesome Architecture 的外部 progress JSON 維持唯讀匯入來源；使用者自己的完成紀錄以中央 `study` document 為準。 |
| D8 | AI 機密 | AI 設定維持 username-scoped LocalStorage，不做跨裝置同步。 |

## 資料範圍

### 納入中央資料庫

- 每日學習佇列與項目完成狀態
- 習慣、習慣打卡與習慣 streak
- 每日完成／跳過紀錄、理由與學習筆記摘要
- NT$、XP、等級、連續天數與成就
- 願望清單與兌換狀態
- 今日項目、onboarding 與主題偏好等學習狀態
- 哲學課程 `lessons`、`lessons_detail`、`completed`、`next_lesson` 與 `user_profile`

### 不納入中央資料庫

- 各 AI provider 的 API Key、model 與本機認證狀態
- `fetched_content` 等可重新取得且可能很大的暫存內容
- 瀏覽器 UI 暫態狀態
- 外部課程原始 progress 檔案本身

## 非目標

- 不在本任務導入 WebSocket、即時多人協作或 CRDT。
- 不重做帳號註冊、密碼重設、OAuth 或管理後台；沿用現有帳號管理方式。
- 不把 AI API Key 上傳伺服器。
- 不刪除既有 JSON、Obsidian 筆記或外部課程來源檔案。
- 不將學習資料正規化成大量 relational tables；MVP 使用版本化 JSON document，保留日後拆表空間。

## 驗收標準

- [ ] AC1：同一帳號在兩個瀏覽器 profile／裝置登入，裝置 A 完成學習或勾選習慣後，裝置 B 重新整理或執行同步即可看到相同 `logs`、XP、streak 與習慣狀態。
- [ ] AC2：裝置 A 新增、編輯、刪除項目或願望後，裝置 B 可看到相同結果；伺服器重啟後資料仍存在。
- [ ] AC3：兩個裝置以相同舊 revision 同時寫入時，只有第一個成功；第二個收到 409，畫面顯示版本衝突，不會靜默覆蓋第一個更新。
- [ ] AC4：所有成功寫入都回傳新的 revision 與更新時間；失敗請求不會被寫入最後成功快取。
- [ ] AC5：後端不可用時畫面顯示「未同步／離線」，不顯示「已儲存」；正式同步模式下變更操作被阻止或清楚標示未同步。
- [ ] AC6：登入帳號 A 無法透過 API 或前端載入帳號 B 的學習資料；未登入存取受保護資料 API 回 401。
- [ ] AC7：既有 `study-system-users/<username>.json` 與 `pieye` 的 legacy 單檔資料可冪等遷移；重跑遷移不重複或覆蓋較新的 DB 資料，原始 JSON 保留。
- [ ] AC8：使用者可預覽並一次性匯入本裝置 LocalStorage；匯入後第二台裝置載入的是中央結果，而不是各自保留一份分歧資料。
- [ ] AC9：哲學課程完成一次後，另一裝置的課程預覽、Teacher context 與下一課編號一致。
- [ ] AC10：AI API Key 不出現在 DB、`/api/data` response、network payload、server log 或備份內容。
- [ ] AC11：`/api/health` 能反映 SQLite 是否可讀寫、DB 路徑與 migration 狀態；DB 檔有明確備份／還原操作說明。
- [ ] AC12：測試涵蓋單裝置 CRUD、雙裝置同步、409 衝突、帳號隔離、重啟持久化、遷移、離線失敗與哲學進度同步。

## 參考檔案

- `server.py`：現有 FastAPI、session、`/api/data`、`/api/philosophy/complete`
- `index.html`：LocalStorage、`saveData()`、啟動載入與 `mergeServerData()`
- `.trellis/spec/index.md`：登入、多帳號與 AI 設定規範
- `.trellis/workspace/journal.md`：Task 007 完成記錄
