"""
HTML Log Viewer Generator
Creates an HTML file similar to Robot Framework's log.html for viewing test logs
"""
import os
import re
from datetime import datetime
from pathlib import Path
import json
from html import escape


def _guess_level(message: str) -> str:
    m = (message or "").upper()
    if "TRACEBACK" in m or "ERROR" in m or "EXCEPTION" in m:
        return "ERROR"
    if "WARNING" in m or "WARN" in m:
        return "WARNING"
    if "DEBUG" in m:
        return "DEBUG"
    return "INFO"


def _windows_path_to_file_url(path: str) -> str:
    # C:\a\b -> file:///C:/a/b
    p = (path or "").strip()
    if not p:
        return ""
    p = p.replace("\\", "/")
    if re.match(r"^[A-Za-z]:/", p):
        return "file:///" + p
    return p


def parse_log_file(log_file_path: str):
    """
    Parse the log and return:
      - entries: list of line entries
      - tests: grouped sections detected by 'TEST <name>' blocks (Robot-style logs)
    """
    entries = []
    tests = []

    # Parse log line format: YYYY-MM-DD HH:MM:SS [LEVEL] file:line - logger: message
    std_pattern = re.compile(
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+\[(\s+)(\w+)\]\s+([^:]+):(\d+)\s+-\s+([^:]+):\s+(.+)"
    )

    current_test = None

    with open(log_file_path, "r", encoding="utf-8") as f:
        for line_no, raw_line in enumerate(f, 1):
            line = raw_line.rstrip("\n")
            if not line.strip():
                continue

            m = std_pattern.match(line.strip())
            if m:
                timestamp, _spaces, level, filename, src_line, logger, message = m.groups()
                level = (level or "").strip().upper() or "INFO"
                entry = {
                    "idx": len(entries),
                    "line_no": line_no,
                    "timestamp": timestamp,
                    "level": level,
                    "filename": (filename or "").strip(),
                    "src_line": (src_line or "").strip(),
                    "logger": (logger or "").strip(),
                    "message": message,
                    "raw": line.strip(),
                }
            else:
                msg = line.strip()
                entry = {
                    "idx": len(entries),
                    "line_no": line_no,
                    "timestamp": "",
                    "level": _guess_level(msg),
                    "filename": "",
                    "src_line": "",
                    "logger": "",
                    "message": msg,
                    "raw": msg,
                }

            # Detect Robot-style test boundaries
            msg = entry["message"]
            if msg.startswith("TEST ") and not msg.startswith("TEST PASSED") and not msg.startswith("TEST FAILED") and not msg.startswith("TEST SKIPPED"):
                # Close previous test if any
                if current_test is not None:
                    tests.append(current_test)
                test_name = msg.replace("TEST ", "", 1).strip()
                current_test = {
                    "name": test_name,
                    "status": "RUNNING",
                    "start_idx": entry["idx"],
                    "end_idx": entry["idx"],
                    "elapsed": "",
                    "artifacts": [],  # {kind, path, url}
                }
            if current_test is not None:
                current_test["end_idx"] = entry["idx"]

                # Status line (Robot-style)
                if msg.startswith("Status:"):
                    # e.g. Status: PASS
                    st = msg.split(":", 1)[1].strip().split()[0].upper()
                    if st in ("PASS", "FAIL", "SKIP"):
                        current_test["status"] = st

                # Elapsed line
                if "Elapsed:" in msg:
                    # e.g. Start / End / Elapsed: ... / 00:00:32.688
                    parts = msg.split("Elapsed:", 1)
                    if len(parts) == 2:
                        current_test["elapsed"] = parts[1].strip()

                # Failure artifacts lines we emit in BenchSale_Conftest.py
                # Example:
                #   Screenshot: C:\...\reports\failures\test_20260101_120000.png
                if msg.strip().startswith(("Screenshot:", "HTML:", "URL file:", "URL:")):
                    k, v = msg.split(":", 1)
                    k = k.strip()
                    v = v.strip()
                    if v:
                        current_test["artifacts"].append(
                            {
                                "kind": k,
                                "path": v,
                                "url": _windows_path_to_file_url(v) if k != "URL" else v,
                            }
                        )

            entries.append(entry)

    if current_test is not None:
        tests.append(current_test)

    return entries, tests


def generate_html_log_viewer(log_file_path, output_html_path=None):
    """Generate a modern HTML log viewer."""
    if output_html_path is None:
        log_dir = os.path.dirname(log_file_path)
        log_filename = os.path.basename(log_file_path)
        output_html_path = os.path.join(log_dir, log_filename.replace('.log', '.html'))
    
    entries, tests = parse_log_file(log_file_path)

    total = len(tests) if tests else 0
    passed = len([t for t in tests if t["status"] == "PASS"])
    failed = len([t for t in tests if t["status"] == "FAIL"])
    skipped = len([t for t in tests if t["status"] == "SKIP"])

    payload = {
        "meta": {
            "file": os.path.basename(log_file_path),
            "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "entries": len(entries),
        },
        "summary": {"total": total, "passed": passed, "failed": failed, "skipped": skipped},
        "tests": tests,
        "entries": entries,  # raw lines for rendering
    }

    # Safe embed: avoid accidentally breaking </script> in the HTML report if logs contain HTML-like text.
    payload_json = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")

    log_basename = escape(os.path.basename(log_file_path))
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html_template = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>BenchSale Report - __LOG_BASENAME__</title>
  <style>
    :root {{
      --bg: #0b1020;
      --panel: rgba(255,255,255,0.06);
      --panel2: rgba(255,255,255,0.08);
      --text: rgba(255,255,255,0.92);
      --muted: rgba(255,255,255,0.65);
      --border: rgba(255,255,255,0.12);
      --good: #2ee59d;
      --bad: #ff4d6d;
      --warn: #ffcc00;
      --info: #66a3ff;
      --chip: rgba(255,255,255,0.10);
      --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      --sans: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji","Segoe UI Emoji";
    }}
    @media (prefers-color-scheme: light) {{
      :root {{
        --bg: #f6f7fb;
        --panel: #ffffff;
        --panel2: #f4f5f9;
        --text: #141722;
        --muted: #4b5563;
        --border: rgba(0,0,0,0.10);
        --chip: rgba(0,0,0,0.06);
      }}
    }}
    * {{ box-sizing: border-box; }}
    html, body {{ height: 100%; }}
    body {{
      margin: 0;
      font-family: var(--sans);
      background:
        radial-gradient(1200px 800px at 10% 10%, rgba(102,163,255,0.25), transparent 60%),
        radial-gradient(1200px 800px at 90% 10%, rgba(46,229,157,0.18), transparent 60%),
        radial-gradient(1200px 800px at 50% 100%, rgba(255,77,109,0.14), transparent 60%),
        var(--bg);
      color: var(--text);
    }}
    .app {{
      display: grid;
      grid-template-columns: 360px 1fr;
      height: 100vh;
      gap: 14px;
      padding: 14px;
    }}
    .sidebar, .main {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 14px;
      overflow: hidden;
      backdrop-filter: blur(10px);
    }}
    .topbar {{
      padding: 14px 16px;
      border-bottom: 1px solid var(--border);
      display: flex;
      gap: 12px;
      align-items: center;
      justify-content: space-between;
    }}
    .title {{
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}
    .title h1 {{
      font-size: 16px;
      margin: 0;
      letter-spacing: 0.2px;
    }}
    .subtitle {{
      font-size: 12px;
      color: var(--muted);
      font-family: var(--mono);
    }}
    .chips {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }}
    .chip {{
      padding: 6px 10px;
      border-radius: 999px;
      background: var(--chip);
      border: 1px solid var(--border);
      font-size: 12px;
      color: var(--muted);
      display: inline-flex;
      gap: 8px;
      align-items: center;
      white-space: nowrap;
    }}
    .dot {{
      width: 8px; height: 8px; border-radius: 50%;
      background: var(--muted);
      display: inline-block;
    }}
    .dot.good {{ background: var(--good); }}
    .dot.bad {{ background: var(--bad); }}
    .dot.warn {{ background: var(--warn); }}
    .dot.info {{ background: var(--info); }}

    .filters {{
      padding: 12px 16px;
      border-bottom: 1px solid var(--border);
      display: grid;
      gap: 10px;
    }}
    .row {{
      display: grid;
      grid-template-columns: 1fr 140px;
      gap: 10px;
    }}
    input, select {{
      width: 100%;
      padding: 10px 12px;
      border-radius: 10px;
      border: 1px solid var(--border);
      background: var(--panel2);
      color: var(--text);
      outline: none;
      font-size: 13px;
    }}
    .list {{
      height: calc(100vh - 160px);
      overflow: auto;
      padding: 10px 10px 14px 10px;
    }}
    .test {{
      border: 1px solid var(--border);
      background: rgba(0,0,0,0.06);
      border-radius: 12px;
      padding: 10px 10px;
      margin: 10px 6px;
      cursor: pointer;
      transition: transform .12s ease, background .12s ease, border-color .12s ease;
    }}
    @media (prefers-color-scheme: light) {{
      .test {{ background: rgba(0,0,0,0.02); }}
    }}
    .test:hover {{ transform: translateY(-1px); border-color: rgba(102,163,255,0.35); }}
    .test.active {{ border-color: rgba(102,163,255,0.65); background: rgba(102,163,255,0.10); }}
    .test-head {{ display:flex; align-items:center; justify-content:space-between; gap: 10px; }}
    .test-name {{ font-size: 13px; font-weight: 600; color: var(--text); line-height: 1.25; }}
    .badge {{
      font-family: var(--mono);
      font-size: 11px;
      padding: 4px 8px;
      border-radius: 999px;
      border: 1px solid var(--border);
      background: rgba(255,255,255,0.06);
      color: var(--muted);
      white-space: nowrap;
    }}
    .badge.pass {{ color: var(--good); border-color: rgba(46,229,157,0.35); }}
    .badge.fail {{ color: var(--bad); border-color: rgba(255,77,109,0.35); }}
    .badge.skip {{ color: var(--warn); border-color: rgba(255,204,0,0.35); }}
    .test-meta {{ margin-top: 6px; display:flex; gap: 10px; color: var(--muted); font-size: 12px; font-family: var(--mono); }}

    .main-top {{
      padding: 14px 16px;
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
    }}
    .main-title {{ display:flex; flex-direction:column; gap: 6px; }}
    .main-title h2 {{ margin: 0; font-size: 16px; }}
    .main-title .meta {{ font-family: var(--mono); font-size: 12px; color: var(--muted); }}
    .actions {{ display:flex; gap: 8px; align-items:center; }}
    .btn {{
      padding: 9px 12px;
      border-radius: 10px;
      border: 1px solid var(--border);
      background: var(--panel2);
      color: var(--text);
      cursor: pointer;
      font-size: 13px;
      transition: background .12s ease, transform .12s ease;
    }}
    .btn:hover {{ background: rgba(102,163,255,0.14); transform: translateY(-1px); }}
    .content {{
      height: calc(100vh - 72px);
      overflow: auto;
      padding: 14px 16px 18px 16px;
    }}
    .card {{
      background: var(--panel2);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 14px;
      margin-bottom: 14px;
    }}
    .card h3 {{ margin: 0 0 10px 0; font-size: 13px; color: var(--muted); font-weight: 600; letter-spacing: 0.2px; }}
    .artifacts a {{
      color: var(--info);
      text-decoration: none;
      font-family: var(--mono);
      font-size: 12px;
      word-break: break-all;
    }}
    .artifacts a:hover {{ text-decoration: underline; }}
    pre {{
      margin: 0;
      padding: 12px;
      border-radius: 12px;
      background: rgba(0,0,0,0.20);
      border: 1px solid var(--border);
      overflow: auto;
      font-family: var(--mono);
      font-size: 12px;
      line-height: 1.45;
      white-space: pre-wrap;
      word-break: break-word;
    }}
    @media (prefers-color-scheme: light) {{
      pre {{ background: rgba(0,0,0,0.04); }}
    }}
    .line {{ display:flex; gap: 10px; }}
    .ln {{ width: 64px; color: var(--muted); text-align:right; user-select:none; }}
    .kw {{ color: #b8ffdd; }}
    @media (prefers-color-scheme: light) {{
      .kw {{ color: #0d6b4b; }}
    }}
    .err {{ color: var(--bad); font-weight: 600; }}
    .warn {{ color: var(--warn); }}
    .hint {{ color: var(--info); }}
  </style>
</head>
<body>
  <div class="app">
    <aside class="sidebar">
      <div class="topbar">
        <div class="title">
          <h1>BenchSale Test Report</h1>
          <div class="subtitle">__LOG_BASENAME__ • __GENERATED_AT__</div>
        </div>
      </div>
      <div class="filters">
        <div class="chips" id="summaryChips"></div>
        <div class="row">
          <input id="q" type="text" placeholder="Search tests..." />
          <select id="status">
            <option value="ALL">All</option>
            <option value="PASS">PASS</option>
            <option value="FAIL">FAIL</option>
            <option value="SKIP">SKIP</option>
          </select>
        </div>
      </div>
      <div class="list" id="testList"></div>
    </aside>

    <main class="main">
      <div class="main-top">
        <div class="main-title">
          <h2 id="activeTitle">All Logs</h2>
          <div class="meta" id="activeMeta"></div>
        </div>
        <div class="actions">
          <button class="btn" id="btnAll">All Logs</button>
          <button class="btn" id="btnCopy">Copy Visible</button>
        </div>
      </div>
      <div class="content" id="mainContent"></div>
    </main>
  </div>

  <script>
    const DATA = __PAYLOAD_JSON__;

    const elList = document.getElementById('testList');
    const elMain = document.getElementById('mainContent');
    const elTitle = document.getElementById('activeTitle');
    const elMeta = document.getElementById('activeMeta');
    const elQ = document.getElementById('q');
    const elStatus = document.getElementById('status');

    function badgeClass(status) {{
      if (status === 'PASS') return 'badge pass';
      if (status === 'FAIL') return 'badge fail';
      if (status === 'SKIP') return 'badge skip';
      return 'badge';
    }}

    function renderSummary() {{
      const s = DATA.summary || {{}};
      const chips = [
        {{label: `Total: ${s.total ?? 0}`, dot: 'info'}},
        {{label: `Passed: ${s.passed ?? 0}`, dot: 'good'}},
        {{label: `Failed: ${s.failed ?? 0}`, dot: 'bad'}},
        {{label: `Skipped: ${s.skipped ?? 0}`, dot: 'warn'}},
      ];
      const el = document.getElementById('summaryChips');
      el.innerHTML = chips.map(c => `<span class="chip"><span class="dot ${c.dot}"></span>${c.label}</span>`).join('');
    }}

    function getVisibleTests() {{
      const q = (elQ.value || '').trim().toLowerCase();
      const st = elStatus.value || 'ALL';
      const out = [];
      (DATA.tests || []).forEach((t, idx) => {{
        const nameOk = !q || (t.name || '').toLowerCase().includes(q);
        const stOk = st === 'ALL' || (t.status || 'RUNNING') === st;
        if (nameOk && stOk) out.push({{ t, idx }});
      }});
      return out;
    }}

    function setActive(id) {{
      document.querySelectorAll('.test').forEach(x => x.classList.remove('active'));
      const el = document.getElementById(id);
      if (el) el.classList.add('active');
    }}

    function renderList() {{
      const visible = getVisibleTests();
      elList.innerHTML = '';

      if (!visible.length) {{
        const empty = document.createElement('div');
        empty.style.padding = '16px';
        empty.style.color = 'var(--muted)';
        empty.textContent = 'No tests match your filter.';
        elList.appendChild(empty);
        return;
      }}

      visible.forEach((item, i) => {{
        const t = item.t;
        const idx = item.idx;
        const id = `t_${idx}_${(t.name||'').replace(/[^a-zA-Z0-9_-]+/g,'_')}`;
        const st = t.status || 'RUNNING';
        const elapsed = t.elapsed ? `• ${t.elapsed}` : '';

        const wrap = document.createElement('div');
        wrap.className = 'test';
        wrap.id = id;

        wrap.addEventListener('click', () => {{
          window.__openTestByIndex(idx);
          setActive(id);
        }});

        const head = document.createElement('div');
        head.className = 'test-head';

        const name = document.createElement('div');
        name.className = 'test-name';
        name.textContent = t.name || '(unnamed)';

        const badge = document.createElement('div');
        badge.className = badgeClass(st);
        badge.textContent = st;

        head.appendChild(name);
        head.appendChild(badge);

        const meta = document.createElement('div');
        meta.className = 'test-meta';
        const a = document.createElement('span');
        a.textContent = `${t.start_idx}..${t.end_idx}`;
        const b = document.createElement('span');
        b.textContent = elapsed;
        meta.appendChild(a);
        meta.appendChild(b);

        wrap.appendChild(head);
        wrap.appendChild(meta);
        elList.appendChild(wrap);
      }});
    }}

    function escapeHtml(s) {{
      return (s || '').replace(/[&<>"']/g, (c) => ({{
        '&':'&amp;',
        '<':'&lt;',
        '>':'&gt;',
        '\"':'&quot;',
        \"'\":'&#39;'
      }}[c]));
    }}

    function formatLine(entry) {{
      const msg = entry.message || '';
      const upper = msg.toUpperCase();
      let cls = '';
      if (upper.includes('KEYWORD')) cls = 'kw';
      if (upper.includes('ERROR') || upper.includes('EXCEPTION') || upper.includes('TRACEBACK') || upper.includes('FAILED')) cls = 'err';
      if (upper.includes('WARNING')) cls = 'warn';
      if (upper.includes('LOCATOR/XPATH HINT') || upper.includes('LOCATOR')) cls = 'hint';

      const left = `<span class="ln">${entry.line_no}</span>`;
      const right = `<span class="${cls}">${escapeHtml(msg)}</span>`;
      return `<div class="line">${left}${right}</div>`;
    }}

    function renderAll() {{
      elTitle.textContent = 'All Logs';
      elMeta.textContent = `${DATA.meta.file} • entries: ${DATA.meta.entries}`;
      const lines = (DATA.entries || []).map(formatLine).join('');
      elMain.innerHTML = `
        <div class="card">
          <h3>Log output</h3>
          <pre>${lines}</pre>
        </div>
      `;
    }}

    window.__openTestByIndex = function(testIndex) {{
      const t = (DATA.tests || [])[testIndex] || {{}};
      const name = t.name || 'Test';
      const status = t.status || '';
      const elapsed = t.elapsed || '';
      const startIdx = t.start_idx ?? 0;
      const endIdx = t.end_idx ?? 0;
      const artifacts = t.artifacts || [];

      elTitle.textContent = name;
      elMeta.textContent = `${status}${elapsed ? ' • ' + elapsed : ''} • lines ${startIdx}..${endIdx}`;
      const slice = (DATA.entries || []).slice(startIdx, endIdx + 1);
      const lines = slice.map(formatLine).join('');

      const artHtml = (artifacts || []).length ? `
        <div class="card artifacts">
          <h3>Failure artifacts</h3>
          ${(artifacts || []).map(a => `
            <div style="margin:6px 0;">
              <span class="chip"><span class="dot info"></span>${escapeHtml(a.kind || 'Artifact')}</span>
              <a href="${escapeHtml(a.url || '')}" target="_blank" rel="noopener">${escapeHtml(a.path || '')}</a>
            </div>
          `).join('')}
        </div>
      ` : '';

      elMain.innerHTML = `
        ${artHtml}
        <div class="card">
          <h3>Test log</h3>
          <pre>${lines}</pre>
        </div>
      `;
    }

    document.getElementById('btnAll').addEventListener('click', () => {{
      setActive('');
      renderAll();
    }});

    document.getElementById('btnCopy').addEventListener('click', async () => {{
      const text = document.getElementById('mainContent').innerText || '';
      try {{
        await navigator.clipboard.writeText(text);
      }} catch (e) {{
        alert('Copy failed (browser blocked clipboard).');
      }}
    }});

    elQ.addEventListener('input', () => renderList());
    elStatus.addEventListener('change', () => renderList());

    renderSummary();
    renderList();
    renderAll();
  </script>
</body>
</html>
"""

    # Normalize leftover doubled braces from the old f-string version of this template.
    # Without this, JS ends up like `function renderList() {{` which breaks rendering entirely.
    html_template = html_template.replace("{{", "{").replace("}}", "}")

    html_content = (
        html_template
        .replace("__LOG_BASENAME__", log_basename)
        .replace("__GENERATED_AT__", escape(generated_at))
        .replace("__PAYLOAD_JSON__", payload_json)
    )
    
    # Write HTML file
    with open(output_html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return output_html_path


def generate_all_log_viewers():
    """Generate HTML viewers for all log files"""
    log_dir = Path(__file__).parent.parent / 'logs'
    html_files = []
    
    if log_dir.exists():
        # Prioritize main log file (benchsale_test.log)
        main_log = log_dir / 'benchsale_test.log'
        if main_log.exists():
            html_file = generate_html_log_viewer(str(main_log))
            html_files.append(html_file)
            print(f"Generated HTML viewer: {html_file}")
        
        # Then process other log files
        for log_file in sorted(log_dir.glob('*.log'), key=lambda x: x.stat().st_mtime, reverse=True):
            if log_file.name != 'benchsale_test.log':
                html_file = generate_html_log_viewer(str(log_file))
                html_files.append(html_file)
                print(f"Generated HTML viewer: {html_file}")
    
    return html_files


if __name__ == '__main__':
    # Generate HTML viewers for all logs
    generate_all_log_viewers()

