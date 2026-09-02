# Study System Instructions

## Current Task

（無進行中任務 — Task 009 已實作，待你瀏覽器確認後可 archive）

## Completed Tasks

- Task 001: MVP Daily Learning Portal (dashboard + Teacher learning mode) ✓
- Task 002: Course sync + Memory integration (Phase 2) ✓
- Task 003: Habits + Coins + Wishlist (Phase 3) ✓
- Task 004: Adaptive Philosophy Course (Phase 4) ✓
- Task 005: NT$ System + Data Persistence + Fixes (Phase 5) ✓
- Task 006: Teacher style upgrade (主動講解 / 移除選擇題) ✓
- Task 007: UX bugfix wave (日期/今日鎖定/經濟防刷/XSS/學習模式) ✓
- Task 008: Central database sync (SQLite authority, revision, multi-device) ✓
- Task 009: Queue direct learn（佇列點擊直進課程）✓

## Principles

1. Static HTML/CSS/JS frontend with a lightweight FastAPI service
2. Authenticated learning data is authoritative in the central SQLite database; LocalStorage is cache/import only
3. Duolingo-style gamification (streak, XP, levels, achievements)
4. Traditional Chinese UI
5. Mobile-first responsive design
6. Queue is the primary entry to start a lesson; Habits tab is check-in only (no Today lesson gate)
