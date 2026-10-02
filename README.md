# timesheet-tools

報工時工具包（Claude Code plugin）：把自己的 git commits 轉成經過審核的工時紀錄，送到工時平台。
目前支援的平台：Redmine。

| Skill | 用途 |
| --- | --- |
| `timesheet` | 報工時：收集 Herdr 各 pane 的 git commits → 對應平台上的票 → 每天補滿 8 h → 草稿審核 → 確認後送出 |
| `redmine` | Redmine 平台附帶工具：查單、列出指派給我的單、留言、改狀態、單筆記工時、把單轉成規格草稿 |

## 安裝

```
/plugin marketplace add <this repo URL or local path>
/plugin install timesheet-tools@timesheet-tools
```

從舊版 `redmine-tools` 升級：先 `/plugin uninstall redmine-tools@redmine-tools`，再依上方重新安裝。

## 需求

- `REDMINE_URL`、`REDMINE_API_KEY` 環境變數 — 設定方式見 `skills/redmine/references/setup.md`。
  API key 是個人憑證，各自設定，不要放進 repo。
- `curl`、`python3`、`git`
- `timesheet` 另需在 Herdr 內執行（`HERDR_ENV=1`，`herdr` 在 PATH 上）。

## 依平台調整

- Redmine 活動 ID：預設 `9 程式開發`、`11 Code Review(審核)`、`12 問題討論`。
  其他站台請以 `$REDMINE_URL/enumerations/time_entry_activities.json` 對照修改
  `skills/timesheet/platforms/redmine.md`。
- 每日目標 8 h：`rows.json` 的 `target_hours`，補分配依改動行數的 √ 比例分配，非實測時間。

## 測試

```
python3 -m unittest discover -s tests
```
