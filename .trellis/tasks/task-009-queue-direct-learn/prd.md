# PRD: Task 009 — 佇列直進課程（不必經今日介面）

## 摘要

把「開始上課」的主入口從「今日」頁搬到「佇列」。使用者在佇列點一堂未完成課程，就直接進入 Teacher 學習模式；不必先被鎖定成今日一課、也不必繞過今日卡片才能學。

今日頁若保留，只負責 streak／習慣／今日狀態摘要，不再是唯一上課入口。

## 背景與問題

### 現況

| 路徑 | 行為 |
|------|------|
| 今日 →「🎓 開始學習」 | `openLearningMode()`，用 `todayItemId`／`pickTodayItem()` |
| 佇列列點擊 | `editItem(id)` → 編輯表單，**不會**開課 |
| 佇列「📖 重學」 | 僅已完成項目：`relearnItem(id)` → `openLearningMode(id)` |
| 完成學習 | `endLearningSession()` 寫 `completedAt` + 今日 log／NT$（已修 orphan rebind） |

### 痛點

1. 想學佇列裡某一堂，要先在「今日」把 `todayItemId` 換成那堂，或靠換課／重學繞路。
2. 佇列點擊語意是「編輯 metadata」，與「我想上課」直覺相反。
3. Pull-based 學習偏好是：打開頁面 → 佇列選一堂 → 上完按完成。今日單卡鎖定增加摩擦。
4. 「不需要今日介面」作為**上課入口**；習慣打卡、streak 仍可能需要一個摘要面，但不應擋住選課。

### 相關最近修復（非本任務，但實作時必須沿用）

- Learning-mode orphan：`ensureLearningItemBound()` / 學習中暫停 silent `syncNow`，避免「完成學習」不寫入佇列 `completedAt`。

## 目標

1. 佇列成為選課與開課的主入口。
2. 點未完成項目 → 直接進入 Teacher 學習模式（同現有 overlay／SSE／完成流程）。
3. 編輯項目仍可用，但不再是列的預設點擊。
4. 完成後佇列狀態正確（`completedAt`、✅ 已學過、可重學）；每日 NT$ 防刷規則不變。
5. 今日頁不再是上課必要路徑；可降級為摘要，或後續再決定是否收合／改預設 tab。

## 非目標

- 不重做 Teacher 教學內容、SSE、vault 寫入、課程 sync 匯入邏輯。
- 不改中央 SQLite revision／auth 模型。
- 不一次刪除整個「今日」tab 與習慣系統（除非驗收時明確選擇「移除今日 tab」；預設是**降級入口**，不是砍功能）。
- 不做多課並行 session、課表日曆、拖曳排序大改。
- 不把外部 progress JSON 改回權威來源。

## 產品決策

| # | 決策 | 選擇 |
|---|------|------|
| D1 | 主開課入口 | **佇列**。列點擊（未完成）= 開始／繼續該課。 |
| D2 | 已完成列點擊 | 預設等同「重學」開 `openLearningMode(id)`，或列上保留明顯「重學」；避免點到又進編輯。 |
| D3 | 編輯 metadata | 獨立「編輯」按鈕（或 ⋯ 選單），`event.stopPropagation()`，不再是整列預設。 |
| D4 | 今日 tab | **保留** streak／習慣／今日 log 摘要；「開始學習」可保留作捷徑，但文案／權重次於佇列。預設啟動 tab 改為 **queue**（可配置後再討論）。 |
| D5 | `todayItemId` | 從佇列開課時：設 `todayItemId = 該課 id`（若今日尚未 log），讓今日摘要與 log 一致；**不**再強制只能學鎖定的那一堂。 |
| D6 | 每日獎勵 | 維持「一天一次 NT$ 學習獎勵」：`dailyLearningRewardDate` + log；同日第二堂可完成並標 `completedAt`，不再發獎勵（與現 `endLearningSession` 一致）。 |
| D7 | 跳過／理由 | 仍可在今日或佇列提供「今天不學」；本任務至少保證佇列開課＋完成閉環，跳過 UI 可不搬家。 |
| D8 | 預設首屏 | 登入後 `switchTab('queue')`（習慣可在今日或佇列上方一小塊；若習慣仍只在今日，首屏改 queue 時需在佇列空態提示「習慣在今日」或把今日習慣摘要輕量露出——實作時選摩擦最低方案）。 |

## 需求

| ID | 需求 |
|----|------|
| R1 | 佇列未完成項目：主點擊區域呼叫 `openLearningMode(id)`，進入學習 overlay。 |
| R2 | 佇列已完成項目：主點擊或「重學」進入 `openLearningMode(id)`；完成後走複習／已領獎路徑，不重複發 NT$。 |
| R3 | 編輯、刪除必須有獨立控件，且不與開課手勢衝突。 |
| R4 | 從佇列開課與從今日開課共用同一 `openLearningMode`／`endLearningSession`；必須使用 live `data.items` rebind（既有 orphan 修復）。 |
| R5 | 開課時若今日尚無 completed/skipped log，將 `todayItemId` 設為該項目（並在需要時 `saveData`，或於完成時一併持久化——避免只改記憶體被 sync 沖掉）。 |
| R6 | 完成學習後回到佇列（或停留可回佇列），該項顯示已完成；未完成列表不再出現該項（或沉到底部已學區，維持現排序：未完成在前）。 |
| R7 | 登入後預設 tab 為佇列；使用者仍可切到今日看習慣與 streak。 |
| R8 | 空佇列／未登入／離線唯讀時行為清楚：不能開課就提示，不出現空白 overlay。 |
| R9 | 繁中 UI；手機可點整列開課，右側按鈕熱區足夠、不誤觸刪除。 |
| R10 | 不破壞課程 sync「只匯入下一章」、中央 revision、哲學 complete API。 |

## UX 草圖（佇列列）

```
[📚] 標題……                    [編輯] [✕]
     類別 · 30分
     ← 點列身 = 開始學習

[📚] 已完成標題…  · ✅ 已學過   [重學] [編輯] [✕]
     ← 點列身 = 重學（同 openLearningMode）
```

## 技術範圍（實作時）

主要檔案：

- `index.html`：`renderQueue`、`editItem`、`openLearningMode`、`switchTab`／`startAuthenticatedApp` 預設 tab、可能微調 `renderToday` CTA 權重
- 不強制改 `server.py`（除非開課要新 API；預期不需要）
- 更新 `.trellis/spec/index.md` 學習佇列規範：選課入口改佇列
- 更新 `study-system-development` skill 一句話（佇列直進）

沿用約束：

- `canMutateStudy()` 擋離線寫入
- `ensureLearningItemBound()` 於完成時
- 學習 overlay 開啟時不跑 silent sync

## 驗收標準

- [x] AC1：登入後預設看到「佇列」tab（或明確以佇列為主的首屏）。
- [x] AC2：點一筆**未完成**佇列項目 → 直接進入 Teacher 學習模式，標題為該課。
- [x] AC3：學習中對話後按「完成學習」→ 該項 `completedAt` 有值，佇列顯示 ✅ 已學過；中央 DB revision 前進。（沿用 orphan rebind；完成後 `switchTab('queue')`）
- [x] AC4：同日再完成另一堂 → 第二堂也標完成，但 NT$ 不重複發（既有 `endLearningSession` 防刷）。
- [x] AC5：點**已完成**項（或重學）可再開課；完成走複習路徑。
- [x] AC6：編輯按鈕仍可改標題／連結／備註；刪除仍可用；兩者不會誤觸發開課。
- [x] AC7：不必先到「今日」按開始學習也能完成一整課閉環。
- [x] AC8：今日 tab 習慣打卡、streak 顯示仍可用（今日 chrome 保留）。
- [x] AC9：離線／conflict 時開課或完成有明確 toast（`canMutateStudy` / `saveData`）。
- [x] AC10：硬重新整理後，已完成狀態仍在（SQLite 權威；本任務未改持久化路徑）。

## 實作記錄（2026-07-29）

- `renderQueue`：列點擊 → `startQueueLesson(id)`；✎ 編輯／✕ 刪除獨立；未完成顯示「🎓 學」
- 預設 tab／nav／`startAuthenticatedApp` → `queue`；badge `v9`
- `openLearningMode`：從佇列開課時綁定 `todayItemId`（今日尚無 log）
- `endLearningSession` 結束後回到佇列
- 今日 CTA 降權，加「從佇列選課」

## 參考

- `index.html`：`renderQueue`、`openLearningMode`、`endLearningSession`、`relearnItem`、`editItem`
- Task 007／008：今日鎖定、中央 DB、完成防刷
- 2026-07-29 orphan 修復：學習中 sync 與 `lmCurrentItem` rebind
- 使用者偏好：pull learning、佇列乾淨（只 next + completed）、全在網頁內學完
