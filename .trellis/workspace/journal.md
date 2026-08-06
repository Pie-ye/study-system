# Journal

## 2026-07-21 — Task 007 UX bugfix wave

- 五路平行 QA 後建立 `task-007-ux-bugfix-wave`
- 修復：本地日期、今日項目鎖定、習慣入口死鎖、經濟防刷、XSS 跳脫、server 資料合併、哲學 lessonNum、學習模式自動開講 / vault 存檔分離、`/api/data` 驗證
- 檔案：`index.html`、`server.py`、`AGENTS.md`

## 2026-07-21 — Session finish

- Commit: `f0f3883` feat(study-system): task 007 UX bugfix wave
- Archive: `5ddc204` task-007 → archive/2026-07/
- Live: todo.coinpilet.win with v7 badge + no-cache headers

## 2026-07-26 — Task 008 planning

- 建立 `task-008-central-database-sync`
- 目標：SQLite 中央資料庫作為唯一真相來源，讓同一帳號的學習進度跨裝置一致
- 範圍：JSON／LocalStorage 遷移、revision + 409 衝突處理、哲學 progress 中央化、離線狀態與備份

## 2026-07-26 — Task 008 implementation

- 實作 SQLite `user_documents`、legacy JSON migration、versioned `/api/data` 與哲學 progress API
- 前端改為中央資料優先、LocalStorage cache／首次匯入、revision conflict、前景／輪詢同步與離線唯讀
- 驗證：inline JavaScript syntax、Python compile、central sync API／migration／isolation tests 全部通過

## 2026-07-29 — Task 009 planning

- 建立 `task-009-queue-direct-learn`
- 目標：不需要經「今日」才能上課；佇列點擊未完成項目直接 `openLearningMode(id)`
- 編輯改獨立按鈕；預設 tab → queue；今日降為 streak／習慣摘要
- 沿用完成學習 orphan rebind（同日稍早修復）
- PRD：`.trellis/tasks/task-009-queue-direct-learn/prd.md`

## 2026-07-29 — Task 009b habits tab + queue click harden

- 佇列：`data-id` + addEventListener；點擊後確認 overlay `.active`，toast「開始：標題」
- 底欄「今日」→「習慣」；移除今日學習卡，`renderHabitsTab` 為主
- badge v9.1
- 上課入口仍為佇列；習慣頁僅打卡/管理 + 今日已學摘要
