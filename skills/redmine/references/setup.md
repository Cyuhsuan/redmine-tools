# Redmine setup

One-time, per machine. Everything the `redmine` skill does runs through `curl` against the
Redmine REST API, so the only setup is enabling that API and exporting two variables.

## 1. Enable the REST API

In Redmine: **Administration → Settings → API → Enable REST web service**. This needs an
administrator; if you are not one, ask whoever runs the instance.

## 2. Get your API key

Go to `/my/account`. The **API access key** is in the right sidebar, behind a "Show" link.
It is a personal credential — it carries your own permissions, so treat it like a password.

## 3. Export the variables

Add to `~/.zshrc`:

```bash
export REDMINE_URL="https://redmine.example.com"   # no trailing slash
export REDMINE_API_KEY="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

Never commit these into a repository, a skill file, or a settings file that is checked in.

## 4. Verify

Restart the shell, then:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' \
  -H "X-Redmine-API-Key: $REDMINE_API_KEY" "$REDMINE_URL/users/current.json"
```

| Result | Meaning |
| --- | --- |
| `200` | Working |
| `401` | Wrong key, or the REST web service is still disabled |
| `000` | Cannot reach the host — check the URL, VPN, or DNS |

## Optional: fewer permission prompts

Read-only calls can be allowlisted in `~/.claude/settings.json` so they stop prompting:

```json
{
  "permissions": {
    "allow": ["Bash(curl -sS --fail-with-body -H \"X-Redmine-API-Key: $REDMINE_API_KEY\" \"$REDMINE_URL/*\")"]
  }
}
```

Keep writes (`-X PUT`, `-X POST`) out of the allowlist — they should stay behind a prompt.

## Rotating the key

Regenerate it at `/my/account` ("Reset" next to the API access key), then update `~/.zshrc`.
The old key stops working immediately.
