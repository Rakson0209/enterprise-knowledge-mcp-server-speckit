"""Landing page that dynamically lists the currently registered MCP tools and resources (FR-019)."""

from __future__ import annotations

from app import __version__
from app.mcp_server import REGISTERED_RESOURCES, REGISTERED_TOOLS

# Human-readable metadata for the registered tools/resources, keyed by name so the page stays in
# sync with what mcp_server actually exposes.
_TOOL_META: dict[str, dict] = {
    "search_documents": {
        "desc": "以混合檢索（Dense + BM25，RRF 融合）搜尋最相關的 chunk，回傳內容、中繼資料與分數。",
        "params": [("query", "string", False), ("top_k", "integer", True)],
    },
    "list_documents": {
        "desc": "列出目前已索引的所有文件目錄。",
        "params": [],
    },
    "get_document": {
        "desc": "回傳文件層級中繼資料（chunk 數、頁碼／投影片範圍）。",
        "params": [("document_id", "string", False)],
    },
    "get_chunk": {
        "desc": "依 id 回傳單一 chunk 的完整內容與中繼資料。",
        "params": [("chunk_id", "string", False)],
    },
}

_RESOURCE_META: dict[str, str] = {
    "documents://all": "所有已索引文件的完整目錄。",
    "documents://{document_id}": "單一文件及其所有 chunk。",
}

_QUICK_LINKS = [
    ("/docs", "API 文件 (Swagger UI)", "互動式 REST API 文件，可直接在瀏覽器試打上傳等端點。"),
    ("/redoc", "API 文件 (ReDoc)", "另一種唯讀、易讀的 API 參考排版。"),
    ("/health", "健康檢查", "存活探測；回傳 {\"status\": \"ok\"}。"),
    ("/documents", "文件目錄 (REST)", "列出所有已索引的文件（GET）。"),
]

_STACK = [
    ("Language", "Python 3.11"),
    ("Web API", "FastAPI (async / ASGI)"),
    ("Parsing", "Docling (+ RapidOCR)"),
    ("Dense Retrieval", "BGE-M3 (1024-dim, L2)"),
    ("Sparse Retrieval", "BM25 (rank-bm25)"),
    ("Fusion", "Reciprocal Rank Fusion (k=60)"),
    ("Vector DB", "Chroma (embedded, persistent)"),
    ("MCP Framework", "FastMCP"),
    ("Deploy", "Docker → Zeabur (Arm Ampere A1, CPU-only)"),
]

_QUERIES = [
    "What is the yield improvement plan?",
    "Show me the KPI table from the Q4 report.",
    "Summarize slide 5.",
    "良率改善計畫的目標是什麼？",
]

_FLOW = """DOCX / PDF / PPTX
   -> Docling Parser (+ RapidOCR 圖片文字)
   -> Cleaning Pipeline (去重複頁首頁尾 / 頁碼 / 純符號雜訊，保留結構)
   -> Metadata-aware Chunking (沿標題 / 頁 / 投影片 / 表格 / 圖片邊界切，禁固定字數)
   -> Hybrid Index (BGE-M3 dense + BM25 sparse, RRF 融合, Chroma)
   -> Remote MCP Server (FastMCP)
   -> Claude Desktop / Claude Code / AI Agent"""

_CSS = """
  :root {
    --bg:#0d1117; --panel:#161b22; --border:#30363d; --text:#e6edf3;
    --muted:#8b949e; --accent:#58a6ff; --accent2:#3fb950; --code-bg:#1f2630;
  }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--text); line-height:1.65;
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang TC","Microsoft JhengHei",Roboto,Helvetica,Arial,sans-serif;
    -webkit-font-smoothing:antialiased; }
  a { color:var(--accent); text-decoration:none; }
  code { font-family:"SF Mono","Cascadia Code",Consolas,"Liberation Mono",monospace;
    background:var(--code-bg); padding:.12em .4em; border-radius:5px; font-size:.9em; color:#d2d9e0; }
  .wrap { max-width:960px; margin:0 auto; padding:0 20px 80px; }
  header { border-bottom:1px solid var(--border);
    background:linear-gradient(180deg,#11151c 0%,var(--bg) 100%); padding:56px 20px 40px; }
  header .inner { max-width:960px; margin:0 auto; }
  .badge { display:inline-block; font-size:.75rem; color:var(--accent2);
    border:1px solid var(--accent2); border-radius:999px; padding:2px 10px; margin-bottom:14px; letter-spacing:.04em; }
  h1 { font-size:2.1rem; margin:0 0 8px; line-height:1.2; }
  .tagline { color:var(--muted); font-size:1.08rem; max-width:700px; margin:0; }
  .ver { color:var(--muted); font-size:.85rem; margin-top:10px; }
  section { margin-top:44px; }
  h2 { font-size:1.25rem; margin:0 0 16px; padding-bottom:8px; border-bottom:1px solid var(--border); }
  .grid { display:grid; gap:14px; grid-template-columns:repeat(auto-fill,minmax(230px,1fr)); }
  .card { background:var(--panel); border:1px solid var(--border); border-radius:10px; padding:16px 18px; }
  a.link { display:block; transition:border-color .15s, transform .15s; }
  a.link:hover { border-color:var(--accent); transform:translateY(-2px); }
  .link-title { font-weight:600; color:var(--text); }
  .arrow { color:var(--accent); }
  .link-path { margin:4px 0 8px; }
  .link-desc { margin:0; color:var(--muted); font-size:.88rem; }
  .tool-name { font-size:1rem; color:var(--accent2); background:transparent; padding:0; font-weight:600; }
  .tool-desc { margin:6px 0 12px; color:var(--text); font-size:.92rem; }
  .params { display:flex; flex-wrap:wrap; gap:6px; }
  .param { display:inline-flex; align-items:center; gap:6px; background:var(--code-bg);
    border:1px solid var(--border); border-radius:6px; padding:2px 8px; font-size:.82rem; }
  .param code { background:transparent; padding:0; }
  .param .ptype { color:var(--muted); font-size:.78rem; }
  .opt { color:var(--muted); }
  .endpoint { background:var(--panel); border:1px solid var(--border); border-radius:10px; padding:18px; }
  .endpoint .row { display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
  .endpoint code#mcp-url { font-size:.95rem; color:var(--accent); }
  button.copy { background:var(--accent); color:#fff; border:0; border-radius:6px;
    padding:5px 12px; cursor:pointer; font-size:.82rem; }
  button.copy:hover { opacity:.9; }
  .note { color:var(--muted); font-size:.82rem; margin:10px 0 0; }
  .note b { color:var(--accent2); }
  ul.plain { list-style:none; padding:0; margin:0; }
  ul.plain li { padding:8px 0; border-bottom:1px solid var(--border); }
  ul.plain li:last-child { border-bottom:0; }
  .rdesc { color:var(--muted); font-size:.88rem; margin-left:10px; }
  ul.queries { list-style:none; padding:0; margin:0; display:grid; gap:8px; }
  ul.queries code { display:block; padding:10px 14px; }
  table.stack { width:100%; border-collapse:collapse; }
  table.stack th, table.stack td { text-align:left; padding:9px 14px; border-bottom:1px solid var(--border); font-weight:400; }
  table.stack th { color:var(--muted); width:210px; }
  pre.flow { background:var(--panel); border:1px solid var(--border); border-radius:10px;
    padding:18px; overflow-x:auto; color:var(--muted); font-size:.85rem; line-height:1.5; }
  .muted { color:var(--muted); }
  footer { margin-top:56px; padding-top:20px; border-top:1px solid var(--border); color:var(--muted); font-size:.85rem; }
"""


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _quick_links_html() -> str:
    out = []
    for path, title, desc in _QUICK_LINKS:
        out.append(
            f'<a class="card link" href="{path}">'
            f'<div class="link-title">{_esc(title)} <span class="arrow">&rarr;</span></div>'
            f'<div class="link-path"><code>{path}</code></div>'
            f'<p class="link-desc">{_esc(desc)}</p></a>'
        )
    return "\n".join(out)


def _tools_html() -> str:
    opt_marker = "<span class='opt'>?</span>"
    cards = []
    for name in REGISTERED_TOOLS:
        meta = _TOOL_META.get(name, {"desc": "", "params": []})
        if meta["params"]:
            chip_parts = []
            for (p, t, opt) in meta["params"]:
                mark = opt_marker if opt else ""
                chip_parts.append(
                    f'<span class="param"><code>{p}{mark}</code>'
                    f'<span class="ptype">{t}</span></span>'
                )
            chips = "".join(chip_parts)
        else:
            chips = '<span class="muted">無參數</span>'
        cards.append(
            f'<div class="card tool"><code class="tool-name">{name}</code>'
            f'<p class="tool-desc">{_esc(meta["desc"])}</p>'
            f'<div class="params">{chips}</div></div>'
        )
    return "\n".join(cards)


def _resources_html() -> str:
    items = []
    for uri in REGISTERED_RESOURCES:
        desc = _RESOURCE_META.get(uri, "")
        items.append(f'<li><code>{_esc(uri)}</code><span class="rdesc">{_esc(desc)}</span></li>')
    return "\n".join(items)


def render_landing_page() -> str:
    quick = _quick_links_html()
    tools = _tools_html()
    resources = _resources_html()
    stack = "\n".join(f"<tr><th>{_esc(k)}</th><td>{_esc(v)}</td></tr>" for k, v in _STACK)
    queries = "\n".join(f"<li><code>{_esc(q)}</code></li>" for q in _QUERIES)
    flow = _esc(_FLOW)

    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Enterprise Knowledge MCP Server</title>
<style>{_CSS}</style>
</head>
<body>
<header>
  <div class="inner">
    <span class="badge">REMOTE MCP SERVER</span>
    <h1>Enterprise Knowledge MCP Server</h1>
    <p class="tagline">企業文件知識庫系統：匯入 DOCX / PDF / PPTX，以 Docling 解析、清洗、沿語意邊界切塊，
      建立 BGE-M3 + BM25 混合檢索索引，並透過 Model Context Protocol 對 Claude Desktop 等 AI Agent 提供查詢能力。</p>
    <div class="ver">v{__version__} · FastAPI + FastMCP · {len(REGISTERED_TOOLS)} tools · {len(REGISTERED_RESOURCES)} resources</div>
  </div>
</header>

<div class="wrap">

  <section>
    <h2>快速入口</h2>
    <div class="grid">
{quick}
    </div>
  </section>

  <section>
    <h2>連線 MCP Server</h2>
    <div class="endpoint">
      <p class="muted" style="margin-top:0">將 MCP 客戶端（Claude Desktop / Claude Code）指向以下端點即可使用。
        此為 streamable HTTP 端點，無法直接用瀏覽器開啟。</p>
      <div class="row">
        <code id="mcp-url">/mcp/</code>
        <button class="copy" onclick="copyMcp()">複製</button>
        <span id="copied" class="muted" style="display:none">已複製 ✓</span>
      </div>
      <p class="note">注意：端點結尾<b>必須含斜線 <code>/mcp/</code></b>；連 <code>/mcp</code>（無斜線）會因 redirect 導致連線失敗。</p>
    </div>
  </section>

  <section>
    <h2>MCP Tools <span class="muted" style="font-size:.8rem">（{len(REGISTERED_TOOLS)} 個）</span></h2>
    <div class="grid">
{tools}
    </div>
  </section>

  <section>
    <h2>MCP Resources <span class="muted" style="font-size:.8rem">（{len(REGISTERED_RESOURCES)} 個）</span></h2>
    <div class="card"><ul class="plain">
{resources}
    </ul></div>
  </section>

  <section>
    <h2>範例查詢</h2>
    <ul class="queries">
{queries}
    </ul>
  </section>

  <section>
    <h2>處理流程</h2>
    <pre class="flow">{flow}</pre>
  </section>

  <section>
    <h2>技術選型</h2>
    <table class="stack">
{stack}
    </table>
  </section>

  <footer>Enterprise Knowledge MCP Server · 以 AI-only workflow（Claude Code + Spec Kit）開發。</footer>
</div>

<script>
  (function () {{
    document.getElementById('mcp-url').textContent = window.location.origin + '/mcp/';
  }})();
  function copyMcp() {{
    navigator.clipboard.writeText(document.getElementById('mcp-url').textContent).then(function () {{
      var c = document.getElementById('copied');
      c.style.display = 'inline';
      setTimeout(function () {{ c.style.display = 'none'; }}, 1800);
    }});
  }}
</script>
</body>
</html>"""
