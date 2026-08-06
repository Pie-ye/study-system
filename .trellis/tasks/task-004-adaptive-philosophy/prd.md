# PRD: Task 004 — 自適應哲學課程

## 摘要

將目前的「每日哲學反思」cron 升級為結構化的自適應課程，由 Teacher 在 study-system 中引導。每次課程的主題根據使用者的每日對話自動選取，課後更新 progress JSON 來累積個人側寫，讓課程越來越貼合使用者。

## 現狀

目前有一個 Hermes cron `每日哲學反思` (555dd58365ed)，每天早上 10:00 在 Hermes 對話中拋出一個哲學問題。使用者討論後手動寫筆記到 Obsidian。

問題：
- 主題固定不變，沒有累積性
- 沒有記錄使用者思考軌跡
- 不在 study-system 中，分散管理
- 無法與其他學習記錄串聯

## Phase 4 目標

讓哲學成為一個「活的課程」——沒有固定課綱，但每次都比上一次更了解使用者。

---

## 核心機制

### A. 自適應主題生成

每次上課時，Teacher 會：

1. **掃描近期對話** — 讀取使用者在 Hermes 中的最近對話（從 session DB 或 dialog logs），找出：
   - 使用者卡住或猶豫的主題
   - 使用者提出的問題或矛盾
   - 使用者表達的情緒或價值觀衝突
2. **對照哲學側寫** — 參考 `philosophy-profile.json` 中的學習歷史
3. **生成主題** — 選一個最相關的哲學問題，從 Socrates 到現代倫理
4. **出課** — 在 study-system 中開始 Teacher 引導的哲學討論

### B. 進度 JSON 結構

```json
{
  "course": "philosophy",
  "title": "自適應哲學課程",
  "started": "2026-07-20",
  "timezone": "Asia/Taipei",
  "next_lesson": 3,
  "completed": [1, 2],
  "paused": false,
  "vault_dir": "Hermes筆記/學習/每日哲學",
  "mode": "adaptive",
  "lessons": {
    "01": "自由意志與決定論 — 你最近的選擇困難",
    "02": "什麼是正義 — 從你的工作困境出發",
    "03": "待生成"
  },
  "lessons_detail": {
    "01": {
      "date": "2026-07-20",
      "question": "如果一個人的行為完全由基因和環境決定，『負責』還有多大意義？",
      "trigger": "使用者在選擇 side project 時反覆猶豫",
      "user_summary": "使用者認為『選擇』是 illusion 但 still matters",
      "topics_raised": ["free_will", "determinism", "responsibility"],
      "depth_rating": 3,
      "hermes_sessions_referenced": ["session_xxx", "session_yyy"]
    }
  },
  "user_profile": {
    "recurring_themes": ["decision_paralysis", "meaning_of_work"],
    "discussed_topics_set": ["自由意志", "正義", "存有"],
    "thinking_style": "reluctant_analytical",
    "preferred_depth": "moderate",
    "tension_zones": ["理想 vs 現實", "自由 vs 責任"],
    "last_updated": "2026-07-20"
  }
}
```

### C. 課後更新流程

每次課程完成後，自動執行：

1. **記錄課程** — 將當前課程寫入 `lessons` 和 `lessons_detail`
2. **分析使用者** — 從對話中提取思維模式、反覆主題、矛盾點
3. **更新側寫** — 更新 `user_profile` 中的各項指標
4. **決定下一步** — 根據側寫選取下一個最合適的哲學方向
5. **產生下一課標題** — 預填 `lessons` 中的待生成項目
6. **遞增 next_lesson** — 讓 sync 可以抓到下一課

### D. Hermes 對話掃描

為了讓 Teacher 能讀取近期對話，需要一個新的 API 端點：

```
POST /api/scan-conversations
  → 讀取 Hermes session DB 中的最近對話（例如最近 3 天）
  → 回傳主題摘要、反覆出現的詞彙、情緒標記
  → 供 Teacher 在生成主題時使用
```

實作方式：
- 讀取 `~/.hermes/sessions/` 中的 session DB（SQLite）
- 查詢最近 N 天的對話
- 用 LLM 摘要對話主題

### E. 與 study-system 整合

- 課程資料放在 `~/.hermes/home/philosophy-progress.json`
- 透過現有的 `/api/sync-courses` 端點匯入 study-system 佇列
- 每次 Teacher 課程完成後，透過 `/api/sync-courses` 重新同步
- 筆記寫入 Obsidian `Hermes筆記/學習/每日哲學/`

---

## 技術方案

### 新增檔案

| 檔案 | 用途 |
|------|------|
| `~/.hermes/home/philosophy-progress.json` | 課程進度 + 個人側寫 |

### 新增 API 端點

```python
# server.py 新增

POST /api/scan-conversations
  → 讀取 session DB，回傳近期對話摘要
  → 參數：days (int, default 3)
  
POST /api/philosophy/next
  → 讀取 philosophy-progress.json + 近期對話
  → 用 LLM 決定下一課的主題
  → 更新 progress JSON
  → 回傳下一課資訊

POST /api/philosophy/complete
  → 課程完成時呼叫
  → 參數：lesson_num, question, user_summary, topics
  → 更新 progress JSON + user_profile
```

### 前端的哲學學習模式

哲學課程在 Teacher 中運作時的特殊流程：
1. 先顯示「本次哲學問題」（由自適應邏輯產生）
2. 開放式討論（非技術課程，沒有正確答案）
3. Teacher 引導反思，而非測驗
4. 課後自動更新 JSON

---

## 風險

| 風險 | 緩解 |
|------|------|
| 掃描對話涉及隱私 | 只掃描 metadata + 摘要，不存原始對話 |
| 自適應主題可能重複 | 用 `discussed_topics_set` 過濾，主動避開 |
| LLM 生成的哲學品質不一 | Teacher 系統提示中加入哲學脈絡引導 |
| 與現有哲學 cron 衝突 | 直接取代 cron，暫停原 cron job |

---

## 驗收標準

- [ ] `philosophy-progress.json` 格式正確，可被 `/api/sync-courses` 讀取
- [ ] 第一次啟動時自動產生第一課
- [ ] 課後 `lessons_detail` 正確寫入
- [ ] 課後 `user_profile` 更新
- [ ] 同一主題不會連續出現（避開已討論過的主題）
- [ ] 每次課程主題都與近期對話有關聯
- [ ] 課程紀錄持久化到 Obsidian
- [ ] 原 cron `每日哲學反思` 可安全暫停
