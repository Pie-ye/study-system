# PRD: Task 002 — 整合 Hermes 記憶與既有課程

## 摘要

讓每日一學成為 Hermes 學習活動的**唯一入口**。不再靠 cron 定時推送，而是把既有課程（AI Agents、Awesome Architecture）的進度自動匯入 study-system 的學習佇列，並讓 Teacher 能夠讀取 Hermes 的長期記憶來個人化教學。

目標：當此任務完成時，可以移除大部分學習相關的 cron。

## 現狀分析

目前學習資源散落各處：

| 資源 | 載體 | 觸發方式 |
|------|------|----------|
| AI Agents 每日一課 | Hermes cron (20:00) | 定時推送 |
| 每日哲學反思 | Hermes cron (10:00) | 定時推送 |
| Awesome Architecture | 無 cron（互動式） | 使用者呼叫 |
| Karakeep 每日一篇 | Hermes cron (暫停) | 定時推送（已停） |

問題：定時推送 vs 隨興學習的矛盾。使用者想在有空的時間自己打開來學，而非被時間綁住。

## 目標

study-system 頁面成為學習入口：
1. 開啟頁面 → 看到今日待學項目（從佇列自動選）
2. 點「開始學習」→ Teacher 引導 + 測驗 + 筆記
3. AI Agents / Awesome Architecture 等課程進度自動同步到佇列
4. Teacher 知道使用者學過什麼、偏好什麼
5. **cron 可以逐步移除**，因為入口統一了

---

## 整合項目

### A. 佇列同步 — 既有課程自動匯入

讀取各課程的 progress JSON，自動產生對應的 study-system 學習項目：

```
讀取 ai-agents-course-progress.json
  → 產生項目「AI Agents 第N課：xxx」
  → 類別：AI / Agent
  → 連結：對應的 GitHub 原始檔

讀取 awesome-architecture-progress.json
  → 產生項目「Awesome Architecture 第N章：xxx」
  → 類別：技術架構
  → 連結：https://study8677.github.io/awesome-architecture/tutorial/0N-xxx/
```

新增端點：
```
POST /api/sync-courses   → 掃描 progress JSON，補齊缺少的項目
GET  /api/sync-courses   → 回傳可同步的課程清單（不寫入，僅預覽）
```

同步時機：手動觸發（頁面有按鈕），或每日第一次開啟頁面時自動檢查。

### B. 記憶整合 — Teacher 讀取 Hermes 記憶

在 server.py 直接 connect 到 Hermes 的 mem0（ChromaDB），唯讀查詢。

流程：
```
點「開始學習」
  → 後端查 mem0：搜尋關於此主題 / 此使用者的記憶
  → 回傳記憶摘要
  → 前端把記憶摘要傳給 /api/chat
  → Teacher 知道使用者之前學過什麼、偏好的教學方式
```

實作方式：在 server.py 中安裝 `mem0` 套件的唯讀子集（只 query，不 write）。連到 `/home/pieye/.hermes/mem0/chroma-jina`。

### C. Cron 清理計畫

當 study-system 成熟後，逐步清理的 cron：

| Cron | 清理方式 |
|------|----------|
| AI Agents 每日一課 | 課程進度匯入佇列，使用者自行點開學習 |
| 每日哲學反思 | 改為佇列中的一個「哲學問題」項目 |
| Karakeep 每日一篇 | 文章作為學習項目，連結直接放進去 |

注意：不強制立即刪除 cron。使用者在 study-system 中實際使用一段時間、確認習慣建立後，再手動關閉 cron。

---

## 技術方案

### 後端新增端點

```python
# server.py 新增

POST /api/sync-courses     # 掃描 progress JSON，匯入學習項目
GET  /api/sync-courses     # 預覽可匯入的課程項目（不回寫）
POST /api/memory-context   # 查詢 mem0，回傳相關記憶摘要
GET  /api/status/summary   # 回傳今日完整狀態（給 Hermes 或其他工具查詢）
```

### mem0 連線（唯讀）

```python
import chromadb
# 直接連 ChromaDB，不透過 mem0 套件（避免依賴衝突）
client = chromadb.PersistentClient(path="/home/pieye/.hermes/mem0/chroma-jina")
collection = client.get_collection("hermes_mem0_jina")
# query memories about user
results = collection.query(query_texts=[topic], n_results=5)
```

### 前端新增功能

- 設定頁面或佇列頁面的「同步課程」按鈕
- 學習模式啟動時，若有記憶摘要，顯示「Teacher 知道你的學習背景」
- When sync completes: 顯示匯入了哪些新項目

---

## 風險與緩解

| 風險 | 緩解 |
|------|------|
| chromadb 版本衝突（server.py 依賴 vs Hermes 依賴） | study-system venv 獨立安裝 chromadb |
| mem0 資料結構變動 | 限唯讀 + try/except fallback |
| 使用者進度不在 study-system 內時感覺失落 | 首次同步會有 onboarding 提示 |

---

## 驗收標準

- [ ] `POST /api/sync-courses` 成功從 AI Agents progress JSON 匯入項目
- [ ] `POST /api/sync-courses` 成功從 Awesome Architecture progress JSON 匯入項目
- [ ] 已完成的課程項目標記為已完成（不重複）
- [ ] `POST /api/memory-context` 回傳非空記憶結果（當有相關記憶時）
- [ ] 學習 session 啟動時，Teacher 知道使用者背景（對話中體現）
- [ ] 同步操作不修改 progress JSON（唯讀）
- [ ] 所有新端點有錯誤處理
