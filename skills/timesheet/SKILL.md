---
name: timesheet
description: |
  Batch time logging: collect the user's commits from every repo in their saved Scope (檢查範圍), map them to work items on the time-tracking platform (Redmine today), top each day up to 8 h across the day's changes, draft a timesheet for review, and post time entries only after the user approves.
  TRIGGER — load this skill BEFORE any other action whenever the prompt says 報工時, 記工時, 填工時, 補工時, 工時清單, 今天做了什麼要報, timesheet, log time / log hours, or asks to turn today's (or a date range's) commits into time entries (Redmine or otherwise). Takes precedence over the general `redmine` skill for these requests.
  Also TRIGGER to view or edit the Scope: 檢查範圍, 報工時範圍, 加入/移除 repo 到報工時, 從 Herdr 匯入, list timesheet repos.
  SKIP for a single ad-hoc time entry the user fully specifies (issue, hours, activity) — use `redmine` for that.
---

# Timesheet

Two jobs: editing the **Scope** (the saved list of Repos to collect from) and running a
timesheet. A timesheet run is five stages, in order. Never skip stage 4's review, and never post in stage 5 without an explicit
go-ahead in the current turn.

`<skill-dir>` below is this skill's base directory, shown when the skill loads. Scripts and
references are resolved from it, never from a fixed install path.

Everything Platform-specific — credentials, how to fetch candidates and already-logged hours,
Activity ids, the submit call — lives in the Platform file. The Platform is Redmine; read
`<skill-dir>/platforms/redmine.md` before stage 1 and follow its sections where this file names
them.

## Scope

The Scope lives in the user's config file and is read and written only through
`config.py` — never edit the JSON by hand. Every command prints JSON.

```bash
python3 <skill-dir>/scripts/config.py list
python3 <skill-dir>/scripts/config.py add <path>      # "加入這個 repo" → the current directory
python3 <skill-dir>/scripts/config.py remove <path>
python3 <skill-dir>/scripts/config.py import-herdr [--workspace <id>]   # "從 Herdr 匯入"
```

`add` saves the main worktree root, so a subdirectory or another worktree of the same repo
lands on the same entry. Report its `status` as-is: `added`, `exists` (already in the Scope),
or `rejected` with its `reason`. `remove` also works for a Repo whose directory is gone.

`import-herdr` is a one-time Import of the Repos open in a Herdr workspace — the current one
unless the user names another (`herdr workspace list` shows ids and labels). Report its
`added`, `exists` and `skipped` (with reasons) lists. It is a snapshot: tell the user later
Herdr changes will not update the Scope. On `not_in_herdr`, say Import needs a Herdr pane and
offer `add` instead.

## 1. Enter

Run the Platform file's **Preflight**; stop with a clear message if it fails.

Date range: whatever the user said ("昨天", "這週", a date). Default today. Say the resolved
dates back in the first line of the reply.

## 2. Collect

```bash
python3 <skill-dir>/scripts/collect.py --since <YYYY-MM-DD> [--until <YYYY-MM-DD>] [--repo <path> ...]
```

Pass `--repo` only when the user narrowed this run to particular Repos ("只報 a-repo"). It does
not change the Scope.

Exit 1 with an `error`:

- `empty_scope` → stop and tell the user to add Repos or import from Herdr (see **Scope**). Never fall back to
  guessing repos from Herdr panes or the current directory.
- `not_in_scope` → ask whether to add those Repos to the Scope; add them only on a yes, then
  rerun.

Otherwise it returns, for each Repo, the user's own
non-merge commits (author = that repo's `user.email`, filtered on author date) grouped by branch
into **sessions**: consecutive commits no more than 2 h apart on the same day.
`estimated_hours` = (last − first commit) + 0.5 h lead time, rounded to 0.5, minimum 0.5.

Also reported: `missing_repos` — Scope entries whose path is gone or no longer a repo — and
`uncommitted` changes. Missing Repos are skipped, never removed from the Scope automatically;
list them as ⚠ under the table. Show uncommitted work as a note only — it carries no hours.

## 3. Map to work items

Fetch the candidates once, using the Platform file's **Candidates** call.

For each branch group, take the first rule that matches and record which one:

| 依據 | Rule |
| --- | --- |
| 明確票號 | An explicit reference (Platform file's **Explicit references**) in a commit subject or branch name |
| 規格連結 | A spec link (Platform file's **Explicit references**) in the repo's `.scratch/<feature>/` spec or docs matching the branch's feature |
| 主旨比對 | A feature code in the branch (e.g. `B1-7` from `feat_B1-7`) appears in exactly one candidate subject (`開發-B1-7-0 公司治理`), or the commit subjects clearly describe one candidate (表單定義 → `[後台] 表單管理`) — scoped to the candidate whose project matches the repo |
| 未對應 | Nothing above, or more than one candidate fits |

Never guess between multiple candidates. 未對應 rows go to the user in stage 4.

Merge sessions that map to the same work item on the same date into one row; keep the session
times in the 依據 column.

## 4. Draft the timesheet for review

Fetch what is already logged for the range so nothing is double-counted, using the Platform
file's **Already logged** call.

### Top up to 8 h

Commit gaps miss reading, meetings and debugging, so each day with commits is topped up to 8 h.
Write the work-item rows to `rows.json` in the scratchpad and run:

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
- `logged` = hours already on the Platform per date, from the call above.
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

- 活動: the Platform file's **Activities** — default is the development activity. Use review or
  discussion only when every commit in the row is clearly that kind of work.
- 說明: one Traditional Chinese line summarising the commit subjects — what was done, not how.
- 依據: session times and short hashes, e.g. `14:19–15:47 d26b18a…378e3fa (7)`.

Below the table:

- Per day: 已在平台 / 本次估算 / 補分配 / 送出後合計 (should read 8).
- ⚠ rows: 未對應 (unallocated — mapping it changes the split, so rerun allocate); same
  work item+date already has a time entry; a day over 8 h; sessions in different repos that
  overlap in time (parallel agents — the user decides whether both count); each missing Repo
  with its reason (say 「移除 <repo>」 to drop it from the Scope).
- A one-line note that 補分配 is proportional to changed lines, not measured time — say 「指定某
  列時數」 to lock it and rebalance the rest.

Then stop and wait. The user edits the md file or replies with changes; re-read the file before
stage 5. Any changed 時數 becomes a `locked` row and any newly mapped work item becomes
allocatable — rerun allocate.py and redraw the table before asking for 送出.

## 5. Submit

Only after an explicit 「送出」/ yes for this table. Rows still 未對應 or with 0 hours are not
sent — list them as skipped.

Post each row with the Platform file's **Submit** section and report per row as it says. On any
failure, report the error body for that row, continue with the rest, and do **not** retry
automatically — a timeout does not prove the entry was not created; check with the **Already
logged** call before re-sending.
