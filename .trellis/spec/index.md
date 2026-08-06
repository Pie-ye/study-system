# 學習系統 Master Spec — Daily Todo & Habit System

## 專案願景

建立一個「每日一學 + 日常習慣」的統一待辦入口，用 Duolingo 風格的遊戲化機制，同時驅動學習進度與習慣養成。

## 核心原則

1. **單一入口** — 每天打開這個頁面，就知道今天要完成什麼
2. **低摩擦** — 不需要思考「今天做什麼」，系統幫你整理好
3. **誠實機制** — 不學可以，但必須寫理由；習慣沒做到就打勾空著
4. **視覺獎勵** — 連續天數、經驗值、成就徽章
5. **跨裝置一致** — server-auth 模式以中央 SQLite 為唯一真相，LocalStorage 僅作快取與一次性匯入

## 規範

### 學習佇列規範
- 每筆學習項目必須有：標題、類別、預計所需時間
- 可選：連結、備註、優先順序
- **選課主入口是佇列**：點未完成項目直接進入 Teacher 學習模式（Task 009）
- 「今日」頁以 streak／習慣／當日狀態摘要為主，不再是唯一上課閘道
- 每天仍可記錄一筆今日 log（完成或跳過理由）；同日可完成多堂課，但學習 NT$ 獎勵一日一次

### 打卡規範
- 完成學習後，點選「完成」，streak +1，獲得 XP
- 未完成學習時，必須填寫「今天為什麼沒學」的理由
- 理由選項：太累、沒時間、沒動力、內容太難、其他（自訂）
- 跳過不扣 streak，但會記錄跳過次數
- 連續跳過超過 3 天，系統會出現「Rex 推一把」提醒

### Streak 規範
- 連續天數 = streak
- 每 7 天連續 = 一個里程碑（7, 14, 21, 30...）
- 中斷 streak 時不歸零，改顯示「最佳連續天數」
- 周末可設定「緩衝模式」：周末不需要完成，但寫理由仍可延續 streak

### XP 與等級規範
- 完成一個項目：+10 XP
- 寫學習筆記（備註欄）：額外 +5 XP
- 連續 7 天：獎勵 +30 XP
- 等級：1-10 級（每級所需 XP 遞增）
- 等級名稱：種子→嫩芽→小樹→大樹→竹林→森林...

### 成就徽章（Duolingo 風格）
- 第一次完成學習：🎉 第一步
- 連續 7 天：🔥 一週達人
- 連續 30 天：💪 月之星
- 連續 100 天：👑 百戰王者
- 學習 10 個不同類別：🌈 博學家
- 寫了 10 次理由：📝 誠實日記

## 技術約束

- 純前端，零後端依賴
- 單一 HTML 檔案（或最多 index.html + style.css + app.js）
- 使用 LocalStorage 持久化資料
- 支援深色/淺色主題（跟隨系統）
- 響應式設計（手機/桌機均可）
- 所有文字以繁體中文為主

## 路線圖

### Phase 1 — MVP（已完成 ✅）
- 單一 HTML 頁面
- 每日挑選 + 完成/跳過 + 理由記錄
- Streak 計數 + 視覺化
- XP + 等級系統
- 基本成就徽章
- 全部 LocalStorage
- Teacher 學習模式（SSE streaming + URL 內容抓取）
- Obsidian 筆記寫入
- 對話紀錄持久化

### Phase 2 — 整合記憶與既有課程（已完成 ✅）
- **佇列同步**：AI Agents、Awesome Architecture 等課程進度自動匯入學習佇列
- **記憶整合**：Teacher 可讀取 mem0 記憶來個人化教學
- **Cron 清理**：當 study-system 成熟後，cron 可逐步移除，改由統一入口代替
- 目標：學習 cron → 0，統一到每日一學頁面

### Phase 3 — 習慣養成 + 每日待辦（已完成 ✅）
- 從「每日一學」升級為「每日待辦」
- **習慣清單**：建立重複性習慣（運動、閱讀、冥想⋯），每天打勾完成
- **今日視圖**：上方顯示今日學習任務，下方顯示今日習慣勾選清單
- **XP 獎勵**：完成一個習慣 +3 XP，全部完成額外 bonus
- **習慣 streak**：每個習慣獨立計算連續天數
- **習慣類別**：健康、理財、人際、自我成長、休閒⋯
- **勾選即完成**：不需進 Teacher 模式，一鍵打勾就 +XP
- **改為金幣系統**：XP → 🪙，新增願望清單 + 兌換機制

### Phase 4 — 自適應哲學課程（已完成 ✅）
- 將 cron 中的哲學反思改為結構化課程
- **自適應課程**：根據使用者每日對話自動產生哲學主題
- **進度 JSON**：類似 AI Agents / Awesome Architecture 的 progress JSON
- **事後更新**：每次課程完成後自動更新 JSON，記錄主題、深度、使用者思路
- **個人側寫**：累積使用者的思維風格、興趣傾向，讓課程越來越客製化
- **佇列同步**：哲學課程自動出現在 study-system 佇列中
- 目標：取代 cron，完全由 study-system 管理

### Phase 5 — 新台幣系統 + 資料持久化（已完成 ✅）
- 金幣改為新台幣 NT$
- 課程進度全部重置
- 移除 onboarding 綠色畫面
- 各課程獨立同步
- 資料持久化到伺服器
- 修復習慣刷錢漏洞
- 支援重新學習已完成的項目

### Phase 6 — Teacher 教學風格升級 🔜
- Teacher 主動講解，不等待學生發問
- 出題以簡答與申論題為主
- 啟發創意思考與發想
- 章節學完後明確告知「今日進度完成，明天繼續」
- 移除選擇題，轉為開放式提問

### Phase 7 — AI 供應商設定介面 🔜
- AI 設定使用獨立的 `study-system-ai-settings-v1` LocalStorage key，不得混入 `studySystem_v1` 學習資料或 `/api/data` 同步 payload。
- 供應商 ID 固定使用 `openai`、`anthropic`、`gemini`、`deepseek`、`grok`；新增供應商時先擴充集中式 provider config，再由畫面讀取。
- Model ID 應以各供應商官方模型目錄為準；更新清單時保留舊 ID 的 migration/fallback，避免既有 localStorage 設定變成無效選項。
- 每個 provider 的設定契約為 `{ model, authMode, apiKey, authStatus }`；`authMode` 只能是 `api-key` 或 `oauth`。
- API Key 只能出現在密碼輸入欄與使用遮罩的摘要中，不得寫入 console、toast、一般文字或 server sync。
- API Key 本機保存狀態只能顯示「已儲存、尚未驗證」；沒有後端驗證時不得顯示「已連線」。
- OAuth callback/token exchange 尚未接通時，必須顯示 `not_available`／「尚未接通」，不得模擬登入成功或產生虛假 token。
- Teacher 實際切換 provider 需要後續安全的後端串接；設定介面完成不代表既有 `/api/chat` 已改用該 Key。

```js
// Correct: keep AI credentials outside the learning-data sync model.
localStorage.setItem('study-system-ai-settings-v1', JSON.stringify(aiSettings));
```

### Phase 9 — 中央資料庫與跨裝置同步 🚧
- SQLite `user_documents` 儲存每個帳號的 study／philosophy documents。
- `/api/data` 使用 revision + optimistic locking；stale write 回 409，不靜默覆蓋。
- Server-auth 模式中央資料優先，LocalStorage 改為最後成功同步快取與首次匯入來源。
- 後端不可用時顯示未同步／本機唯讀狀態；AI API Key 不進入中央同步。

### Phase 10 — 佇列直進課程（Task 009）✅
- 佇列列點擊未完成項目 → `startQueueLesson` / `openLearningMode(id)`，不必經今日卡片
- 編輯／刪除獨立控件；已完成可重學
- 預設 tab 改 queue；今日降為摘要／習慣
- 完成閉環沿用 orphan rebind 與一日一次 NT$ 防刷
- PRD：`.trellis/tasks/task-009-queue-direct-learn/prd.md`

### Phase 8 — 使用者登入與多帳號隔離 ✅

#### 1. Scope / Trigger
- 登入頁必須在後端可用與純靜態 LocalStorage 模式都能使用。
- 預設帳號為 `pieye`；公開註冊保持關閉，新增帳號只能由管理者建立。

#### 2. Signatures
- `POST /api/auth/login`: `{ username, password }` → `{ status: "ok", user }`，成功以 HttpOnly session cookie 驗證。
- `GET /api/auth/me`: 回傳 `{ authenticated, user? }`。
- `POST /api/auth/logout`: 清除 session cookie。
- LocalStorage keys：`studySystem_users_v1`、`studySystem_v1:<username>`、`study-system-ai-settings-v1:<username>`。

#### 3. Contracts
- 後端可用時優先使用 server session 與帳號分檔資料。
- 後端不可用或沒有登入 API 時，前端可切換至本機帳號驗證；本機只允許既有帳號，不得顯示註冊入口。
- 本機帳號密碼只保存 PBKDF2 hash，不保存明文；本機模式不得將學習資料同步至未驗證的後端。

#### 4. Validation & Error Matrix
- 帳號不存在或密碼錯誤 → 顯示登入錯誤，不初始化儀表板。
- 未登入呼叫受保護後端 API → HTTP 401。
- 後端連線失敗 → 顯示本機登入提示，不將它誤報成密碼錯誤。
- localStorage 資料不存在 → 建立該帳號的預設學習資料，不讀取其他帳號資料。

#### 5. Good / Base / Bad Cases
- Good：`pieye / pieye123` 在後端與純靜態模式均可登入，資料只寫入 pieye namespace。
- Base：後端 session 失效時回到登入頁；本機模式仍可保留本機學習資料。
- Bad：用共用 `studySystem_v1` 或全域 server JSON 作為所有帳號的唯一資料來源。

#### 6. Tests Required
- 驗證初始帳號成功、錯誤密碼拒絕、未登入 API 回 401、登出後 session 失效。
- 驗證第二個帳號讀不到 pieye 的學習資料與 AI 設定。
- 驗證後端不存在時，PBKDF2 本機登入仍能初始化儀表板，且不觸發 `/api/data` 同步。

#### 7. Wrong vs Correct
```js
// Wrong: app startup depends entirely on an optional backend.
await fetch('/api/auth/me');
```

```js
// Correct: use server auth when available, otherwise keep the static app usable.
const user = await authenticateLocalUser(username, password);
if (user) await startAuthenticatedApp({ ...user, authMode: 'local' });
```
