---
name: redmine-timesheet
description: |
  Batch time logging to Redmine: collect the user's commits from every repo open in Herdr, map them to Redmine issues, top each day up to 8 h across the day's changes, draft a timesheet for review, and post time entries only after the user approves.
  TRIGGER — load this skill BEFORE any other action whenever the prompt says 報工時, 記工時, 填工時, 補工時, 工時清單, 今天做了什麼要報, timesheet, log time / log hours, or asks to turn today's (or a date range's) commits into Redmine time entries. Takes precedence over the general `redmine` skill for these requests.
  SKIP for a single ad-hoc time entry the user fully specifies (issue, hours, activity) — use `redmine` for that.
---

# Redmine timesheet

Five stages, in order. Never skip stage 4's review, and never post in stage 5 without an explicit
go-ahead in the current turn.

Shared rules from the `redmine` skill apply: auth header `X-Redmine-API-Key: $REDMINE_API_KEY`,
`curl -sS --fail-with-body`, never echo or store the key, payloads go in the scratchpad.

`<skill-dir>` below is this skill's base directory, shown when the skill loads. Scripts and
references are resolved from it, never from a fixed install path.

## 1. Enter

Check, and stop with a clear message if any fails:

```bash
test "${HERDR_ENV:-}" = 1 && test -n "${REDMINE_URL:-}" && test -n "${REDMINE_API_KEY:-}"
```

Missing Redmine variables → point at `<skill-dir>/../redmine/references/setup.md`.
Not inside Herdr → say so and stop; do not fall back to guessing repos.

Date range: whatever the user said ("昨天", "這週", a date). Default today. Say the resolved
dates back in the first line of the reply.

## 2. Collect

```bash
python3 <skill-dir>/scripts/collect.py --since <YYYY-MM-DD> [--until <YYYY-MM-DD>]
```

It reads every Herdr pane's cwd, dedupes to git roots, and for each repo returns the user's own
non-merge commits (author = that repo's `user.email`, filtered on author date) grouped by branch
into **sessions**: consecutive commits no more than 2 h apart on the same day.
`estimated_hours` = (last − first commit) + 0.5 h lead time, rounded to 0.5, minimum 0.5.

Also reported: panes that are not git repos (`skipped_panes`) and `uncommitted` changes. Show
uncommitted work as a note only — it carries no hours.

## 3. Map to Redmine issues

Fetch the candidates once:

```bash
curl -sS --fail-with-body -H "X-Redmine-API-Key: $REDMINE_API_KEY" \
  "$REDMINE_URL/issues.json?assigned_to_id=me&status_id=open&limit=100"
```

For each branch group, take the first rule that matches and record which one:

| 依據 | Rule |
| --- | --- |
| 明確票號 | `#12345` / `refs #12345` / `issues/12345` in a commit subject or branch name |
| 規格連結 | A `Redmine: …/issues/<id>` line in the repo's `.scratch/<feature>/` spec or docs matching the branch's feature |
| 主旨比對 | A feature code in the branch (e.g. `B1-7` from `feat_B1-7`) appears in exactly one candidate subject (`開發-B1-7-0 公司治理`), or the commit subjects clearly describe one candidate (表單定義 → `[後台] 表單管理`) — scoped to the candidate whose project matches the repo |
| 未對應 | Nothing above, or more than one candidate fits |

Never guess between multiple candidates. 未對應 rows go to the user in stage 4.

Merge sessions that map to the same issue on the same date into one row; keep the session times
in the 依據 column.

## 4. Draft the timesheet for review

Fetch what is already logged for the range so nothing is double-counted:

```bash
curl -sS --fail-with-body -H "X-Redmine-API-Key: $REDMINE_API_KEY" \
  "$REDMINE_URL/time_entries.json?user_id=me&from=<since>&to=<until>&limit=100"
```

### Top up to 8 h

Commit gaps miss reading, meetings and debugging, so each day with commits is topped up to 8 h.
Write the issue rows to `rows.json` in the scratchpad and run:

```bash
python3 <skill-dir>/scripts/allocate.py <scratchpad>/rows.json
```

```json
{"target_hours": 8,
 "logged": {"2026-10-01": 1.0},
 "rows": [{"id": "57379@2026-10-01", "date": "2026-10-01", "hours": 2.0, "lines": 11237,
           "allocatable": true, "locked": false}]}
```

- `hours` = the row's summed `estimated_hours`; `lines` = the row's summed session `lines`
  (changed lines, lockfiles and generated files excluded).
- `logged` = hours already in Redmine per date, from the call above.
- `allocatable: false` for 未對應 rows — they get nothing and do not count toward the day.
- `locked: true` for any row whose hours the user set by hand — it keeps exactly that value.

Shortfall = 8 − logged − planned, in whole 0.5 h units, split by √(changed lines) with largest
remainder, so the day lands on exactly 8 h when the shortfall is a multiple of 0.5. Days already
at or over 8 h are left alone and flagged `over_target`. Days with no commits get no rows — never
invent work for them.

Take `hours` from the output. Do not redistribute by hand; if the user disagrees with a split,
lock the row at their number and rerun, so the rest rebalances.

### The table

Write `timesheet-<since>[_<until>].md` to the scratchpad and show the same table in chat:

| # | 日期 | 票號 | 主旨 | 活動 | 估算 | 補分配 | 時數 | 說明 | 依據 | 對應方式 |

估算 = `base_hours`, 補分配 = `added_hours`, 時數 = what will be sent.

- 活動 default `9 程式開發`. Use `11 Code Review(審核)` or `12 問題討論` only when every commit in
  the row is clearly that kind of work. Never fall back to Redmine's own default activity. Resolve
  ids from `/enumerations/time_entry_activities.json` if this table looks stale.
- 說明: one Traditional Chinese line summarising the commit subjects — what was done, not how.
- 依據: session times and short hashes, e.g. `14:19–15:47 d26b18a…378e3fa (7)`.

Below the table:

- Per day: 已在 Redmine / 本次估算 / 補分配 / 送出後合計 (should read 8).
- ⚠ rows: 未對應 (unallocated — mapping it changes the split, so rerun allocate); same
  issue+date already has a time entry; a day over 8 h; sessions in different repos that
  overlap in time (parallel agents — the user decides whether both count).
- A one-line note that 補分配 is proportional to changed lines, not measured time — say 「指定某
  列時數」 to lock it and rebalance the rest.

Then stop and wait. The user edits the md file or replies with changes; re-read the file before
stage 5. Any changed 時數 becomes a `locked` row and any newly mapped issue becomes allocatable —
rerun allocate.py and redraw the table before asking for 送出.

## 5. Submit

Only after an explicit 「送出」/ yes for this table. Rows still 未對應 or with 0 hours are not
sent — list them as skipped.

For each row write a payload to the scratchpad and post it:

```json
{"time_entry":{"issue_id":57379,"spent_on":"2026-10-01","hours":2.0,"activity_id":9,"comments":"<說明>"}}
```

```bash
curl -sS --fail-with-body -X POST -H "Content-Type: application/json" \
  -H "X-Redmine-API-Key: $REDMINE_API_KEY" -d @<payload.json> "$REDMINE_URL/time_entries.json"
```

`201` with the created entry is success. Report per row: issue link `$REDMINE_URL/issues/<id>`,
hours, and the returned time entry id. On any failure, report the error body for that row,
continue with the rest, and do **not** retry automatically — a timeout does not prove the entry
was not created; check `/time_entries.json` before re-sending.
