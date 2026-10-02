# redmine-tools

Claude Code plugin with two skills:

| Skill | 用途 |
| --- | --- |
| `redmine` | 查單、列出指派給我的單、留言、改狀態、單筆記工時、把單轉成規格草稿 |
| `redmine-timesheet` | 報工時：收集 Herdr 各 pane 的 git commits → 對應 Redmine 票 → 每天補滿 8 h → 草稿審核 → 確認後送出 |

## 安裝

```
/plugin marketplace add <this repo URL or local path>
/plugin install redmine-tools@redmine-tools
```

## 需求

- `REDMINE_URL`、`REDMINE_API_KEY` 環境變數 — 設定方式見 `skills/redmine/references/setup.md`。
  API key 是個人憑證，各自設定，不要放進 repo。
- `curl`、`python3`、`git`
- `redmine-timesheet` 另需在 Herdr 內執行（`HERDR_ENV=1`，`herdr` 在 PATH 上）。

## 依 Redmine 站台調整

- 活動 ID：`redmine-timesheet` 預設 `9 程式開發`、`11 Code Review(審核)`、`12 問題討論`。
  其他站台請以 `$REDMINE_URL/enumerations/time_entry_activities.json` 對照修改 `SKILL.md`。
- 每日目標 8 h：`rows.json` 的 `target_hours`，補分配依改動行數的 √ 比例分配，非實測時間。
