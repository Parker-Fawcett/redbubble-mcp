# redbubble-mcp

**Redbubble MCP server — a [Model Context Protocol](https://modelcontextprotocol.io) tool server that lets AI agents (Claude, Cursor, opencode, Windsurf, any MCP client) connect to your Redbubble artist account**: upload designs, browse your portfolio, check sales and earnings, and act as your print-on-demand assistant.

> Looking for a "Redbubble MCP", "Redbubble agent tools", or a way to connect Redbubble to Claude/ChatGPT/Cursor? This is it. Redbubble ships **no official artist API**, so this server talks to Redbubble the same ways you do: their own web API (with your logged-in session) and a real browser for uploads.

## Why this exists

- **Cloudflare reality**: Redbubble is Cloudflare-protected — plain HTTP clients (requests/httpx) and even headless browsers get challenged, no matter what cookies you carry. This server runs all session traffic through a **real headed browser page** (Playwright) executing fetches in-page, which is the only setup that passes.
- Redbubble's artist dashboard runs its own **studio GraphQL API** (`POST /studio/graphql`). We capture the frontend's real queries (earnings summary, payment info, work details) and expose them as tools, plus a generic GraphQL passthrough for discovery.
- Design uploads go through a **real browser flow**: opening one of your existing works' *duplicate* page and swapping the image, so product settings and enabled products copy over exactly — the proven pattern of hand-maintained upload bots.
- Built-in safety rails because [Redbubble's guidelines allow permanent account closure](https://help.redbubble.com/hc/en-us/articles/202270929-Community-and-Content-Guidelines) for bot abuse:
  - hard cap of **30 uploads/day** (Redbubble's own published limit)
  - configurable pacing (default 5 minutes between uploads)
  - personal use by default — permission to automate is technically Redbubble's to grant in writing

## Tools

| Tool | What it does | Status |
| --- | --- | --- |
| `safety_info` | The automation ground rules (caps, pacing, ToS) | live-tested |
| `redbubble_status` | Saved session OK? How many uploads left today? | live-tested |
| `list_works` | Every portfolio work with ids, titles, edit/duplicate URLs | live-tested |
| `get_earnings` | Total earnings + 12-month earnings graph | live-tested |
| `get_payment_info` | Payout method, payability, last/next payment dates | live-tested |
| `get_work_details` | Title, tags, publication state, image + shop URL per work id | live-tested |
| `graphql_tool` | Generic passthrough to Redbubble's studio GraphQL schema | live-tested |
| `upload_work` | Upload a design file via a real browser (optionally duplicating an existing work's product setup) | works, selectors need live feedback |

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
  server.py           MCP server + tool definitions
  login.py            one-time headful login capturing your session
  browser_session.py  keeps one headed browser alive for all traffic
  browser_client.py   in-page fetch client (GraphQL + JSON GET) with challenge retry
  works.py            portfolio URL parsing
  session.py          persisted session state (~/.redbubble-mcp/)
  upload_browser.py   Playwright upload flow (Add New Work / duplicate a listed work)
  guards.py           daily cap ledger + pacing interval
```

## Roadmap

- [x] High-level profile tools (get_earnings / get_payment_info / list_works / get_work_details)
- [ ] Batch upload with per-file tags from a CSV (`title,tags,description,file`)
- [ ] Edit/delete existing works (title, tags, description, margin %)
- [ ] Sales listing page (`/account/sales`) as a tool
- [ ] Write permission guide (how to ask Redbubble for written automation approval)

## Not affiliated

This is an independent, community project. It is not affiliated with, endorsed by, or connected to Redbubble in any way, and its maintainers accept no responsibility for what third-party automation does to your account: respect the [Community & Content Guidelines](https://help.redbubble.com/hc/en-us/articles/202270929-Community-and-Content-Guidelines).

## License

MIT — see [LICENSE](LICENSE).
