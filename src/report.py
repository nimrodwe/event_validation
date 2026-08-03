"""Report: write findings files + serve event-validation dashboard."""

import csv
import json
import os
import threading
import time
import webbrowser

from flask import Flask, jsonify, render_template_string, request
from werkzeug.serving import make_server

from src.config import DATASET, OUT
from src.run_log import clear_runs, load_runs
from src.validate import Validator

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Event Validation</title>
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
    .status { display: flex; gap: 1rem; flex-wrap: wrap; align-items: center; }
    .stat {
      font-size: .85rem; padding: .35rem .75rem; border-radius: 6px;
      background: #0f172a; border: 1px solid #334155; color: #cbd5e1;
    }
    .stat strong { color: #38bdf8; }
    main { padding: 1.5rem 2rem; display: grid; gap: 1.25rem; }
    .panel { background: #1e293b; border-radius: 10px; border: 1px solid #334155; overflow: hidden; }
    .panel-pad { padding: 1rem; }
    .section-head {
      display: flex; align-items: center; justify-content: space-between; gap: 1rem;
      margin-bottom: .75rem; flex-wrap: wrap;
    }
    .filters { display: flex; gap: .5rem; flex-wrap: wrap; }
    .filters input, .filters select {
      background: #0f172a; color: #e2e8f0; border: 1px solid #475569; border-radius: 6px;
      padding: .35rem .55rem; font-size: .85rem;
    }
    .item {
      border: 1px solid #334155; border-radius: 8px; margin-bottom: .5rem; overflow: hidden;
      background: #0f172a;
    }
    .item-head {
      display: flex; gap: .75rem; flex-wrap: wrap; align-items: center;
      padding: .65rem .9rem; cursor: pointer; background: #1e293b;
      font-family: ui-monospace, monospace; font-size: .85rem;
    }
    .item-head:hover { background: #334155; }
    .item-body { display: none; padding: .75rem 1rem 1rem; border-top: 1px solid #334155; }
    .item.open .item-body { display: block; }
    .item-body pre {
      margin: 0; white-space: pre-wrap; word-break: break-word;
      font-size: .8rem; color: #cbd5e1; background: #020617;
      border: 1px solid #334155; border-radius: 6px; padding: .75rem;
    }
    .badge {
      font-size: .72rem; padding: .12rem .45rem; border-radius: 999px;
      border: 1px solid #475569; color: #cbd5e1;
    }
    .badge.cat { color: #fbbf24; border-color: #854d0e; }
    .badge.rule { color: #7dd3fc; border-color: #075985; }
    .badge.passed { color: #4ade80; border-color: #166534; }
    .badge.failed { color: #f87171; border-color: #7f1d1d; }
    .badge.skipped { color: #fbbf24; border-color: #854d0e; }
    .badge.success { color: #4ade80; border-color: #166534; }
    .badge.failure { color: #f87171; border-color: #7f1d1d; }
    .badge.cancelled { color: #94a3b8; border-color: #475569; }
    .badge.in_progress { color: #38bdf8; border-color: #075985; }
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
    .test-right {
      margin-left: auto; display: flex; align-items: center; gap: .5rem;
    }
    .test-uuid { color: #94a3b8; font-size: .85rem; }
    .test-neg {
      color: #fbbf24; font-weight: 700; font-size: .85rem;
      border: 1px solid rgba(251, 191, 36, .45);
      border-radius: 4px; padding: .05rem .35rem;
    }
    .fail-summary {
      margin: .35rem 0 .5rem; color: #fca5a5; font-family: ui-monospace, monospace;
      font-size: .82rem; white-space: pre-wrap; word-break: break-word;
      background: rgba(127, 29, 29, 0.35); border-left: 3px solid #f87171;
      padding: .5rem .65rem; border-radius: 4px;
    }
    .fail-summary .fail-title { font-weight: 600; margin-bottom: .4rem; }
    .steps {
      display: none;
      font-family: ui-monospace, monospace; font-size: .78rem; line-height: 1.45;
      background: #020617; border: 1px solid #334155; border-radius: 6px; padding: .75rem;
      white-space: pre-wrap; color: #94a3b8;
    }
    .test-block.open .steps { display: block; }
    /* Failed tests: keep error + data visible (error is above .steps). */
    .test-block.failed .steps { display: block; }
    .steps .INFO { color: #7dd3fc; }
    .steps .WARNING { color: #fbbf24; }
    .steps .step-line.ERROR {
      color: #fca5a5; background: rgba(127, 29, 29, 0.35);
      border-left: 3px solid #f87171; padding: .35rem .5rem; margin: 0 0 .6rem; border-radius: 4px;
    }
    .empty { color: #64748b; font-size: .9rem; }
    button.btn {
      background: #0f172a; color: #e2e8f0; border: 1px solid #475569; border-radius: 6px;
      padding: .4rem .75rem; cursor: pointer; font-size: .85rem;
    }
    button.btn:hover { background: #334155; }
    button.btn:disabled { opacity: .5; cursor: wait; }
    button.btn-danger { border-color: #7f1d1d; color: #fca5a5; }
    button.btn-danger:hover { background: #7f1d1d; color: #fff; }
    button.btn-primary { border-color: #075985; color: #7dd3fc; }
    button.btn-primary:hover { background: #075985; color: #fff; }
    a.btn-link {
      display: inline-block; text-decoration: none; margin-right: .5rem; margin-top: .5rem;
      background: #0f172a; color: #e2e8f0; border: 1px solid #475569; border-radius: 6px;
      padding: .4rem .75rem; font-size: .85rem;
    }
    a.btn-link:hover { background: #334155; }
    .actions { display: flex; gap: .5rem; flex-wrap: wrap; }
    .msg { color: #94a3b8; font-size: .8rem; min-height: 1.2em; }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Event Validation</h1>
      <div class="sub">Local pytest runs</div>
    </div>
    <div class="status">
      <div class="actions">
        <button class="btn btn-danger" id="btn-shutdown" type="button">Shut down</button>
      </div>
    </div>
  </header>
  <main>
    <section class="panel panel-pad">
      <div class="section-head">
        <div>
          <h2>Pytest runs (this machine only)</h2>
          <div class="sub">Local pytest history on this computer — not shared with your other machines</div>
        </div>
        <button class="btn btn-danger" id="btn-clear-runs" type="button">Clear all runs</button>
      </div>
      <div id="runs" class="empty">Loading…</div>
    </section>
  </main>
  <script>
    let testRuns = {{ test_runs_json | safe }};
    const openRuns = new Set();
    const openTests = new Set();

    function esc(s) {
      return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    }

    function outcomeBadge(outcome) {
      const cls = outcome === 'passed' ? 'passed' : outcome === 'failed' ? 'failed' : 'skipped';
      return `<span class="badge ${cls}">${esc(outcome || '')}</span>`;
    }

    function niceDate(iso) {
      if (!iso) return 'Unknown date';
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) return esc(iso);
      return d.toLocaleString(undefined, {
        weekday: 'short', year: 'numeric', month: 'short', day: 'numeric',
        hour: 'numeric', minute: '2-digit'
      });
    }

    function testName(nodeid) {
      return (nodeid || '').split('::').pop() || nodeid || '';
    }

    function isNegativeTest(test) {
      if (test && test.negative === true) return true;
      const name = testName(test && test.nodeid);
      return name.startsWith('test_negatives') || name.startsWith('test_type_bad');
    }

    function testUuid(test) {
      // First UUID that was sent for this test (empty string → "(empty)").
      if (test && test.uuid != null) {
        return test.uuid === '' ? '(empty)' : String(test.uuid);
      }
      for (const s of (test && test.steps) || []) {
        const msg = (s.message || '').trim();
        if (msg.startsWith('UUID ')) {
          const value = msg.slice(5);
          return value === '' ? '(empty)' : value;
        }
        if (!msg.startsWith('{')) continue;
        try {
          const data = JSON.parse(msg);
          if (data.properties && data.properties.UUID != null) {
            return data.properties.UUID === '' ? '(empty)' : String(data.properties.UUID);
          }
          if (data.UUID != null) return data.UUID === '' ? '(empty)' : String(data.UUID);
        } catch (err) {}
      }
      return '';
    }

    function formatStepMessage(message) {
      const msg = (message || '').trim();
      if (!msg.startsWith('{') && !msg.startsWith('[')) return esc(message || '');
      try { return esc(JSON.stringify(JSON.parse(msg), null, 2)); }
      catch (err) { return esc(message || ''); }
    }

    function runKey(run) { return run.run_id || run.started || ''; }

    function renderRuns() {
      const root = document.getElementById('runs');
      if (!testRuns.length) {
        root.className = 'empty';
        root.textContent = 'No pytest runs yet. Run: python -m pytest -v';
        return;
      }
      root.className = '';
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
          if (openRuns.has(key)) openRuns.delete(key); else openRuns.add(key);
          box.classList.toggle('open');
        };
        const body = document.createElement('div');
        body.className = 'run-body';
        (run.tests || []).forEach(t => {
          const testKey = key + '::' + (t.nodeid || '');
          const block = document.createElement('div');
          block.className = 'test-block' + (openTests.has(testKey) ? ' open' : '');
          const uuid = testUuid(t);
          const uuidHtml = uuid ? `<span class="test-uuid">${esc(uuid)}</span>` : '';
          const stepList = t.steps || [];
          const errSteps = stepList.filter(s => s.level === 'ERROR');
          const dataSteps = stepList.filter(s => s.level !== 'ERROR');
          const errStep = errSteps[0];
          // Failed: API error + key/before/after ABOVE data. Data steps never include ERROR.
          let errPreview = '';
          if (t.outcome === 'failed' && errStep && errStep.message) {
            const raw = String(errStep.message).trim();
            const nl = raw.indexOf('\\n');
            const head = nl === -1 ? raw : raw.slice(0, nl).trim();
            const body = nl === -1 ? '' : raw.slice(nl + 1).trim();
            errPreview =
              `<div class="fail-summary">` +
              `<div class="fail-title">${esc(head)}</div>` +
              (body ? `<div>${esc(body)}</div>` : '') +
              `</div>`;
          }
          const lines = (t.outcome === 'failed' ? dataSteps : stepList).map(s =>
            `<div class="step-line ${esc(s.level)}"><span class="${esc(s.level)}">[${esc(s.level)}]</span> ${formatStepMessage(s.message)}</div>`
          ).join('') || (t.outcome === 'failed' ? '' : '<div class="empty">No step logs</div>');
          if (t.outcome === 'failed') {
            block.classList.add('failed');
            block.classList.add('open');
            openTests.add(testKey);
          }
          const title = document.createElement('div');
          title.className = 'test-title';
          const negHtml = isNegativeTest(t) ? '<span class="test-neg">(N)</span>' : '';
          title.innerHTML =
            `${outcomeBadge(t.outcome)} <span class="test-name">${esc(testName(t.nodeid))}</span>` +
            `<span class="test-right">${negHtml}${uuidHtml}</span>`;
          title.onclick = () => {
            if (openTests.has(testKey)) openTests.delete(testKey); else openTests.add(testKey);
            block.classList.toggle('open');
          };
          const steps = document.createElement('div');
          steps.className = 'steps';
          steps.innerHTML = lines;
          block.appendChild(title);
          if (errPreview) {
            const preview = document.createElement('div');
            preview.innerHTML = errPreview;
            block.appendChild(preview.firstChild);
          }
          if (lines) block.appendChild(steps);
          body.appendChild(block);
        });
        box.appendChild(head);
        box.appendChild(body);
        root.appendChild(box);
      });
    }

    function renderAll() {
      renderRuns();
    }

    async function loadRuns() {
      const r = await fetch('/api/test-runs');
      testRuns = await r.json();
    }

    document.getElementById('btn-clear-runs').addEventListener('click', async () => {
      await fetch('/api/test-runs/clear', { method: 'POST' });
      testRuns = [];
      renderRuns();
    });
    document.getElementById('btn-shutdown').addEventListener('click', async () => {
      await fetch('/api/shutdown', { method: 'POST' });
      document.body.innerHTML = '<main class="panel-pad"><h1>Server shut down</h1><p class="sub">You can close this tab.</p></main>';
    });

    async function presenceLoop() {
      try { await fetch('/api/presence', { method: 'POST' }); } catch (e) {}
      setTimeout(presenceLoop, 3000);
    }
    presenceLoop();
    // Clear presence as soon as the tab closes so pytest can reopen the browser.
    window.addEventListener('pagehide', () => {
      try { navigator.sendBeacon('/api/presence/leave'); } catch (e) {}
    });
    renderAll();
    setInterval(async () => {
      try {
        await loadRuns();
        renderRuns();
      } catch (e) {}
    }, 2000);
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
        self.app = Flask(__name__)
        self._server = None
        self._closed = threading.Event()
        self._shutdown_hooks = []
        self._last_presence = 0.0
        self.app.add_url_rule("/", "home", self.home)
        self.app.add_url_rule("/api/received", "received", self.api_received)
        self.app.add_url_rule("/api/findings", "findings", self.api_findings)
        self.app.add_url_rule("/api/validate", "validate", self.api_validate, methods=["POST"])
        self.app.add_url_rule("/api/test-runs", "test_runs", self.api_test_runs)
        self.app.add_url_rule("/api/test-runs/clear", "clear_runs", self.api_clear_test_runs, methods=["POST"])
        self.app.add_url_rule("/api/presence", "presence_ping", self.api_presence_ping, methods=["POST"])
        self.app.add_url_rule("/api/presence", "presence_status", self.api_presence_status, methods=["GET"])
        self.app.add_url_rule(
            "/api/presence/leave",
            "presence_leave",
            self.api_presence_leave,
            methods=["POST"],
        )
        self.app.add_url_rule("/api/shutdown", "shutdown", self.api_shutdown, methods=["POST"])
        self.app.add_url_rule("/api/health", "health", self.api_health)

    def api_health(self):
        return jsonify({"ok": True, "features": ["presence_leave"]})

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

    def _read_received(self, case_id=None):
        path = self.out / "received" / "events.jsonl"
        items = []
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip() == "":
                    continue
                items.append(json.loads(line))
        if case_id:
            items = [item for item in items if str(item.get("case_id", "")) == case_id]
        items.reverse()
        return items

    def _read_findings_payload(self):
        findings_dir = self.out / "findings"
        findings = []
        summary = {}
        findings_path = findings_dir / "findings.json"
        summary_path = findings_dir / "summary.json"
        if findings_path.exists():
            findings = json.loads(findings_path.read_text(encoding="utf-8"))
        if summary_path.exists():
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        elif findings:
            summary = {"total": len(findings)}
        return {"findings": findings, "summary": summary}

    def home(self):
        return render_template_string(
            DASHBOARD_HTML,
            test_runs_json=json.dumps(load_runs()),
        )

    def api_received(self):
        case_id = request.args.get("case_id")
        events = self._read_received(case_id=case_id)
        return jsonify({"count": len(events), "events": events})

    def api_findings(self):
        return jsonify(self._read_findings_payload())

    def api_validate(self):
        validator = Validator()
        findings = []
        if DATASET.exists():
            findings.extend(validator.validate_dataset())
        findings.extend(validator.validate_received(self.out / "received" / "events.jsonl"))
        self.write(findings)
        return jsonify(self._read_findings_payload())

    def api_test_runs(self):
        return jsonify(load_runs())

    def api_clear_test_runs(self):
        clear_runs()
        return jsonify({"ok": True})


    def api_presence_ping(self):
        self._last_presence = time.time()
        return jsonify({"ok": True})

    def api_presence_leave(self):
        """Tab closed — mark inactive immediately so pytest can reopen the browser."""
        self._last_presence = 0.0
        return jsonify({"ok": True, "active": False})

    def api_presence_status(self):
        if not self._last_presence:
            age = 1e9
        else:
            age = time.time() - self._last_presence
        # Slightly above the 3s ping interval; leave endpoint clears sooner on close.
        return jsonify({"age_seconds": age, "active": age < 5})

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
        url = "http://127.0.0.1:" + str(port)
        # Docker sets BIND_HOST=0.0.0.0 so the Mac can reach published ports.
        bind_host = os.environ.get("BIND_HOST", "127.0.0.1")

        self._closed.clear()
        self._server = make_server(bind_host, port, self.app)

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
