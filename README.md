# redbubble-mcp

**Redbubble MCP server — a [Model Context Protocol](https://modelcontextprotocol.io) tool server that lets AI agents (Claude, Cursor, opencode, Windsurf, any MCP client) connect to your Redbubble artist account**: upload designs, browse your portfolio, check sales and earnings, and act as your print-on-demand assistant.

> Looking for a "Redbubble MCP", "Redbubble agent tools", or a way to connect Redbubble to Claude/ChatGPT/Cursor? This is it. Redbubble ships **no official artist API**, so this server talks to Redbubble the same ways you do: their own web API (with your logged-in session) and a real browser for uploads.

## Why this exists

- Redbubble's own internal web API (`redbubble.com/api/v2/...`) is undocumented and cookie-authenticated — this server wraps it with your saved session.
- Design uploads are done through a **real browser window** (Playwright) so that logins, captchas and Cloudflare stay human, not headless.
- Built-in safety rails because [Redbubble's guidelines allow permanent account closure](https://help.redbubble.com/hc/en-us/articles/202270929-Community-and-Content-Guidelines) for bot abuse:
  - hard cap of **30 uploads/day** (Redbubble's own published limit)
  - configurable pacing (default 5 minutes between uploads)
  - personal use by default — permission to automate is technically Redbubble's to grant in writing

## Tools

| Tool | What it does |
| --- | --- |
| `safety_info` | The automation ground rules (caps, pacing, ToS) |
| `redbubble_status` | Saved session OK? How many uploads left today? |
| `redbubble_get(path, params)` | Read-only GET against any Redbubble internal-API path |
| `redbubble_post(path, payload)` | Write via the internal API — use sparingly |
| `upload_work(image, title, tags, ...)` | Upload a design file via a real browser (optionally duplicating an existing work's product setup) |

Endpoint paths are undocumented, so generic `redbubble_get`/`redbubble_post` are exposed so agents can **discover endpoints live** against the account owner's session instead of relying on hard-coded guesses that rot.

## Install

```bash
python -m pip install redbubble-mcp
python -m playwright install chromium   # first time only
pipx install redbubble-mcp              # alternative: isolated CLI install
```

From source:

```bash
git clone https://github.com/businessfawcett-cloud/redbubble-mcp
cd redbubble-mcp
python -m pip install -e .
python -m playwright install chromium
```

## Log in once

`redbubble-mcp-login` opens a browser window; **you** log into Redbubble (any captcha is solved by you). Cookies are saved to `~/.redbubble-mcp/` (never committed anywhere) and reused until they expire — re-run the command whenever the agent reports a session error.

```bash
redbubble-mcp-login
```

## Wire it into your agent

Claude Desktop / Claude Code (`claude_desktop_config.json` / `.mcp.json`), opencode, Cursor, or any MCP client:

```jsonc
{
  "mcpServers": {
    "redbubble": {
      "command": "redbubble-mcp",
      "args": []
    }
  }
}
```

If installed with pipx, `"command": "redbubble-mcp"` still works; otherwise point `command` at your interpreter: `["python", "-m", "redbubble_mcp.server"]`.

Example operating style for the agent goading your assistant along:

- *Pending earnings?* → `redbubble_get` with your account's sales/earnings paths
- *Upload this PNG, 15 tags, sticker/t-shirt settings like my last design* → `upload_work(..., template_work_url=<your best listing>)`
- *Status?* → `redbubble_status`

## Repo layout

```
src/redbubble_mcp/
  server.py          MCP server + tool definitions
  login.py           one-time headful login capturing your session
  client.py          authenticated HTTP client (cookie + XSRF handling)
  session.py         persisted cookie store (~/.redbubble-mcp/session.json)
  upload_browser.py  Playwright upload flow (Add New Work / duplicate a listed work)
  guards.py          daily cap ledger + pacing interval
```

## Roadmap

- [ ] High-level profile tools (list_works / get_sales / get_earnings) once endpoint paths are confirmed against live sessions
- [ ] Batch upload with per-file tags from a CSV (`title,tags,description,file`)
- [ ] Edit/delete existing works (title, tags, description, margin %)
- [ ] Write permission guide (how to ask Redbubble for written automation approval)

## Not affiliated

This is an independent, community project. It is not affiliated with, endorsed by, or connected to Redbubble in any way, and its maintainers accept no responsibility for what third-party automation does to your account: respect the [Community & Content Guidelines](https://help.redbubble.com/hc/en-us/articles/202270929-Community-and-Content-Guidelines).

## License

MIT — see [LICENSE](LICENSE).
