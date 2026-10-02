# timesheet-tools

報工時工具包（Claude Code plugin）：把自己的 git commits 轉成經過審核的工時紀錄，送到工時平台。
目前支援的平台：Redmine。

| Skill | 用途 |
| --- | --- |
| `timesheet` | 報工時：收集檢查範圍（Scope）內各 repo 的 git commits → 對應平台上的票 → 每天補滿 8 h → 草稿審核 → 確認後送出 |
| `redmine` | Redmine 平台附帶工具：查單、列出指派給我的單、留言、改狀態、單筆記工時、把單轉成規格草稿 |

## 安裝

```
/plugin marketplace add <this repo URL or local path>
/plugin install timesheet-tools@timesheet-tools
```

從舊版 `redmine-tools` 升級：先 `/plugin uninstall redmine-tools@redmine-tools`，再依上方重新安裝。

## 需求

- `curl`、`python3`、`git`
- Redmine 平台：`REDMINE_URL`、`REDMINE_API_KEY` 環境變數 — 設定方式見
  `skills/redmine/references/setup.md`。API key 是個人憑證，各自設定，不要放進 repo。

## 第一次使用

直接說「報工時」。沒有設定時會先跑 Setup：

1. 選平台（目前只有 Redmine）並驗證連線
2. 從站台的活動列表挑選「開發／Code Review／討論」各用哪個活動
3. 設定每日目標（預設 8 h）
4. 建立檢查範圍：在 Herdr 內可「從 Herdr 匯入」目前 workspace 開著的 repo，或「把這個 repo 加入報工時檢查範圍」

之後可隨時說「設定報工時」重跑、「每日目標改 7.5」、「從 Herdr 匯入」、「移除 <repo>」。
匯入是一次性快照，之後 Herdr 的變化不會影響檢查範圍。

設定檔在 `$XDG_CONFIG_HOME/timesheet-tools/config.json`（預設 `~/.config/...`），只存平台、活動、
每日目標與檢查範圍，不存網址或 API key，也不進版控。

補分配依改動行數的 √ 比例分配，不是實測時間；工時表格式由腳本固定產出。

## 測試

```
python3 -m unittest discover -s tests
```
