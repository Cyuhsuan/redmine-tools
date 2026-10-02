# Redmine REST API reference

Base: `$REDMINE_URL`. Auth header on every request: `X-Redmine-API-Key: $REDMINE_API_KEY`.
All endpoints below are the `.json` form; `.xml` also exists but is not used here.

## Reading

| Purpose | Call |
| --- | --- |
| One issue, full detail | `GET /issues/<id>.json?include=journals,attachments,relations,children` |
| Issues assigned to me | `GET /issues.json?assigned_to_id=me&status_id=open&sort=updated_on:desc&limit=50` |
| Issues in a project | add `&project_id=<identifier-or-id>` |
| Search by subject | `GET /issues.json?subject=~<text>` |
| Updated since | `GET /issues.json?updated_on=>%3D2026-01-01` |
| Current user (connectivity check) | `GET /users/current.json` |
| Projects | `GET /projects.json?limit=100` |
| Time entries on an issue | `GET /time_entries.json?issue_id=<id>` |

`status_id` accepts `open`, `closed`, `*`, or a numeric id. Filters combine with `&`; a `~`
prefix means "contains", and comparison operators must be URL-encoded (`>=` → `%3E%3D`).

### Paging

List endpoints return `total_count`, `offset`, `limit` (max 100). Page with `&offset=`. Do not
fetch every page by reflex — take the first page and say how many more exist unless the user
asked for the full set.

### Resolving ids

Numeric ids for statuses, priorities and trackers differ per installation. Look them up rather
than assuming:

| Purpose | Call |
| --- | --- |
| Statuses | `GET /issue_statuses.json` |
| Priorities | `GET /enumerations/issue_priorities.json` |
| Trackers | `GET /trackers.json` |
| Activities (for time entries) | `GET /enumerations/time_entry_activities.json` |
| Custom fields | `GET /custom_fields.json` (admin only) |

Custom fields come back on an issue as `custom_fields: [{id, name, value}]`. Match on `name`,
not on position.

## Writing

Write the body to a JSON file in the scratchpad directory and send it with `-d @<file>`.

```bash
curl -sS --fail-with-body -X PUT \
  -H "Content-Type: application/json" \
  -H "X-Redmine-API-Key: $REDMINE_API_KEY" \
  -d @<payload.json> \
  "$REDMINE_URL/issues/<id>.json"
```

| Purpose | Call | Body |
| --- | --- | --- |
| Append a note | `PUT /issues/<id>.json` | `{"issue":{"notes":"..."}}` |
| Private note | same | add `"private_notes": true` |
| Change status / progress | same | `{"issue":{"status_id":N,"done_ratio":50,"notes":"..."}}` |
| Create an issue | `POST /issues.json` | `{"issue":{"project_id":"x","subject":"...","description":"..."}}` |
| Log time | `POST /time_entries.json` | `{"time_entry":{"issue_id":N,"hours":1.5,"activity_id":N,"comments":"..."}}` |

`PUT` returns `204 No Content` on success. `POST` returns `201` with the created object.

## Errors

| Code | Meaning |
| --- | --- |
| `401` | Bad key, or the REST web service is disabled in Administration → Settings → API |
| `403` | Key is valid but lacks permission on that project, or the issue is private |
| `404` | No such issue, or the project is not visible to this account |
| `422` | Validation failed — the body lists `errors`; read them, do not retry blindly |

A `422` usually means a required custom field is missing or a numeric id does not exist in this
installation. Re-read the ids rather than guessing a different number.

## Attachments

`include=attachments` returns each attachment's `content_url`. Downloading needs the same auth
header. Download only when the user asks — attachments can be large and may be confidential.
