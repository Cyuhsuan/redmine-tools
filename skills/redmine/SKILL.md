---
name: redmine
description: |
  Read and update Redmine issues through the REST API — look up an issue, list issues assigned to the user, turn an issue into a project spec draft, append a note, change status, or log time.
  TRIGGER — load this skill BEFORE any other action (before reading files, running curl, or answering from memory) whenever: the prompt says Redmine / redmine / RM in any form; contains a Redmine issue URL (…/issues/<number>) or a URL on the $REDMINE_URL host; references a bare ticket number like #1234, 單號 1234, issue 1234, 票 1234; or uses 工單, 議題, 票, ticket, 待辦單, 指派給我, 我的單, 寫進單裡, 在單上留言/回覆/備註, 改狀態, 結單, 開單 — even when the request looks like a one-liner.
  SKIP for batch time logging (報工時, 記工時, 工時清單) — use `redmine-timesheet`. Also SKIP when the issue clearly belongs to another tracker: GitHub (github.com, gh, PR), GitLab, Jira, Linear, or Notion is named or linked.
---

# Redmine

Talk to Redmine over its REST API with `curl`. No MCP server, no SDK.

## Preflight

Every call needs two environment variables:

- `REDMINE_URL` — site root, no trailing slash
- `REDMINE_API_KEY` — personal API key

If either is missing, stop and point the user at `references/setup.md`. Never guess a site
address and never ask the user to paste their API key into the conversation.

Auth is always the header `X-Redmine-API-Key: $REDMINE_API_KEY`. Always use
`curl -sS --fail-with-body` so HTTP errors surface instead of silently returning empty.

Never echo the key. Do not write it into any file, command, or commit message.

## Reading

Read operations are safe to run without asking.

```bash
curl -sS --fail-with-body -H "X-Redmine-API-Key: $REDMINE_API_KEY" \
  "$REDMINE_URL/issues/<id>.json?include=journals,attachments,relations"
```

Endpoint details, query parameters and paging are in `references/api.md` — read it before
composing anything beyond a plain issue fetch.

When summarising an issue, cover: 主旨、狀態、指派對象、追蹤標籤、目前卡在哪、驗收條件.
Separate **確認的需求** from **待釐清事項**; never present an inference as a requirement.
Report what the API returned — if a field is empty, say it is empty rather than filling it in.

When listing issues, render a table (編號 / 主旨 / 專案 / 狀態 / 優先權 / 最後更新)，依最後更新
日新到舊，並指出停滯最久的幾筆。

## Writing

Appending a note, changing a status, logging time — these are outward-facing writes to a shared
tracker other people read.

1. `GET` the issue first and show the user its subject and current status.
2. Draft the note and **show the exact text before sending**. Get an explicit yes unless the
   user already authorised this write in the current turn.
3. Build the payload as a JSON file in the scratchpad directory, never inline in the URL and
   never inside the repository.
4. `PUT`. A successful update returns `204` with no body — that is normal, not a failure.
5. Report the result with the `$REDMINE_URL/issues/<id>` link.

Notes describe only what actually happened. If tests failed, say so.

Changing `status_id` or `done_ratio` requires confirming the target value with the user first —
resolve the numeric id from `references/api.md`, do not guess it.

## Turning an issue into a spec

Read the current project's `AGENTS.md` / `CLAUDE.md` and whatever issue-tracker document they
point at, then follow **that project's** spec layout, file naming and status vocabulary. If the
project documents no convention, ask where the file belongs — do not invent a path.

Stamp `Redmine: $REDMINE_URL/issues/<id>` at the top of the generated file for traceability.
If the target file already exists, read it and decide whether to merge or open a new file. Never
overwrite silently.

## Boundaries

Redmine is the source of truth for issue status; the project's spec files are the working
document. When they disagree, surface the difference and ask — do not silently sync either way.

Output language follows the project's convention; default to Traditional Chinese when the
project states none.
