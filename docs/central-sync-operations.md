# 中央同步資料庫操作說明

## 資料庫位置

服務預設使用：

```text
/home/pieye/.hermes/home/study-system.sqlite3
```

可用環境變數 `STUDY_DB_PATH` 改變位置。資料庫由 `server.py` 初始化，使用 SQLite WAL 模式；不要把 `.sqlite3`、`-wal` 或 `-shm` 檔案提交到 Git。

## 健康檢查

```bash
curl -fsS http://127.0.0.1:8765/api/health
```

`database.ok=true` 且 `database.writable=true` 才代表中央資料庫可正常使用。

## 備份

備份前先暫停服務，確保 SQLite 的 WAL 內容已 checkpoint，再複製資料庫檔案：

```bash
cp /home/pieye/.hermes/home/study-system.sqlite3 \
  /home/pieye/.hermes/home/study-system.sqlite3.backup-$(date +%Y%m%d-%H%M%S)
```

同時保留既有的 `study-system-users/`、`study-system-data.json` 與哲學 progress JSON；它們是 migration／rollback 的原始來源，migration 不會刪除它們。

## 還原

1. 停止 study-system 服務。
2. 保留現場 `.sqlite3`、`-wal`、`-shm` 檔案作為事故副本。
3. 將已驗證的 backup 複製回 `STUDY_DB_PATH`。
4. 確認檔案權限屬於執行服務的使用者。
5. 啟動服務並呼叫 `/api/health`，再用測試帳號確認 revision 與資料內容。

不要直接刪除現場 DB；若 DB 無法讀取，先複製現場檔案再處理。

## 緊急回退

若中央 DB 暫時無法服務，可將 `STUDY_SYNC_MODE=legacy` 作為部署層的回退標記，並回到 legacy JSON 版本。回退期間畫面必須視為「非中央同步」，不可把該期間的 LocalStorage 變更宣稱為已同步；恢復中央 DB 後，應先備份並以人工確認方式匯入。
