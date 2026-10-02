---
name: timesheet
description: |
  Batch time logging: collect the user's commits from every repo in their saved Scope (檢查範圍), map them to work items on the time-tracking platform (Redmine today), top each day up to the Daily target (8 h by default) across the day's changes, draft a timesheet for review, and post time entries only after the user approves.
  TRIGGER — load this skill BEFORE any other action whenever the prompt says 報工時, 記工時, 填工時, 補工時, 工時清單, 今天做了什麼要報, timesheet, log time / log hours, or asks to turn today's (or a date range's) commits into time entries (Redmine or otherwise). Takes precedence over the general `redmine` skill for these requests.
  Also TRIGGER for Setup or the Scope: 設定報工時, 報工時設定, 改每日目標, 改活動, 檢查範圍, 報工時範圍, 加入/移除 repo 到報工時, 從 Herdr 匯入, list timesheet repos.
  SKIP for a single ad-hoc time entry the user fully specifies (issue, hours, activity) — use `redmine` for that.
---

# Timesheet

Three jobs: **Setup** (Platform, Activities, Daily target), editing the **Scope** (the saved
list of Repos to collect from), and running a timesheet. A timesheet run is five stages, in
order. Never skip stage 4's review, and never post in stage 5 without an explicit go-ahead in
the current turn.

`<skill-dir>` below is this skill's base directory, shown when the skill loads. Scripts and
references are resolved from it, never from a fixed install path.

Everything Platform-specific — credentials, connection check, how to fetch candidates,
Activities and already-logged hours, the submit call — lives in the Platform file
`<skill-dir>/platforms/<platform>.md`, where `<platform>` is the config's `platform`. Read it
before stage 1 (or during Setup, once the Platform is chosen) and follow its sections where this
file names them.

The user's config is read and written only through `config.py` — never edit the JSON by hand.
Every command prints JSON and exits 1 without changing anything when it rejects its input.

## Setup

Run Setup when the user asks (「設定報工時」), or automatically when stage 1 finds it incomplete
— then carry on with the timesheet they asked for once Setup finishes.

1. **Platform**: ask which Platform; the only one is `redmine`. Load its Platform file.
2. **Preflight** and **Verify** from the Platform file. On failure, explain and stop — write
   nothing.
3. **Activities**: fetch the Platform file's **Activity list** and ask the user which Activity
   to use for each of `development` (the default for every row), `review` and `discussion`.
4. **Daily target**: ask, defaulting to 8 h (0.5 h steps).
5. Write it all in one call:

   ```bash
   python3 <skill-dir>/scripts/config.py setup '{"platform": "redmine", "target_hours": 8,
     "activities": {"development": {"id": 9, "name": "程式開發"},
                    "review": {"id": 11, "name": "Code Review(審核)"},
                    "discussion": {"id": 12, "name": "問題討論"}}}'
   ```

6. If the Scope is empty (`scope_size` 0 in the result), offer 「從 Herdr 匯入」 when inside Herdr
   (`HERDR_ENV=1`), otherwise offer to add the current directory — see **Scope**.

Later single changes: `config.py set-target <hours>` (「每日目標改 7.5」), `config.py
set-activities '<json>'` (all three uses, after showing the Activity list again),
`config.py show` to display the settings. URLs and API keys stay in environment variables and
never go into the config.

## Scope

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

```bash
python3 <skill-dir>/scripts/config.py check
```

`ready: false` → run **Setup** first, then continue here. Then run the Platform file's
**Preflight**; stop with a clear message if it fails.

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
pass them to stage 4 so the rendered table lists them as ⚠. Show uncommitted work as a
note only, after the table — it carries no hours.

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

### Rows

Commit gaps miss reading, meetings and debugging, so each day with commits is topped up to the
Daily target,
and the review table is rendered by script. You prepare one file, `rows.json` in the
scratchpad; the scripts do all arithmetic and all formatting.

```json
{"since": "2026-10-01", "until": "2026-10-01",
 "logged": {"2026-10-01": 1.0},
 "existing_entries": [{"ticket": "57379", "date": "2026-10-01"}],
 "missing_repos": [],
 "rows": [{"id": "57379@2026-10-01", "date": "2026-10-01", "hours": 2.0, "lines": 11237,
           "allocatable": true, "locked": false,
           "ticket": "57379", "subject": "開發-B1-7-0 公司治理", "activity": "9 程式開發",
           "summary": "新增表單定義與欄位驗證", "basis": "14:19–15:47 d26b18a…378e3fa (7)",
           "mapping": "明確票號",
           "sessions": [{"repo": "/path/to/repo", "start": "14:19", "end": "15:47"}]}]}
```

- `hours` = the row's summed `estimated_hours`; `lines` = the row's summed session `lines`
  (changed lines, lockfiles and generated files excluded).
- `logged` = hours already on the Platform per date; `existing_entries` = the ticket+date pairs
  already there. Both from the **Already logged** call.
- `missing_repos` = collect.py's `missing_repos`, as-is.
- `allocatable: false` and no `ticket` for 未對應 rows — they get nothing and do not count
  toward the day.
- `locked: true` for any row whose hours the user set by hand — it keeps exactly that value.
- Leave out `target_hours`: allocate.py takes the Daily target from the config.
- `activity`: `"<id> <name>"` from the config's `activities` — `development` by default; use
  `review` or `discussion` only when every commit in the row is clearly that kind of work.
- `summary` (說明): one Traditional Chinese line summarising the commit subjects — what was
  done, not how.
- `basis` (依據): session times and short hashes, e.g. `14:19–15:47 d26b18a…378e3fa (7)`.
- `mapping` (對應方式): the stage 3 rule that matched.
- `sessions`: every session merged into the row, with its Repo — used to flag parallel work.

### Render

```bash
python3 <skill-dir>/scripts/allocate.py <scratchpad>/rows.json > <scratchpad>/allocated.json
python3 <skill-dir>/scripts/render.py <scratchpad>/allocated.json \
  > <scratchpad>/timesheet-<since>[_<until>].md
```

Show the md file's content in chat verbatim. Do not reformat, reorder, re-total or add rows,
and do not write any table, total or ⚠ line yourself — if something is wrong, fix `rows.json`
and rerun both scripts.

What the scripts guarantee: Top-up fills each day's shortfall (target − logged − planned) in whole
0.5 h units, split by √(changed lines) with largest remainder; days already over target are
left alone; days with no commits get no rows. The md file always has the same 11 columns, the
per-day totals, and the ⚠ list (未對應, ticket+date already logged, over target, overlapping
sessions across Repos, missing Repos).

Then stop and wait. The user edits the md file or replies with changes; re-read the file before
stage 5. Carry every change back into `rows.json`: a changed 時數 becomes a `locked` row, a
newly mapped work item becomes allocatable with its ticket. Rerun both scripts and show the new
md before asking for 送出.

## 5. Submit

Only after an explicit 「送出」/ yes for this table. Rows still 未對應 or with 0 hours are not
sent — list them as skipped.

Post each row with the Platform file's **Submit** section and report per row as it says. On any
failure, report the error body for that row, continue with the rest, and do **not** retry
automatically — a timeout does not prove the entry was not created; check with the **Already
logged** call before re-sending.
