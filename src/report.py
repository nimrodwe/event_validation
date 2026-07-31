"""Report: write findings files + serve pytest-runs dashboard."""

import csv
import json
import threading
import time
import webbrowser

from flask import Flask, jsonify, render_template_string
from werkzeug.serving import make_server

from src.config import OUT
from src.run_log import clear_test_runs, load_test_runs

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Pytest Dashboard</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: system-ui, sans-serif; margin: 0; background: #0f172a; color: #e2e8f0; }
    header {
      padding: 1.5rem 2rem; background: #1e293b; border-bottom: 1px solid #334155;
      display: flex; align-items: center; justify-content: space-between; gap: 1rem; flex-wrap: wrap;
    }
    h1 { margin: 0 0 .25rem; font-size: 1.5rem; }
    h2 { margin: 0; font-size: 1.1rem; color: #cbd5e1; }
    .sub { color: #94a3b8; font-size: .9rem; }
    main { padding: 1.5rem 2rem; }
    .panel { background: #1e293b; border-radius: 10px; border: 1px solid #334155; overflow: hidden; }
    .panel-pad { padding: 1rem; }
    .run {
      border: 1px solid #334155; border-radius: 8px; margin-bottom: .75rem; overflow: hidden;
      background: #0f172a;
    }
    .run-head {
      display: flex; gap: 1rem; flex-wrap: wrap; align-items: center;
      padding: .75rem 1rem; cursor: pointer; background: #1e293b;
    }
    .run-head:hover { background: #334155; }
    .run-body { display: none; padding: .75rem 1rem 1rem; border-top: 1px solid #334155; }
    .run.open .run-body { display: block; }
    .badge {
      font-size: .75rem; padding: .15rem .5rem; border-radius: 999px;
      border: 1px solid #475569; color: #cbd5e1;
    }
    .badge.passed { color: #4ade80; border-color: #166534; }
    .badge.failed { color: #f87171; border-color: #7f1d1d; }
    .badge.skipped { color: #fbbf24; border-color: #854d0e; }
    .test-block { margin: .75rem 0; }
    .test-title {
      display: flex; align-items: center; flex-wrap: wrap; gap: .35rem 1.25rem;
      font-family: ui-monospace, monospace; font-size: .9rem; margin-bottom: .35rem;
      cursor: pointer; user-select: none;
    }
    .test-title:hover { color: #f8fafc; }
    .test-title::before { content: "▸ "; color: #64748b; font-size: .75rem; }
    .test-block.open .test-title::before { content: "▾ "; color: #38bdf8; }
    .test-name { color: #e2e8f0; }
    .test-uuid { color: #94a3b8; font-size: .85rem; }
    .steps {
      display: none;
      font-family: ui-monospace, monospace; font-size: .78rem; line-height: 1.45;
      background: #020617; border: 1px solid #334155; border-radius: 6px; padding: .75rem;
      white-space: pre-wrap; color: #94a3b8;
    }
    .test-block.open .steps { display: block; }
    .steps .INFO { color: #7dd3fc; }
    .steps .WARNING { color: #fbbf24; }
    .steps .step-line.ERROR {
      color: #fca5a5;
      background: rgba(127, 29, 29, 0.35);
      border-left: 3px solid #f87171;
      padding: .35rem .5rem;
      margin: .25rem 0;
      border-radius: 4px;
    }
    .steps .step-line.ERROR .ERROR { color: #fecaca; }
    .empty { color: #64748b; font-size: .9rem; }
    .section-head { display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: .75rem; }
    button.btn {
      background: #0f172a; color: #e2e8f0; border: 1px solid #475569; border-radius: 6px;
      padding: .4rem .75rem; cursor: pointer; font-size: .85rem;
    }
    button.btn:hover { background: #334155; }
    button.btn-danger { border-color: #7f1d1d; color: #fca5a5; }
    button.btn-danger:hover { background: #7f1d1d; color: #fff; }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Pytest Dashboard</h1>
      <div class="sub">Click a run, then a test name, to see step logs</div>
    </div>
    <button class="btn btn-danger" id="shutdown" type="button">Shut down server</button>
  </header>
  <main>
    <section class="panel panel-pad">
      <div class="section-head">
        <h2>Pytest runs</h2>
        <button class="btn btn-danger" id="clear-runs" type="button">Clear all runs</button>
      </div>
      <div id="runs"></div>
    </section>
  </main>
  <script>
    let testRuns = {{ test_runs_json | safe }};

    function outcomeBadge(outcome) {
      const cls = outcome === 'passed' ? 'passed' : outcome === 'failed' ? 'failed' : 'skipped';
      return `<span class="badge ${cls}">${outcome}</span>`;
    }

    function niceDate(iso) {
      if (!iso) return 'Unknown date';
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) return iso;
      return d.toLocaleString(undefined, {
        weekday: 'short',
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit'
      });
    }

    function testName(nodeid) {
      return (nodeid || '').split('::').pop() || nodeid || '';
    }

    function testUuid(steps) {
      for (const s of steps || []) {
        const msg = (s.message || '').trim();
        if (!msg.startsWith('{')) continue;
        try {
          const data = JSON.parse(msg);
          if (data.properties && data.properties.UUID) return String(data.properties.UUID);
          if (data.UUID) return String(data.UUID);
        } catch (err) {}
      }
      return '';
    }

    function escapeHtml(text) {
      return String(text).replace(/</g, '&lt;');
    }

    function formatStepMessage(message) {
      const msg = (message || '').trim();
      if (!msg.startsWith('{') && !msg.startsWith('[')) return escapeHtml(message || '');
      try {
        return escapeHtml(JSON.stringify(JSON.parse(msg), null, 2));
      } catch (err) {
        return escapeHtml(message || '');
      }
    }

    const openRuns = new Set();
    const openTests = new Set();

    function runKey(run) {
      return run.run_id || run.started || '';
    }

    function renderRuns() {
      const root = document.getElementById('runs');
      if (!testRuns.length) {
        root.innerHTML = '<div class="empty">No pytest runs yet. Run: python -m pytest -v</div>';
        return;
      }
      root.innerHTML = '';
      testRuns.forEach((run) => {
        const key = runKey(run);
        const passed = (run.tests || []).filter(t => t.outcome === 'passed').length;
        const failed = (run.tests || []).filter(t => t.outcome === 'failed').length;
        const box = document.createElement('div');
        box.className = 'run' + (openRuns.has(key) ? ' open' : '');
        const head = document.createElement('div');
        head.className = 'run-head';
        head.innerHTML = `
          <strong>${niceDate(run.started || run.run_id)}</strong>
          <span class="badge">${(run.tests || []).length} tests</span>
          <span class="badge passed">${passed} passed</span>
          <span class="badge failed">${failed} failed</span>`;
        head.onclick = () => {
          if (openRuns.has(key)) openRuns.delete(key);
          else openRuns.add(key);
          box.classList.toggle('open');
        };

        const body = document.createElement('div');
        body.className = 'run-body';
        (run.tests || []).forEach(t => {
          const testKey = key + '::' + (t.nodeid || '');
          const block = document.createElement('div');
          block.className = 'test-block' + (openTests.has(testKey) ? ' open' : '');
          const name = escapeHtml(testName(t.nodeid));
          const uuid = testUuid(t.steps);
          const uuidHtml = uuid ? `<span class="test-uuid">${escapeHtml(uuid)}</span>` : '';
          const lines = (t.steps || []).map(s =>
            `<div class="step-line ${s.level}"><span class="${s.level}">[${s.level}]</span> ${formatStepMessage(s.message)}</div>`
          ).join('') || '<div class="empty">No step logs</div>';
          const title = document.createElement('div');
          title.className = 'test-title';
          title.innerHTML = `${outcomeBadge(t.outcome)} <span class="test-name">${name}</span>${uuidHtml}`;
          title.onclick = () => {
            if (openTests.has(testKey)) openTests.delete(testKey);
            else openTests.add(testKey);
            block.classList.toggle('open');
          };
          const steps = document.createElement('div');
          steps.className = 'steps';
          steps.innerHTML = lines;
          block.appendChild(title);
          block.appendChild(steps);
          body.appendChild(block);
        });

        box.appendChild(head);
        box.appendChild(body);
        root.appendChild(box);
      });
    }

    async function refreshLive() {
      try {
        await fetch('/api/presence', { method: 'POST' });
        testRuns = await fetch('/api/test-runs').then(r => r.json());
        renderRuns();
      } catch (err) {
        console.log('refresh failed', err);
      }
    }

    document.getElementById('clear-runs').onclick = async () => {
      if (!confirm('Clear all pytest runs from the dashboard?')) return;
      await fetch('/api/test-runs/clear', { method: 'POST' });
      testRuns = [];
      renderRuns();
    };

    document.getElementById('shutdown').onclick = async () => {
      if (!confirm('Shut down the dashboard and local receiver?')) return;
      try {
        await fetch('/api/shutdown', { method: 'POST' });
      } catch (err) {}
      document.body.innerHTML =
        '<main style="padding:2rem"><h1>Server shut down</h1><p class="sub">You can close this tab.</p></main>';
    };

    renderRuns();
    refreshLive();
    setInterval(refreshLive, 2000);
  </script>
</body>
</html>"""

FINDINGS_REPORT_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Findings Report</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 2rem; background: #0f172a; color: #e2e8f0; }
    h1 { margin-top: 0; }
    .sub { color: #94a3b8; margin-bottom: 1.5rem; }
    details { background: #1e293b; border: 1px solid #334155; border-radius: 8px; margin-bottom: .5rem; padding: .75rem 1rem; }
    summary { cursor: pointer; font-family: ui-monospace, monospace; }
    pre { white-space: pre-wrap; color: #cbd5e1; font-size: .85rem; }
  </style>
</head>
<body>
  <h1>Validation findings</h1>
  <div class="sub">Static report from run.py validate / all — click a row for details</div>
  <div id="list"></div>
  <script>
    const findings = {{ findings_json | safe }};
    const root = document.getElementById('list');
    if (!findings.length) {
      root.innerHTML = '<p class="sub">No findings.</p>';
    } else {
      root.innerHTML = findings.map(f => `
        <details>
          <summary>${f.locator} · ${f.rule_id} · ${f.category} · ${f.field}</summary>
          <pre>${JSON.stringify(f, null, 2).replace(/</g, '&lt;')}</pre>
        </details>`).join('');
    }
  </script>
</body>
</html>"""


class Report:
    def __init__(self, out_dir=None):
        if out_dir is None:
            out_dir = OUT
        self.out = out_dir
        self.test_runs = []
        self.app = Flask(__name__)
        self._server = None
        self._closed = threading.Event()
        self._shutdown_hooks = []
        self._last_presence = 0.0
        self.app.add_url_rule("/", "home", self.home)
        self.app.add_url_rule("/api/test-runs", "test_runs", self.api_test_runs)
        self.app.add_url_rule("/api/test-runs/clear", "clear_runs", self.api_clear_test_runs, methods=["POST"])
        self.app.add_url_rule("/api/presence", "presence_ping", self.api_presence_ping, methods=["POST"])
        self.app.add_url_rule("/api/presence", "presence_status", self.api_presence_status, methods=["GET"])
        self.app.add_url_rule("/api/shutdown", "shutdown", self.api_shutdown, methods=["POST"])

    def write(self, findings):
        """Write machine-readable findings + a static HTML drill-down report."""
        findings_dir = self.out / "findings"
        findings_dir.mkdir(parents=True, exist_ok=True)

        (findings_dir / "findings.json").write_text(json.dumps(findings, indent=2), encoding="utf-8")

        if findings:
            csv_file = open(findings_dir / "findings.csv", "w", newline="", encoding="utf-8")
            writer = csv.DictWriter(csv_file, fieldnames=list(findings[0].keys()))
            writer.writeheader()
            writer.writerows(findings)
            csv_file.close()

        by_category = {}
        dataset_rows = []
        for f in findings:
            cat = f["category"]
            if cat not in by_category:
                by_category[cat] = 0
            by_category[cat] = by_category[cat] + 1
            if f["source"] == "dataset" and f["locator"] not in dataset_rows:
                dataset_rows.append(f["locator"])
        dataset_rows.sort()

        summary = {
            "total": len(findings),
            "by_category": by_category,
            "dataset_rows": dataset_rows,
        }
        (findings_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

        report_dir = self.out / "report"
        report_dir.mkdir(parents=True, exist_ok=True)
        html = FINDINGS_REPORT_HTML.replace("{{ findings_json | safe }}", json.dumps(findings))
        (report_dir / "index.html").write_text(html, encoding="utf-8")

    def home(self):
        return render_template_string(
            DASHBOARD_HTML,
            test_runs_json=json.dumps(self.test_runs),
        )

    def api_test_runs(self):
        return jsonify(load_test_runs())

    def api_clear_test_runs(self):
        clear_test_runs()
        return jsonify({"ok": True})

    def api_presence_ping(self):
        self._last_presence = time.time()
        return jsonify({"ok": True})

    def api_presence_status(self):
        if not self._last_presence:
            age = 1e9
        else:
            age = time.time() - self._last_presence
        return jsonify({"age_seconds": age, "active": age < 8})

    def add_shutdown_hook(self, fn):
        self._shutdown_hooks.append(fn)

    def api_shutdown(self):
        self._closed.set()
        for fn in list(self._shutdown_hooks):
            try:
                fn()
            except Exception:
                pass
        if self._server is not None:
            threading.Thread(target=self._server.shutdown, daemon=True).start()
        return jsonify({"ok": True})

    def wait_until_shutdown(self):
        """Block until Shut down server is clicked (or the process is interrupted)."""
        self._closed.wait()

    def open_browser_later(self, url):
        webbrowser.open(url)

    def serve(self, port=8080, open_browser=True, blocking=True):
        self.test_runs = load_test_runs()
        url = "http://127.0.0.1:" + str(port)

        self._closed.clear()
        self._server = make_server("127.0.0.1", port, self.app)

        if open_browser:
            timer = threading.Timer(0.8, self.open_browser_later, [url])
            timer.start()

        print("Dashboard: " + url)
        print("Click 'Shut down server' on the dashboard when finished.")
        if blocking:
            try:
                self._server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                self._closed.set()
            return self

        thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        thread.start()
        return self
