"""Report: write findings files + serve event-validation dashboard."""

import csv
import json
import os
import threading
import time
import webbrowser

from flask import Flask, jsonify, render_template_string, request, send_from_directory
from werkzeug.serving import make_server

from src.ci_runs import CI_RUNS
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
    .suite-folder, .event-folder {
      margin: .65rem 0; border: 1px solid #334155; border-radius: 8px;
      background: #0f172a; overflow: hidden;
    }
    .suite-folder > .folder-head, .event-folder > .folder-head {
      display: flex; align-items: center; flex-wrap: wrap; gap: .35rem 1rem;
      padding: .55rem .85rem; cursor: pointer; user-select: none;
      font-family: ui-monospace, monospace; font-size: .9rem; background: #1e293b;
    }
    .suite-folder > .folder-head:hover, .event-folder > .folder-head:hover {
      background: #334155;
    }
    .suite-folder > .folder-head::before, .event-folder > .folder-head::before {
      content: "▸ "; color: #64748b; font-size: .75rem;
    }
    .suite-folder.open > .folder-head::before, .event-folder.open > .folder-head::before {
      content: "▾ "; color: #38bdf8;
    }
    .suite-folder > .folder-body, .event-folder > .folder-body {
      display: none; padding: .35rem .75rem .75rem; border-top: 1px solid #334155;
    }
    .suite-folder.open > .folder-body, .event-folder.open > .folder-body {
      display: block;
    }
    .event-folder { margin: .45rem 0; background: #020617; }
    .event-folder > .folder-head { background: #0f172a; font-size: .85rem; }
    .folder-label { color: #e2e8f0; font-weight: 600; }
    .folder-meta { color: #94a3b8; font-size: .8rem; margin-left: auto; }
    .test-block { margin: .45rem 0 .45rem .35rem; }
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
    .ci-meta { color: #94a3b8; font-size: .85rem; }
    .ci-note { color: #64748b; font-size: .8rem; margin-top: .75rem; }
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
      <div class="sub">Pytest runs and CI</div>
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
    <section class="panel panel-pad">
      <div class="section-head">
        <div>
          <h2>Pytest CI runs (shared)</h2>
          <div class="sub" id="ci-sub">Same public catalog on every machine — look here for workflow #38 etc.</div>
        </div>
      </div>
      <div id="ci-error" class="msg" style="color:#fca5a5"></div>
      <div id="ci-runs" class="empty">Loading…</div>
    </section>
  </main>
  <script>
    let testRuns = {{ test_runs_json | safe }};
    let ciPayload = {{ ci_runs_json | safe }};
    const openRuns = new Set();
    const openTests = new Set();
    const openFolders = new Set();
    const openCiRuns = new Set();

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

    /** Group test_negatives[new_keys-e1] / test_type_bad[e1] into folders. */
    function eventGroupInfo(test) {
      const negTitles = {
        new_keys: 'new keys',
        missing_keys: 'missing keys',
        empty_got_null: 'empty string got none or null',
        value_got_empty: 'string value got empty string',
      };
      const negOrder = ['new_keys', 'missing_keys', 'empty_got_null', 'value_got_empty'];
      if (test && test.group_suite && test.group_event) {
        return {
          suite: test.group_suite,
          suiteLabel: test.group_suite_label || test.group_suite,
          eventId: test.group_event,
          eventLabel: test.group_event_label || test.group_event,
          shortName: test.group_leaf || testName(test.nodeid),
          negOrder: negOrder.indexOf(test.group_event),
        };
      }
      const name = testName(test && test.nodeid);
      let suite = null;
      let suiteLabel = null;
      if (name.indexOf('test_negatives[') === 0) {
        suite = 'test_negatives';
        suiteLabel = 'test_negatives';
      } else if (name.indexOf('test_type_bad[') === 0) {
        suite = 'test_type_bad';
        suiteLabel = 'test_type_bad';
      } else {
        return null;
      }
      const openB = name.indexOf('[');
      const closeB = name.lastIndexOf(']');
      if (openB < 0 || closeB <= openB) return null;
      const inner = name.slice(openB + 1, closeB);

      // Negatives: new_keys-e1 → folder "new keys", leaf event-1
      if (suite === 'test_negatives') {
        for (let i = 0; i < negOrder.length; i++) {
          const kindId = negOrder[i];
          const prefix = kindId + '-e';
          if (inner.indexOf(prefix) !== 0) continue;
          const eventNum = inner.slice(prefix.length);
          if (!/^\\d+$/.test(eventNum)) continue;
          return {
            suite: suite,
            suiteLabel: suiteLabel,
            eventId: kindId,
            eventLabel: negTitles[kindId] || kindId,
            shortName: 'event-' + eventNum,
            negOrder: i,
          };
        }
        return null;
      }

      // type_bad: e1 (or legacy e1-datetime)
      if (inner.length < 2 || inner.charAt(0) !== 'e') return null;
      const dash = inner.indexOf('-');
      let eventId;
      let shortName;
      if (dash === -1) {
        eventId = inner;
        shortName = 'bad types';
      } else {
        if (dash < 2) return null;
        eventId = inner.slice(0, dash);
        shortName = inner.slice(dash + 1) || 'bad types';
      }
      const eventNum = eventId.slice(1);
      if (!/^\\d+$/.test(eventNum)) return null;
      return {
        suite: suite,
        suiteLabel: suiteLabel,
        eventId: eventId,
        eventLabel: 'event-' + eventNum,
        shortName: shortName,
        negOrder: -1,
      };
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

    function folderStats(tests) {
      const passed = tests.filter(t => t.outcome === 'passed').length;
      const failed = tests.filter(t => t.outcome === 'failed').length;
      return { passed, failed, total: tests.length };
    }

    function makeFolder(kind, folderKey, label, tests, renderChildren, metaExtra) {
      const stats = folderStats(tests);
      const el = document.createElement('div');
      // Keep folders collapsed unless the user opened them (or a child failed).
      const autoOpen = stats.failed > 0;
      el.className = kind + (openFolders.has(folderKey) || autoOpen ? ' open' : '');
      if (autoOpen) openFolders.add(folderKey);
      const head = document.createElement('div');
      head.className = 'folder-head';
      head.innerHTML =
        `<span class="folder-label">${esc(label)}</span>` +
        (stats.failed ? outcomeBadge('failed') : outcomeBadge('passed')) +
        `<span class="folder-meta">${esc(metaExtra || '')}` +
        (metaExtra ? ' · ' : '') +
        `${stats.total} tests · ${stats.passed} passed` +
        (stats.failed ? ` · ${stats.failed} failed` : '') + `</span>`;
      head.onclick = (ev) => {
        ev.stopPropagation();
        if (openFolders.has(folderKey)) openFolders.delete(folderKey); else openFolders.add(folderKey);
        el.classList.toggle('open');
      };
      const body = document.createElement('div');
      body.className = 'folder-body';
      renderChildren(body);
      el.appendChild(head);
      el.appendChild(body);
      return el;
    }

    function makeTestBlock(runKeyStr, t, displayName) {
      const testKey = runKeyStr + '::' + (t.nodeid || '');
      const block = document.createElement('div');
      block.className = 'test-block' + (openTests.has(testKey) ? ' open' : '');
      const uuid = testUuid(t) || '—';
      const uuidHtml = `<span class="test-uuid">${esc(uuid)}</span>`;
      const stepList = t.steps || [];
      const errSteps = stepList.filter(s => s.level === 'ERROR');
      const dataSteps = stepList.filter(s => s.level !== 'ERROR');
      const errStep = errSteps[0];
      let errPreview = '';
      if (t.outcome === 'failed' && errStep && errStep.message) {
        const raw = String(errStep.message).trim();
        const nl = raw.indexOf('\\n');
        const head = nl === -1 ? raw : raw.slice(0, nl).trim();
        const bodyTxt = nl === -1 ? '' : raw.slice(nl + 1).trim();
        errPreview =
          `<div class="fail-summary">` +
          `<div class="fail-title">${esc(head)}</div>` +
          (bodyTxt ? `<div>${esc(bodyTxt)}</div>` : '') +
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
      const label = displayName != null ? displayName : testName(t.nodeid);
      title.innerHTML =
        `${outcomeBadge(t.outcome)} <span class="test-name">${esc(label)}</span>` +
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
      return block;
    }

    function appendGroupedTests(container, runKeyStr, tests) {
      const plain = [];
      const suites = {};
      (tests || []).forEach(t => {
        const g = eventGroupInfo(t);
        if (!g) {
          plain.push(t);
          return;
        }
        if (!suites[g.suite]) suites[g.suite] = { label: g.suiteLabel, events: {} };
        if (!suites[g.suite].events[g.eventId]) {
          suites[g.suite].events[g.eventId] = {
            label: g.eventLabel,
            tests: [],
            negOrder: g.negOrder,
          };
        }
        suites[g.suite].events[g.eventId].tests.push({ test: t, shortName: g.shortName });
      });

      plain.forEach(t => container.appendChild(makeTestBlock(runKeyStr, t)));

      Object.keys(suites).sort().forEach(suiteKey => {
        const suite = suites[suiteKey];
        const allSuiteTests = [];
        const eventIds = Object.keys(suite.events).sort((a, b) => {
          const oa = suite.events[a].negOrder;
          const ob = suite.events[b].negOrder;
          if (oa != null && oa >= 0 && ob != null && ob >= 0) return oa - ob;
          const na = parseInt(String(a).replace(/\\D/g, ''), 10) || 0;
          const nb = parseInt(String(b).replace(/\\D/g, ''), 10) || 0;
          return na - nb;
        });
        eventIds.forEach(eid => {
          suite.events[eid].tests.forEach(x => allSuiteTests.push(x.test));
        });
        const suiteFolderKey = runKeyStr + '::folder::' + suiteKey;
        container.appendChild(makeFolder(
          'suite-folder',
          suiteFolderKey,
          suite.label,
          allSuiteTests,
          (suiteBody) => {
            eventIds.forEach(eventId => {
              const ev = suite.events[eventId];
              const eventTests = ev.tests.map(x => x.test);
              const eventFolderKey = suiteFolderKey + '::' + eventId;
              const sharedUuid = (() => {
              const seen = [];
              eventTests.forEach(t => {
                const u = testUuid(t);
                if (u && seen.indexOf(u) === -1) seen.push(u);
              });
              return seen.length === 1 ? seen[0] : '';
            })();
            // Under a rule folder, leaves are event-1..n — sort by event number.
            ev.tests.sort((a, b) => {
              const na = parseInt(String(a.shortName).replace(/\\D/g, ''), 10) || 0;
              const nb = parseInt(String(b.shortName).replace(/\\D/g, ''), 10) || 0;
              return na - nb;
            });
            suiteBody.appendChild(makeFolder(
                'event-folder',
                eventFolderKey,
                ev.label,
                eventTests,
                (eventBody) => {
                  ev.tests.forEach(x => {
                    eventBody.appendChild(makeTestBlock(runKeyStr, x.test, x.shortName));
                  });
                },
                sharedUuid ? ('UUID ' + sharedUuid) : null
              ));
            });
          },
          eventIds.length + ' events'
        ));
      });
    }

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
        appendGroupedTests(body, key, run.tests || []);
        box.appendChild(head);
        box.appendChild(body);
        root.appendChild(box);
      });
    }

    function ciBadge(run) {
      if (run.conclusion) {
        const c = run.conclusion;
        const cls = (c === 'success' || c === 'failure' || c === 'cancelled') ? c : 'skipped';
        return `<span class="badge ${cls}">${esc(c)}</span>`;
      }
      const st = run.status || 'queued';
      return `<span class="badge in_progress">${esc(st)}</span>`;
    }

    function ciHasInProgress(payload) {
      return ((payload && payload.runs) || []).some(
        r => !r.conclusion || (r.status && r.status !== 'completed')
      );
    }

    function renderCiRuns() {
      const root = document.getElementById('ci-runs');
      const errEl = document.getElementById('ci-error');
      const subEl = document.getElementById('ci-sub');
      const runs = (ciPayload && ciPayload.runs) || [];
      const updated = (ciPayload && ciPayload.updated_at) || '';
      errEl.textContent = (ciPayload && ciPayload.error) ? ciPayload.error : '';
      if (subEl) {
        subEl.textContent = updated
          ? ('Shared catalog · ' + runs.length + ' runs · updated ' + niceDate(updated) + ' — same on Windows and Mac')
          : 'Same public catalog on every machine — look here for workflow numbers like #38';
      }

      if (ciPayload && ciPayload.error && !runs.length) {
        root.className = 'empty';
        root.textContent = (ciPayload && ciPayload.error)
          ? String(ciPayload.error)
          : 'No CI runs loaded yet.';
        return;
      }
      if (!runs.length) {
        root.className = 'empty';
        root.textContent = 'No CI runs yet. Push or run the workflow from Actions.';
        return;
      }
      root.className = '';
      root.innerHTML = '';
      if (ciPayload.actions_url) {
        const src = document.createElement('div');
        src.className = 'ci-meta';
        src.style.marginBottom = '0.75rem';
        src.innerHTML = `Workflow: <a class="btn-link" style="margin:0" href="${esc(ciPayload.actions_url)}" target="_blank" rel="noopener">Open workflow on GitHub</a>`;
        root.appendChild(src);
      }
      runs.forEach((run) => {
        const key = String(run.run_number || run.html_url || '');
        const box = document.createElement('div');
        box.className = 'run' + (openCiRuns.has(key) ? ' open' : '');
        const head = document.createElement('div');
        head.className = 'run-head';
        const result = run.conclusion || run.status || 'unknown';
        const actionsLink = run.html_url
          ? `<a class="btn-link" style="margin:0 0 0 auto" href="${esc(run.html_url)}" target="_blank" rel="noopener" onclick="event.stopPropagation()">Actions run</a>`
          : `<span class="test-uuid">${esc(result)}</span>`;
        head.innerHTML = `
          <strong>#${esc(String(run.run_number || '?'))}</strong>
          ${ciBadge(run)}
          <span class="badge">${esc(run.event || '')}</span>
          <span class="badge">${esc(run.head_branch || '')}</span>
          <span class="ci-meta">${niceDate(run.created_at)}</span>
          ${actionsLink}`;
        head.onclick = () => {
          if (openCiRuns.has(key)) openCiRuns.delete(key); else openCiRuns.add(key);
          box.classList.toggle('open');
        };
        const body = document.createElement('div');
        body.className = 'run-body';
        // Per-run public Pages URL: /runs/<run_id>/ (no GitHub token).
        const runAllure = run.allure_url || '';
        let links = '';
        if (run.html_url) {
          links += `<a class="btn-link" href="${esc(run.html_url)}" target="_blank" rel="noopener">This run on Actions</a>`;
        }
        if (runAllure) {
          links += `<a class="btn btn-primary" href="${esc(runAllure)}" target="_blank" rel="noopener" onclick="event.stopPropagation()">Open Allure report</a>`;
        }
        const failHint = (run.conclusion === 'failure')
          ? `<div class="sub" style="color:#fca5a5;margin:.35rem 0">Failed CI run — Actions for logs; Open Allure is this run's published report.</div>`
          : '';
        body.innerHTML = `
          <div class="ci-meta">${esc(run.display_title || '')}</div>
          <div class="ci-meta">SHA ${esc(run.head_sha || '—')} · ${esc(result)}</div>
          ${failHint}
          <div class="actions" style="margin-top:.5rem">${links}</div>
          <pre style="margin-top:.75rem;white-space:pre-wrap;word-break:break-word;font-size:.8rem;color:#cbd5e1;background:#020617;border:1px solid #334155;border-radius:6px;padding:.75rem">${esc(JSON.stringify(run, null, 2))}</pre>
          <p class="ci-note">Open Allure report opens this run from the allure-pages branch (raw.githack) — same on every machine, no login.</p>`;
        box.appendChild(head);
        box.appendChild(body);
        root.appendChild(box);
      });
    }

    let ciTimer = null;
    function scheduleCiRefresh() {
      if (ciTimer) clearInterval(ciTimer);
      // Poll public catalog (no GitHub API rate limits).
      ciTimer = setInterval(() => refreshCi(true), 10000);
    }

    async function refreshCi(force) {
      try {
        const url = force ? '/api/ci-runs?refresh=1' : '/api/ci-runs';
        ciPayload = await fetch(url).then(r => r.json());
        renderCiRuns();
      } catch (err) {
        ciPayload = { runs: [], error: 'Could not reach local /api/ci-runs', allure_pages_url: '' };
        renderCiRuns();
      }
      scheduleCiRefresh();
    }

    function renderAll() {
      renderRuns();
      renderCiRuns();
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
    refreshCi(false);
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
        self.app.add_url_rule("/api/ci-runs", "ci_runs", self.api_ci_runs)
        self.app.add_url_rule(
            "/api/ci-runs/<run_id>/allure",
            "ci_allure_prepare",
            self.api_ci_allure_prepare,
            methods=["POST"],
        )
        self.app.add_url_rule(
            "/ci-allure/<run_id>/",
            "ci_allure_index",
            self.ci_allure_index,
        )
        self.app.add_url_rule(
            "/ci-allure/<run_id>/<path:filename>",
            "ci_allure_file",
            self.ci_allure_file,
        )
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
        return jsonify({
            "ok": True,
            "ci_source": "allure-pages/ci-runs.json",
            "uses_github_api": False,
            "features": [
                "presence_leave",
                "event_folders",
                "suite_test_names",
                "uuid_corner",
                "negatives_named_buckets",
                "ci_runs_panel",
                "ci_section_no_header_actions",
                "ci_catalog_cdn_mirrors",
            ],
        })

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
            ci_runs_json=json.dumps(CI_RUNS.load()),
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


    def api_ci_runs(self):
        force = request.args.get("refresh") in ("1", "true", "yes")
        return jsonify(CI_RUNS.load(force=force))

    def api_ci_allure_prepare(self, run_id):
        """Return the public Allure Pages URL (no GitHub token required)."""
        result = CI_RUNS.prepare_allure_report(run_id)
        status = 200 if result.get("ok") else 400
        return jsonify(result), status

    def ci_allure_index(self, run_id):
        folder = CI_RUNS.find_allure_index_dir(run_id)
        if folder is None:
            return jsonify({"ok": False, "error": "Allure report not loaded yet."}), 404
        return send_from_directory(folder, "index.html")

    def ci_allure_file(self, run_id, filename):
        folder = CI_RUNS.find_allure_index_dir(run_id)
        if folder is None:
            return jsonify({"ok": False, "error": "Allure report not loaded yet."}), 404
        return send_from_directory(folder, filename)

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
