# PRD: Task 003 — 習慣養成 + 每日待辦

## 摘要

將每日一學從「學習入口」升級為「每日待辦入口」，加入習慣追蹤功能。使用者在同一頁面可以看到今天要學什麼、今天有哪些習慣要完成，全部用 XP + streak 驅動。

## 現狀

目前頁面只有「學習佇列」的項目。每天從佇列中選一個來學，學完 +XP。

問題：使用者也許每天還有其他想養成的習慣（運動、冥想、喝水、記帳⋯），但沒有地方記錄和追蹤。

## Phase 3 目標

讓這個頁面變成每天早上打開的第一個頁面：看到今天要學什麼 + 今天習慣清單，全部勾完就有滿滿 XP。

---

## 功能需求

### F1: 習慣資料模型

```javascript
habits: [
  {
    id: 'uuid',
    title: '早晨運動 10 分鐘',
    category: '健康',
    frequency: 'daily',     // 'daily' | 'weekday' | 'weekly'
    xpPerCheck: 3,
    createdAt: '2026-07-20',
    logs: ['2026-07-20', '2026-07-21']  // 完成的日期
  }
]
```

每筆習慣獨立記錄完成的日期清單，用於計算 streak。

### F2: 今日視圖 — 整合學習 + 習慣

今日分頁重新設計為上下兩區：

```
┌─ 今日學習 ─────────────────┐
│  Awesome Architecture Ch.02│
│  [ 開始學習 ]  [ 今天不學 ]  │
└────────────────────────────┘

┌─ 今日習慣 ─────────────────┐
│ ☐  早晨運動 10 分鐘   🔥 3天│
│ ☑  閱讀 5 頁           🔥 7天│
│ ☐  冥想 5 分鐘         🔥 1天│
│                            │
│   進度：1/3  已獲得 +3 XP   │
└────────────────────────────┘
```

- 學習區塊保持現有邏輯（每日挑選 + Teacher 模式）
- 習慣區塊顯示所有 `frequency: daily` 的習慣
- 每個習慣一個 checkbox，打勾即標記完成，+XP
- 顯示每個習慣的當前連續天數（🔥）
- 顯示今日習慣總進度（X/Y 已完成）

### F3: 習慣管理分頁

在「佇列」分頁旁邊新增「習慣」分頁：

- 新增習慣：名稱、類別、頻率（每天/平日/每週）
- 編輯習慣
- 刪除習慣
- 顯示每個習慣的統計（總完成次數、最佳連續天數、當前連續天數）

### F4: XP 與成就

- 完成一個習慣：+3 XP
- 全部習慣完成：額外 +5 XP bonus
- 新成就：
  - 🏃 第一次完成習慣
  - 🔥 連續 7 天完成全部習慣
  - 💪 連續 30 天完成全部習慣
  - 🌈 累計完成 5 種不同類別的習慣

### F5: 習慣統計

統計分頁新增：
- 總習慣完成次數
- 今日習慣進度
- 各習慣的連續天數圖表（條狀）

### F6: 今日學習習慣分數

今日總分 = 學習 XP + 習慣 XP，顯示在狀態列。

---

## 技術規格

### 資料結構變更

```javascript
// 新增 data.habits 陣列
{
  ...existingData,
  habits: [
    {
      id: 'uuid',
      title: '習慣名稱',
      category: '健康',
      frequency: 'daily',  // daily | weekday | weekly
      xpPerCheck: 3,
      createdAt: '2026-07-20',
      logs: ['2026-07-20']  // 完成日期字串陣列
    }
  ]
}
```

### 新成就列表

| id | 名稱 | 條件 | icon |
|----|------|------|------|
| firstHabit | 習慣起步 | 第一次完成習慣 | 🏃 |
| habitWeek | 習慣一週 | 連續 7 天完成全部習慣 | 🔥 |
| habitMonth | 習慣達人 | 連續 30 天完成全部習慣 | 💪 |
| habitVariety | 多元習慣 | 累計 5 種不同類別 | 🌈 |

### 計算邏輯

```javascript
function calcHabitStreak(habit){
  // 從今天往回數，連續有 logs 的天數
  let streak = 0;
  let check = todayStr();
  while(habit.logs.includes(check)){
    streak++;
    check = yesterdayStr(check);
  }
  return streak;
}
```

### 今日習慣完成度

```javascript
const todayHabits = data.habits.filter(h => h.frequency === 'daily');
const doneToday = todayHabits.filter(h => h.logs.includes(todayStr()));
const progress = doneToday.length / todayHabits.length;
```

---

## 依賴

- 無新後端依賴（純前端）
- 需新增「習慣」分頁 HTML + CSS
- 需新增 habits 資料結構 + CRUD + 渲染

---

## 驗收標準

- [ ] 可在「習慣」分頁新增/編輯/刪除習慣
- [ ] 今日視圖顯示所有 daily 習慣，附 checkbox
- [ ] 打勾習慣後 XP 增加，顯示 Toast 通知
- [ ] 每個習慣顯示獨立 streak
- [ ] 全部習慣完成時顯示 bonus XP
- [ ] 習慣 streak 計算正確（中斷後歸零）
- [ ] 新成就正確解鎖
- [ ] 深色模式支援
- [ ] 行動裝置可用
