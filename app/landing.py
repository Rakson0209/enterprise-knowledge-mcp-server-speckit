"""Landing page that dynamically lists the currently registered MCP tools and resources (FR-019)."""

from __future__ import annotations

from app.mcp_server import REGISTERED_RESOURCES, REGISTERED_TOOLS


def render_landing_page() -> str:
    tools = "".join(f"<li><code>{t}</code></li>" for t in REGISTERED_TOOLS)
    resources = "".join(f"<li><code>{r}</code></li>" for r in REGISTERED_RESOURCES)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Enterprise Knowledge MCP Server</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 720px; margin: 3rem auto; padding: 0 1rem;
         line-height: 1.5; color: #1a1a1a; }}
  code {{ background: #f2f2f2; padding: 0.1rem 0.35rem; border-radius: 4px; }}
  h1 {{ margin-bottom: 0.25rem; }}
  .muted {{ color: #666; }}
  a {{ color: #2b6cb0; }}
</style>
</head>
<body>
  <h1>Enterprise Knowledge MCP Server</h1>
  <p class="muted">A hybrid-search knowledge base over DOCX/PDF/PPTX, exposed as a Remote MCP
     Server for AI agents.</p>

  <h2>MCP endpoint</h2>
  <p>Connect an MCP client (Claude Desktop / Claude Code) to <code>/mcp</code>.</p>

  <h2>Tools</h2>
  <ul>{tools}</ul>

  <h2>Resources</h2>
  <ul>{resources}</ul>

  <h2>Other endpoints</h2>
  <ul>
    <li><a href="/health">/health</a> — liveness check</li>
    <li><a href="/docs">/docs</a> — REST API documentation</li>
    <li><code>POST /documents</code> — upload a document (auto-indexed, no restart)</li>
    <li><a href="/documents">/documents</a> — catalogue of indexed documents</li>
  </ul>
</body>
</html>"""
