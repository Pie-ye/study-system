# PRD: Task 007 — UX / 操作錯誤修復波次

## 摘要

依 2026-07-21 五路平行 QA（今日、佇列、習慣/願望、學習模式、統計/持久化）結果，修復會影響使用者操作、顯示與經濟系統的真實 bug。不新增功能，以正確性與一致性為主。

## 來源

平行靜態分析 + API 探測（server `:8765`）。報告涵蓋 Critical / High / Medium / Low。

## 目標

1. 日期、今日項目、streak 在台灣時區正確
2. 無法刷 NT$ / 雙重完成
3. 習慣可從零新增；願望兌換安全
4. 使用者字串不造成 HTML 注入
5. 本機與 server 資料合併不抹掉進度
6. 哲學課進度不覆寫卡住
7. 學習模式完成/關閉/錯誤處理合理

## 範圍（本波次必修）

### C1 本地日期
- `todayStr` / `yesterdayStr` / `calcHabitStreak` 改用本地日曆日

### C2 今日項目鎖定
- `pickTodayItem` 優先使用有效的 `todayItemId`
- 全完成複習也要寫入 `todayItemId`

### C3 習慣入口
- 零 daily 習慣時仍顯示「＋ 新增習慣」

### C4 經濟防刷
- `resetToday`：若當日 completed log，退回 `xpEarned`
- `completeToday` / `submitSkip`：當日已有 log 則拒絕
- `saveWish` / `buyWish`：價格 ≥ 1；已兌換不可再扣
- `toggleHabit` 取消：餘額不足時禁止取消（避免花幣後取消刷獎）

### C5 XSS
- 佇列 / 今日 / 統計 / 習慣 / 願望 / 同步預覽等 `innerHTML` 路徑使用 `escapeHtml`
- 連結僅允許 `http(s):`

### C6 資料合併與 API
- server merge：scalars 取較完整側（xp 取 max、achievements 深合併、version 升級）
- 預設 `version: 2`；v1 遷移不反覆清零
- `POST /api/data` 拒絕非 object

### C7 哲學進度
- item 帶 `lessonNum`（同步寫入）；完成時優先用欄位而非標題 regex
- 表單補「哲學」類別與 icon

### H 高優先（同波次盡量修）
- 刪除今日項目時清理 `todayItemId` / 當日 log 顯示
- `endLearningSession`：今日已有 log 仍存 vault，並 toast 說明
- 開啟學習後自動呼叫 chat 開講（若無歷史）
- SSE：檢查 `resp.ok`；結束未 `[DONE]` 仍 finalize
- `closeLearning` 有對話時 confirm
- `switchTab` 非今日時隱藏今日卡與習慣區
- 統計/完成文案 NT$ 一致
- 成就：更新 `bestStreak` 後再 `checkAchievements`
- 同步 upsert 保留同 title 的 id（避免 log 斷鏈）

## 非目標（本波次不做）
- 獨立習慣分頁完整 CRUD UI 重做
- weekday/weekly 完整日程引擎
- NT$ 與等級 XP 欄位拆分（架構較大，僅先防刷與文案）
- Markdown 完整 renderer
- 主題 FOUC 全面重構

## 驗收
- [x] 台灣凌晨日期與本地一致（`todayStr` 改本地日曆日）
- [x] 同日切 tab 不重抽今日項目（`pickTodayItem` 鎖定 `todayItemId`）
- [x] 新用戶可新增第一個習慣（零習慣仍顯示入口）
- [x] 無法透過 reset/負價/取消勾選刷幣
- [x] 惡意標題不執行腳本（主要 render 路徑 `escapeHtml` + 安全連結）
- [x] server 合併不降本地較高 xp（`mergeServerData`）
- [x] 哲學完成不反覆寫 lesson 1（標題保留課號 + `lessonNum` 欄位）
- [x] 重學時仍可存 vault（`saveLearningArtifacts` 與 XP 路徑分離）

## 實作紀錄（2026-07-21）

已改：`index.html`、`server.py`。主要見 C1–C7 與 H 高優先項。  
未做（明確非目標）：習慣分頁完整重做、weekday 引擎、NT$/XP 欄位拆分、完整 Markdown renderer。

## 技術
- 主要：`index.html`、`server.py`
- 原則：純靜態 + LocalStorage；繁中 UI
