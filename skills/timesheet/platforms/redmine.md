# Platform: Redmine

Everything the `timesheet` flow needs that is specific to Redmine. Work items are Redmine
issues; the 票號 column holds the issue id.

Shared rules from the `redmine` skill apply: auth header `X-Redmine-API-Key: $REDMINE_API_KEY`,
`curl -sS --fail-with-body`, never echo or store the key, payloads go in the scratchpad.

## Preflight

```bash
test -n "${REDMINE_URL:-}" && test -n "${REDMINE_API_KEY:-}"
```

Missing → point at `<skill-dir>/../redmine/references/setup.md` and stop.

## Verify

Setup's connection check:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' \
  -H "X-Redmine-API-Key: $REDMINE_API_KEY" "$REDMINE_URL/users/current.json"
```

| Result | Meaning |
| --- | --- |
| `200` | Working |
| `401` | Wrong key, or the REST web service is disabled |
| `000` | Cannot reach the host — URL, VPN or DNS |

Anything but `200` → explain with this table and point at
`<skill-dir>/../redmine/references/setup.md`.

## Activity list

Setup offers the site's own Activities:

```bash
curl -sS --fail-with-body -H "X-Redmine-API-Key: $REDMINE_API_KEY" \
  "$REDMINE_URL/enumerations/time_entry_activities.json"
```

Offer only entries with `active: true`. The `is_default` entry is a hint for `development`,
nothing more — the user picks each of the three.

## Candidates

Fetch once per run:

```bash
curl -sS --fail-with-body -H "X-Redmine-API-Key: $REDMINE_API_KEY" \
  "$REDMINE_URL/issues.json?assigned_to_id=me&status_id=open&limit=100"
```

Each candidate's project is `project.name`; subject is `subject`.

## Explicit references

What counts as an explicit issue reference for the 明確票號 and 規格連結 rules:

- In a commit subject or branch name: `#12345`, `refs #12345`, `issues/12345`
- In a repo's `.scratch/<feature>/` spec or docs: a `Redmine: …/issues/<id>` line

## Already logged

```bash
curl -sS --fail-with-body -H "X-Redmine-API-Key: $REDMINE_API_KEY" \
  "$REDMINE_URL/time_entries.json?user_id=me&from=<since>&to=<until>&limit=100"
```

Sum `hours` per `spent_on` for `logged`; keep `issue.id` + `spent_on` pairs for the
"same issue+date already has a time entry" warning.

## Activities

The ids come from the user's config (`activities`), chosen in Setup from the Activity list.
Send the configured id as `activity_id`; never fall back to Redmine's own default activity.

## Submit

For each row write a payload to the scratchpad and post it:

```json
{"time_entry":{"issue_id":57379,"spent_on":"2026-10-01","hours":2.0,"activity_id":9,"comments":"<說明>"}}
```

```bash
curl -sS --fail-with-body -X POST -H "Content-Type: application/json" \
  -H "X-Redmine-API-Key: $REDMINE_API_KEY" -d @<payload.json> "$REDMINE_URL/time_entries.json"
```

`201` with the created entry is success. Report per row: issue link `$REDMINE_URL/issues/<id>`,
hours, and the returned time entry id. To check whether an entry exists before re-sending, use
the Already logged call.
