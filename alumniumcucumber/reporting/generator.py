"""HTML and JSON report generator for the Alumnium reporter."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from .models import RunData


def generate_json(run_data: RunData) -> str:
    """Serialise RunData to a JSON string.

    Args:
        run_data: The completed run data.

    Returns:
        JSON string with 2-space indentation.
    """
    return json.dumps(dataclasses.asdict(run_data), indent=2, ensure_ascii=False)


def generate_html(run_data: RunData) -> str:
    """Generate a fully self-contained HTML report string.

    Args:
        run_data: The completed run data.

    Returns:
        Complete HTML document as a string.
    """
    data_json = json.dumps(dataclasses.asdict(run_data), ensure_ascii=False)
    # Escape </script> within data to prevent HTML injection
    data_json_safe = data_json.replace("</script>", "<\\/script>")

    html = f"""<!DOCTYPE html>
<html data-theme="dark" lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_esc(run_data.title)} — Alumnium Reporter</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
{_CSS}
</style>
</head>
<body>
<script>
if (window.location.protocol === 'file:') {{
  var banner = document.createElement('div');
  banner.style.cssText = 'background:#ff9800;color:#fff;padding:12px;text-align:center;font-family:system-ui;font-size:13px;line-height:1.8;position:relative;z-index:9999;';
  banner.innerHTML = 'Chat is disabled because the report was opened directly from the file system.<br>'
    + '<strong>Please double-click '
    + '<code style="background:rgba(0,0,0,.2);padding:1px 5px;border-radius:3px">open_report.bat</code>'
    + ' (Windows) or '
    + '<code style="background:rgba(0,0,0,.2);padding:1px 5px;border-radius:3px">open_report.command</code>'
    + ' (Mac) instead.</strong>';
  document.body.prepend(banner);
  var inp    = document.getElementById('chat-input');
  var btn    = document.getElementById('chat-send-btn');
  var keyRow = document.getElementById('chat-key-row');
  if (inp)    {{ inp.disabled = true; inp.placeholder = 'Chat unavailable \u2014 open via launcher file'; }}
  if (btn)      btn.disabled = true;
  if (keyRow)   keyRow.style.opacity = '0.3';
}}
</script>

<!-- HEADER -->
<header class="header">
  <div class="header-left">
    <div class="logo-icon">
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
        <circle cx="9" cy="9" r="9" fill="url(#lg1)"/>
        <path d="M5 9l3 3 5-5" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
        <defs><linearGradient id="lg1" x1="0" y1="0" x2="18" y2="18" gradientUnits="userSpaceOnUse"><stop stop-color="#4f8ef7"/><stop offset="1" stop-color="#00cba9"/></linearGradient></defs>
      </svg>
    </div>
    <span class="logo-wordmark">Alumnium</span>
    <span class="logo-sub">Reporter</span>
  </div>
  <nav class="header-nav">
    <button class="tab-btn active" id="tab-dashboard" onclick="switchTab('dashboard')">Dashboard</button>
    <button class="tab-btn" id="tab-fullreport" onclick="switchTab('fullreport')">Full Report</button>
  </nav>
  <div class="header-right">
    <button class="theme-toggle" id="themeToggle" onclick="toggleTheme()" title="Toggle theme">
      <span id="themeIcon">{_SVG_MOON}</span>
    </button>
    <span class="run-id-badge" id="runIdBadge"></span>
  </div>
</header>

<!-- DASHBOARD VIEW -->
<div id="view-dashboard" class="view active">
  <div class="main-content">

    <!-- Run Hero -->
    <section class="run-hero">
      <div class="run-title" id="runTitle"></div>
      <div class="run-meta" id="runMeta"></div>
    </section>

    <!-- Summary Cards -->
    <section class="cards-grid" id="cardsGrid"></section>

    <!-- Progress Bar -->
    <section class="progress-section">
      <div class="progress-bar-track">
        <div class="progress-segment pass" id="progressPass"></div>
        <div class="progress-segment fail" id="progressFail"></div>
        <div class="progress-segment skip" id="progressSkip"></div>
      </div>
    </section>

    <!-- Narrative + Chat -->
    <section class="two-col-section">
      <div class="narrative-panel" id="narrativePanel"></div>
      <div class="chat-panel" id="chatPanel"></div>
    </section>

    <!-- Feature Summary Table -->
    <section class="feature-table-section">
      <div class="feature-table-container" id="featureTableContainer"></div>
    </section>

    <!-- CTA -->
    <div class="cta-row">
      <button class="cta-btn" onclick="switchTab('fullreport')">View Full Report →</button>
    </div>

  </div>
</div>

<!-- FULL REPORT VIEW -->
<div id="view-fullreport" class="view">
  <div class="full-report-layout">
    <aside class="sidebar" id="sidebar"></aside>
    <div class="detail-main-wrap">
      <div id="filterBanner"></div>
      <main class="detail-main" id="detailMain"></main>
    </div>
    <aside class="screenshot-panel" id="screenshotPanel">
      <div class="sp-placeholder">
        <span class="sp-placeholder-icon">\U0001F4F7</span>
        <span class="sp-placeholder-text">Click a step thumbnail to preview</span>
      </div>
    </aside>
  </div>
</div>

<script>
const REPORT_DATA = {data_json_safe};

// ── Theme ──────────────────────────────────────────────────────────────
function toggleTheme() {{
  const html = document.documentElement;
  const current = html.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', next);
  sessionStorage.setItem('alumnium-theme', next);
  document.getElementById('themeIcon').innerHTML = next === 'dark' ? `{_SVG_MOON_JS}` : `{_SVG_SUN_JS}`;
}}

(function initTheme() {{
  const saved = sessionStorage.getItem('alumnium-theme') || 'dark';
  document.documentElement.setAttribute('data-theme', saved);
  if (saved === 'light') {{
    document.getElementById('themeIcon').innerHTML = `{_SVG_SUN_JS}`;
  }}
}})();

// ── Tab navigation ─────────────────────────────────────────────────────
let _activeFilter = null;   // null | 'passed' | 'failed' | 'skipped'

function switchTab(tab) {{
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('view-' + tab).classList.add('active');
  document.getElementById('tab-' + tab).classList.add('active');
  if (tab === 'fullreport') renderFullReport();
}}

function filterFullReport(status) {{
  _activeFilter = status;
  _fullRendered = false;
  switchTab('fullreport');
}}

function clearFilter() {{
  _activeFilter = null;
  _fullRendered = false;
  renderFullReport();
}}

// ── Helpers ────────────────────────────────────────────────────────────
function esc(s) {{
  if (!s) return '';
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}}

function fmt(secs) {{
  if (secs == null) return '--';
  if (secs < 1) return (secs * 1000).toFixed(0) + 'ms';
  if (secs < 60) return secs.toFixed(2) + 's';
  const m = Math.floor(secs / 60), s = (secs % 60).toFixed(1);
  return m + 'm ' + s + 's';
}}

function fmtDate(iso) {{
  if (!iso) return '--';
  try {{
    return new Date(iso).toLocaleString();
  }} catch(e) {{ return iso; }}
}}

function statusIcon(st) {{
  if (st === 'passed') return `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--status-pass)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/></svg>`;
  if (st === 'failed' || st === 'error') return `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--status-fail)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m15 9-6 6M9 9l6 6"/></svg>`;
  return `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--status-skip)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M8 12h8"/></svg>`;
}}

function statusDot(st, size) {{
  const sz = size || 8;
  const col = st === 'passed' ? 'var(--status-pass)' : (st === 'failed' || st === 'error') ? 'var(--status-fail)' : 'var(--status-skip)';
  return `<span style="display:inline-block;width:${{sz}}px;height:${{sz}}px;border-radius:50%;background:${{col}};flex-shrink:0"></span>`;
}}

function featureStatus(feat) {{
  if (feat.scenarios.some(s => s.status === 'failed' || s.status === 'error')) return 'failed';
  if (feat.scenarios.every(s => s.status === 'passed')) return 'passed';
  return 'skipped';
}}

// ── Dashboard Render ───────────────────────────────────────────────────
function renderDashboard() {{
  const d = REPORT_DATA;
  const s = d.summary;

  document.getElementById('runIdBadge').textContent = 'RUN ' + d.run_id;
  document.getElementById('runTitle').textContent = d.title;
  const screenshotBadge = {{'on_failure': '\U0001F4F7 Failures only', 'every_step': '\U0001F4F7 Every step', 'off': '\U0001F4F7 Off'}}[d.screenshot_mode] || '\U0001F4F7 Off';
  document.getElementById('runMeta').innerHTML =
    `<span class="meta-label">RUN ID</span> ${{esc(d.run_id)}} &nbsp;&middot;&nbsp; ` +
    `<span class="meta-label">MODEL</span> ${{esc(d.alumnium_model)}} &nbsp;&middot;&nbsp; ` +
    `<span class="meta-label">STARTED</span> ${{fmtDate(d.started_at)}} &nbsp;&middot;&nbsp; ` +
    `<span class="meta-label">DURATION</span> ${{fmt(s.total_duration)}} &nbsp;&middot;&nbsp; ` +
    `<span class="screenshot-mode-badge">${{screenshotBadge}}</span>`;

  // Cards
  const cards = [
    {{ label: 'TOTAL SCENARIOS', value: s.total_scenarios, sub: s.total_features + ' feature(s)', color: 'var(--accent-primary)', valueColor: 'var(--text-primary)', onclick: "switchTab('fullreport')" }},
    {{ label: 'PASSED', value: s.passed, sub: s.pass_rate + '% pass rate', color: 'var(--status-pass)', valueColor: 'var(--status-pass)', onclick: "filterFullReport('passed')" }},
    {{ label: 'FAILED', value: s.failed, sub: s.failed > 0 ? 'Needs attention' : 'All clear ✓', color: 'var(--status-fail)', valueColor: 'var(--status-fail)', onclick: "filterFullReport('failed')" }},
    {{ label: 'SKIPPED', value: s.skipped, sub: 'Not executed', color: 'var(--status-skip)', valueColor: 'var(--status-skip)', onclick: "filterFullReport('skipped')" }},
  ];
  document.getElementById('cardsGrid').innerHTML = cards.map(c => `
    <div class="summary-card summary-card-link" style="border-left-color:${{c.color}}" onclick="${{c.onclick}}">
      <div class="card-label">${{c.label}}</div>
      <div class="card-value" style="color:${{c.valueColor}}">${{c.value}}</div>
      <div class="card-sub">${{esc(c.sub)}}</div>
    </div>`).join('');

  // Progress bar
  const total = s.total_scenarios || 1;
  const pPass = (s.passed / total * 100).toFixed(2);
  const pFail = (s.failed / total * 100).toFixed(2);
  const pSkip = (s.skipped / total * 100).toFixed(2);
  setTimeout(() => {{
    document.getElementById('progressPass').style.width = pPass + '%';
    document.getElementById('progressFail').style.width = pFail + '%';
    document.getElementById('progressSkip').style.width = pSkip + '%';
  }}, 100);

  // Narrative
  renderNarrative(d.narrative);

  // Chat
  renderChat(d.alumnium_model);

  // Feature table
  renderFeatureTable(d.features);
}}

function renderNarrative(narrative) {{
  const el = document.getElementById('narrativePanel');
  if (!narrative || narrative.error || !narrative.headline) {{
    el.innerHTML = `
      <div class="panel-header"><span class="ai-label">{_SVG_SPARKLES_INLINE} AI Summary</span></div>
      <div class="narrative-fallback">AI narrative unavailable. Set ALUMNIUM_MODEL to enable this feature.</div>`;
    return;
  }}
  const riskClass = 'risk-' + narrative.risk_level;
  const riskLabel = narrative.risk_level === 'green' ? '&#9679; ALL GOOD' :
                    narrative.risk_level === 'red' ? '&#128308; CRITICAL' : '&#9888; ATTENTION';
  const paragraphs = narrative.body.split(/\\n\\n+/).map(p => `<p>${{esc(p)}}</p>`).join('');
  el.innerHTML = `
    <div class="panel-header">
      <span class="ai-label">{_SVG_SPARKLES_INLINE} AI Summary</span>
      <span class="risk-badge ${{riskClass}}">${{riskLabel}}</span>
    </div>
    <div class="narrative-headline">${{esc(narrative.headline)}}</div>
    <div class="narrative-body">${{paragraphs}}</div>
    <div class="narrative-footer">Generated by ${{esc(narrative.provider)}} &middot; alumnium-reporter</div>`;
}}

function renderFeatureTable(features) {{
  const el = document.getElementById('featureTableContainer');
  if (!features || !features.length) {{
    el.innerHTML = '<div class="empty-msg">No features recorded.</div>';
    return;
  }}
  const rows = features.map((feat, fi) => {{
    const pass = feat.scenarios.filter(s => s.status === 'passed').length;
    const fail = feat.scenarios.filter(s => s.status === 'failed' || s.status === 'error').length;
    const skip = feat.scenarios.filter(s => s.status !== 'passed' && s.status !== 'failed' && s.status !== 'error').length;
    const dur = feat.scenarios.reduce((a, s) => a + s.duration, 0);
    const st = feat.scenarios.some(s => s.status === 'failed' || s.status === 'error') ? 'FAILURES' :
               feat.scenarios.every(s => s.status === 'passed') ? 'PASSED' : 'SKIPPED';
    const stClass = st === 'FAILURES' ? 'badge-fail' : st === 'PASSED' ? 'badge-pass' : 'badge-skip';
    const bg = fi % 2 === 0 ? 'var(--surface)' : 'var(--bg-secondary)';
    return `<tr style="background:${{bg}}" class="feat-row" onclick="switchTab('fullreport'); scrollToFeature(${{fi}})">
      <td class="ft-name">${{esc(feat.name)}}</td>
      <td class="ft-num">${{feat.scenarios.length}}</td>
      <td class="ft-num" style="color:var(--status-pass)">${{pass || '\u2014'}}</td>
      <td class="ft-num" style="color:var(--status-fail)">${{fail || '\u2014'}}</td>
      <td class="ft-num" style="color:var(--status-skip)">${{skip || '\u2014'}}</td>
      <td class="ft-dur">${{fmt(dur)}}</td>
      <td><span class="badge ${{stClass}}">${{st}}</span></td>
    </tr>`;
  }}).join('');
  el.innerHTML = `<table class="feature-table">
    <thead><tr>
      <th>Feature</th><th>Scenarios</th><th>Passed</th><th>Failed</th><th>Skipped</th><th>Duration</th><th>Status</th>
    </tr></thead>
    <tbody>${{rows}}</tbody>
  </table>`;
}}

// ── Chat Panel ────────────────────────────────────────────────────────
const KEYLESS_PROVIDERS = ['ollama'];
let _apiKey = '';
let _chatMessages = [];
let _chatStarted = false;

function renderChat(model) {{
  const provider = (model || 'unset').split('/')[0].toLowerCase();
  const keyless = KEYLESS_PROVIDERS.includes(provider);
  if (keyless) {{ _apiKey = '__keyless__'; }}
  const el = document.getElementById('chatPanel');
  el.innerHTML = `
    <div class="panel-header">
      <span class="chat-label">{_SVG_MSG_INLINE} Ask about this run</span>
      <span class="provider-badge">${{esc(provider)}}</span>
    </div>
    ${{keyless ? `
    <div id="keySetArea" class="key-set-area" style="display:flex">
      &#128275; No API key required &mdash; ready to chat
    </div>` : `
    <div id="chat-key-row" class="key-entry-area">
      <div class="key-prompt">{_SVG_KEY_INLINE} Enter your ${{esc(provider)}} API key to chat</div>
      <div class="key-input-row">
        <input type="password" id="chat-api-key-input" placeholder="API key..." class="key-input" onkeydown="if(event.key==='Enter')submitKey()">
        <button class="key-submit-btn" onclick="submitKey()">&#8594;</button>
      </div>
      <div class="key-note">Key is never stored. Session memory only.</div>
    </div>
    <div id="keySetArea" class="key-set-area" style="display:none">
      &#128274; API key set &mdash; ready to chat &nbsp; <a href="#" onclick="clearKey();return false">Change</a>
    </div>`}}

    <div id="suggestionsArea" class="suggestions-area">
      <button class="suggestion-btn" onclick="sendSuggestion('Summarise what failed in this run')">Summarise what failed in this run</button>
      <button class="suggestion-btn" onclick="sendSuggestion('Which features had the most failures?')">Which features had the most failures?</button>
      <button class="suggestion-btn" onclick="sendSuggestion('What should be fixed first?')">What should be fixed first?</button>
    </div>
    <div id="messagesArea" class="messages-area"></div>
    <div class="input-row">
      <input type="text" id="chat-input" placeholder="Ask a question about this run..." class="chat-input" onkeydown="if(event.key==='Enter'&&!event.shiftKey){{event.preventDefault();sendChat();}}">
      <button id="chat-send-btn" class="send-btn" onclick="sendChat()">{_SVG_SEND_INLINE}</button>
    </div>`;
  if (window.location.protocol === 'file:') {{
    const _inp = document.getElementById('chat-input');
    const _btn = document.getElementById('chat-send-btn');
    if (_inp) {{ _inp.disabled = true; _inp.placeholder = 'Chat unavailable \u2014 open via launcher file'; }}
    if (_btn) _btn.disabled = true;
    document.querySelectorAll('.suggestion-btn').forEach(function(b) {{ b.disabled = true; }});
  }}
}}

function submitKey() {{
  const val = document.getElementById('chat-api-key-input').value.trim();
  if (!val) return;
  _apiKey = val;
  document.getElementById('chat-key-row').style.display = 'none';
  document.getElementById('keySetArea').style.display = 'flex';
}}

function clearKey() {{
  _apiKey = '';
  document.getElementById('chat-key-row').style.display = 'block';
  document.getElementById('keySetArea').style.display = 'none';
  document.getElementById('chat-api-key-input').value = '';
}}

function sendSuggestion(text) {{
  document.getElementById('chat-input').value = text;
  sendChat();
}}

async function sendChat() {{
  const input = document.getElementById('chat-input');
  const msg = input.value.trim();
  if (!msg) return;
  const _provider = (REPORT_DATA.alumnium_model || 'unset').split('/')[0].toLowerCase();
  if (!_apiKey && !KEYLESS_PROVIDERS.includes(_provider)) {{ alert('Please enter your API key first.'); return; }}
  input.value = '';
  if (!_chatStarted) {{
    _chatStarted = true;
    const sa = document.getElementById('suggestionsArea');
    if (sa) sa.style.display = 'none';
  }}
  appendMessage('user', msg);
  const sendBtn = document.getElementById('chat-send-btn');
  sendBtn.disabled = true;
  input.disabled = true;
  appendTyping();
  try {{
    const response = await callLlm(msg);
    removeTyping();
    appendMessage('ai', response);
  }} catch(e) {{
    removeTyping();
    appendMessage('error', 'Error: ' + e.message);
  }} finally {{
    sendBtn.disabled = false;
    input.disabled = false;
    input.focus();
  }}
}}

function appendMessage(role, text) {{
  const area = document.getElementById('messagesArea');
  const div = document.createElement('div');
  div.className = 'message ' + role;
  if (role === 'ai') {{
    div.innerHTML = renderMarkdown(text);
  }} else {{
    div.textContent = text;
  }}
  area.appendChild(div);
  area.scrollTop = area.scrollHeight;
}}

function appendTyping() {{
  const area = document.getElementById('messagesArea');
  const div = document.createElement('div');
  div.className = 'message ai typing';
  div.id = 'typingIndicator';
  div.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
  area.appendChild(div);
  area.scrollTop = area.scrollHeight;
}}

function removeTyping() {{
  const el = document.getElementById('typingIndicator');
  if (el) el.remove();
}}

function renderMarkdown(text) {{
  if (!text) return '';
  let h = esc(text);
  // Bold
  h = h.replace(/[*][*](.+?)[*][*]/g, '<strong>$1</strong>');
  // Italic
  h = h.replace(/[*](.+?)[*]/g, '<em>$1</em>');
  // Inline code
  h = h.replace(/`([^`]+)`/g, '<code>$1</code>');
  // Bullets
  h = h.replace(/^[*-] (.+)$/gm, '<li>$1</li>');
  h = h.replace(/(<li>.*<[/]li>)/s, '<ul>$1</ul>');
  // Line breaks
  h = h.replace(/\\n/g, '<br>');
  return h;
}}

async function callLlm(userMsg) {{
  const model = REPORT_DATA.alumnium_model || '';
  const provider = model.split('/')[0].toLowerCase();
  const modelId = model.includes('/') ? model.split('/').slice(1).join('/') : null;

  const systemPrompt = `You are an AI assistant embedded in a BDD test report for a QA team.
You have access to the complete test run data below, including every feature,
scenario, step, status, duration, error message, and AI failure analysis.

Answer questions about the test results clearly and precisely.
Use specific scenario names and feature names in your answers.
If asked about something not in the test data, say so clearly.
Format your answers with short paragraphs. Use bullet points for lists.
Never fabricate test results that are not in the data provided.

Test run data (JSON):
${{JSON.stringify(REPORT_DATA)}}`;

  if (provider === 'anthropic') {{
    const resp = await fetch('https://api.anthropic.com/v1/messages', {{
      method: 'POST',
      headers: {{
        'x-api-key': _apiKey,
        'anthropic-version': '2023-06-01',
        'anthropic-dangerous-direct-browser-access': 'true',
        'content-type': 'application/json',
      }},
      body: JSON.stringify({{
        model: modelId || 'claude-sonnet-4-20250514',
        max_tokens: 1024,
        system: systemPrompt,
        messages: [{{ role: 'user', content: userMsg }}],
      }}),
    }});
    if (!resp.ok) throw new Error('Anthropic API error ' + resp.status);
    const data = await resp.json();
    return data.content[0].text;

  }} else if (provider === 'openai') {{
    const resp = await fetch('https://api.openai.com/v1/chat/completions', {{
      method: 'POST',
      headers: {{ 'Authorization': 'Bearer ' + _apiKey, 'Content-Type': 'application/json' }},
      body: JSON.stringify({{
        model: modelId || 'gpt-4o',
        max_tokens: 1024,
        messages: [{{ role: 'system', content: systemPrompt }}, {{ role: 'user', content: userMsg }}],
      }}),
    }});
    if (!resp.ok) throw new Error('OpenAI API error ' + resp.status);
    const data = await resp.json();
    return data.choices[0].message.content;

  }} else if (provider === 'google') {{
    const gModel = modelId || 'gemini-1.5-flash';
    const resp = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${{gModel}}:generateContent?key=${{_apiKey}}`, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{
        contents: [{{ parts: [{{ text: systemPrompt + '\\n\\nUser: ' + userMsg }}] }}],
      }}),
    }});
    if (!resp.ok) throw new Error('Google API error ' + resp.status);
    const data = await resp.json();
    return data.candidates[0].content.parts[0].text;

  }} else if (provider === 'ollama') {{
    const resp = await fetch('http://localhost:11434/api/chat', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{
        model: modelId || 'mistral-small3.1',
        stream: false,
        messages: [{{ role: 'system', content: systemPrompt }}, {{ role: 'user', content: userMsg }}],
      }}),
    }});
    if (!resp.ok) throw new Error('Ollama API error ' + resp.status);
    const data = await resp.json();
    return data.message.content;

  }} else if (provider === 'mistral') {{
    const resp = await fetch('https://api.mistral.ai/v1/chat/completions', {{
      method: 'POST',
      headers: {{ 'Authorization': 'Bearer ' + _apiKey, 'Content-Type': 'application/json' }},
      body: JSON.stringify({{
        model: modelId || 'mistral-small-latest',
        max_tokens: 1024,
        messages: [{{ role: 'system', content: systemPrompt }}, {{ role: 'user', content: userMsg }}],
      }}),
    }});
    if (!resp.ok) throw new Error('Mistral API error ' + resp.status);
    const data = await resp.json();
    return data.choices[0].message.content;

  }} else if (provider === 'deepseek') {{
    const resp = await fetch('https://api.deepseek.com/chat/completions', {{
      method: 'POST',
      headers: {{ 'Authorization': 'Bearer ' + _apiKey, 'Content-Type': 'application/json' }},
      body: JSON.stringify({{
        model: modelId || 'deepseek-chat',
        max_tokens: 1024,
        messages: [{{ role: 'system', content: systemPrompt }}, {{ role: 'user', content: userMsg }}],
      }}),
    }});
    if (!resp.ok) throw new Error('DeepSeek API error ' + resp.status);
    const data = await resp.json();
    return data.choices[0].message.content;

  }} else {{
    throw new Error('Chat not supported for provider: ' + provider);
  }}
}}

// ── Full Report Render ────────────────────────────────────────────────
let _fullRendered = false;

function _matchesFilter(sc) {{
  if (!_activeFilter) return true;
  if (_activeFilter === 'failed') return sc.status === 'failed' || sc.status === 'error';
  return sc.status === _activeFilter;
}}

function renderFilterBanner() {{
  const el = document.getElementById('filterBanner');
  if (!el) return;
  if (!_activeFilter) {{ el.innerHTML = ''; return; }}
  const labels = {{ passed: 'Passed', failed: 'Failed', skipped: 'Skipped' }};
  const label = labels[_activeFilter] || _activeFilter;
  el.innerHTML = `<div class="filter-banner">
    Showing: <strong>${{label}}</strong> scenarios only
    <button class="filter-clear-btn" onclick="clearFilter()">&#10005; Show all</button>
  </div>`;
}}

function renderFullReport() {{
  if (_fullRendered) return;
  _fullRendered = true;

  const d = REPORT_DATA;
  renderFilterBanner();
  renderSidebar(d.features);
  renderDetailMain(d.features);
}}

function renderSidebar(features) {{
  const el = document.getElementById('sidebar');
  if (!features || !features.length) {{
    el.innerHTML = '<div class="sidebar-empty">No features.</div>';
    return;
  }}
  let html = '<div class="sidebar-title">FEATURES</div>';
  let firstFeatureShown = true;
  features.forEach((feat, fi) => {{
    const matching = feat.scenarios.filter(_matchesFilter);
    if (!matching.length) return;
    const st = featureStatus(feat);
    const expanded = firstFeatureShown ? 'expanded' : '';
    const open = firstFeatureShown ? 'block' : 'none';
    firstFeatureShown = false;
    html += `<div class="sidebar-feature ${{expanded}}" id="sf-${{fi}}">
      <div class="sf-header" onclick="toggleSidebarFeature(${{fi}})">
        ${{statusDot(st, 8)}}
        <span class="sf-name">${{esc(feat.name)}}</span>
        <span class="sf-count">${{matching.length}}</span>
        <span class="sf-chevron" id="sfc-${{fi}}">{_SVG_CHEVRON_RIGHT_INLINE}</span>
      </div>
      <div class="sf-scenarios" id="sfs-${{fi}}" style="display:${{open}}">`;
    feat.scenarios.forEach((sc, si) => {{
      if (!_matchesFilter(sc)) return;
      html += `<div class="sf-scenario" id="sss-${{fi}}-${{si}}" onclick="scrollToScenario('${{sc.id}}', ${{fi}}, ${{si}})">
        ${{statusDot(sc.status, 6)}}
        <span class="sfs-name">${{esc(sc.name)}}</span>
      </div>`;
    }});
    html += `</div></div>`;
  }});
  el.innerHTML = html;
}}

function toggleSidebarFeature(fi) {{
  const list = document.getElementById('sfs-' + fi);
  const chevron = document.getElementById('sfc-' + fi);
  const isOpen = list.style.display !== 'none';
  list.style.display = isOpen ? 'none' : 'block';
  chevron.innerHTML = isOpen ? `{_SVG_CHEVRON_RIGHT_INLINE}` : `{_SVG_CHEVRON_DOWN_INLINE}`;
}}

function scrollToFeature(fi) {{
  const el = document.getElementById('feat-' + fi);
  if (el) el.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
}}

function scrollToScenario(scId, fi, si) {{
  // Mark active
  document.querySelectorAll('.sf-scenario').forEach(e => e.classList.remove('active'));
  const sel = document.getElementById('sss-' + fi + '-' + si);
  if (sel) sel.classList.add('active');
  const el = document.getElementById('sc-' + scId);
  if (el) el.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
}}

function renderDetailMain(features) {{
  const el = document.getElementById('detailMain');
  if (!features || !features.length) {{
    el.innerHTML = '<div class="empty-msg">No features recorded.</div>';
    return;
  }}
  const filtered = features.map(feat => ({{
    ...feat,
    scenarios: feat.scenarios.filter(_matchesFilter),
  }})).filter(feat => feat.scenarios.length > 0);
  if (!filtered.length) {{
    el.innerHTML = '<div class="empty-msg">No scenarios match this filter.</div>';
    return;
  }}
  el.innerHTML = filtered.map((feat, fi) => renderFeatureSection(feat, fi)).join('');
}}

function renderFeatureSection(feat, fi) {{
  const tags = (feat.tags || []).map(t => `<span class="tag-badge">${{esc(t)}}</span>`).join('');
  const desc = feat.description ? `<div class="feat-desc">${{esc(feat.description)}}</div>` : '';
  const scenariosHtml = feat.scenarios.map(sc => renderScenarioCard(sc)).join('');
  return `<section class="feat-section" id="feat-${{fi}}">
    <div class="feat-heading">
      <span class="feat-title">${{esc(feat.name)}}</span>
      ${{tags}}
      <span class="feat-file">${{esc(feat.file)}}</span>
    </div>
    ${{desc}}
    ${{scenariosHtml}}
  </section>`;
}}

function renderScenarioCard(sc) {{
  const st = sc.status;
  const borderColor = st === 'passed' ? 'var(--status-pass)' : (st === 'failed' || st === 'error') ? 'var(--status-fail)' : 'var(--status-skip)';
  const defaultOpen = st === 'failed' || st === 'error';
  const tags = (sc.tags || []).map(t => `<span class="tag-badge">${{esc(t)}}</span>`).join('');
  const icon20 = st === 'passed' ?
    `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--status-pass)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/></svg>` :
    (st === 'failed' || st === 'error') ?
    `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--status-fail)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m15 9-6 6M9 9l6 6"/></svg>` :
    `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--status-skip)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M8 12h8"/></svg>`;
  const stepsHtml = (sc.steps || []).map((st2, si) => renderStep(st2, si + 1, sc.id)).join('');
  const aiHtml = sc.ai_analysis ? renderAiAnalysis(sc.ai_analysis) : '';
  const bodyStyle = defaultOpen ? '' : 'display:none';
  const chevronInitial = defaultOpen ? `{_SVG_CHEVRON_DOWN_INLINE}` : `{_SVG_CHEVRON_RIGHT_INLINE}`;
  return `<div class="scenario-card" id="sc-${{sc.id}}" style="border-left-color:${{borderColor}}">
    <div class="sc-header" onclick="toggleScenario('scb-${{sc.id}}', 'sch-${{sc.id}}')">
      ${{icon20}}
      <span class="sc-name">${{esc(sc.name)}}</span>
      ${{tags}}
      <span class="sc-dur">{_SVG_CLOCK_INLINE} ${{fmt(sc.duration)}}</span>
      <span class="sc-chevron" id="sch-${{sc.id}}">${{chevronInitial}}</span>
    </div>
    <div class="sc-body" id="scb-${{sc.id}}" style="${{bodyStyle}}">
      <div class="steps-list">${{stepsHtml}}</div>
      ${{aiHtml}}
    </div>
  </div>`;
}}

function toggleScenario(bodyId, chevronId) {{
  const body = document.getElementById(bodyId);
  const chev = document.getElementById(chevronId);
  const isOpen = body.style.display !== 'none';
  body.style.display = isOpen ? 'none' : 'block';
  chev.innerHTML = isOpen ? `{_SVG_CHEVRON_RIGHT_INLINE}` : `{_SVG_CHEVRON_DOWN_INLINE}`;
}}

function renderStep(step, stepIdx, scenarioId) {{
  const kwColors = {{
    'Given': 'var(--accent-primary)', 'When': 'var(--accent-primary)',
    'Then': 'var(--accent-secondary)',
  }};
  const kwColor = kwColors[step.keyword] || 'var(--text-muted)';
  const stColor = (step.status === 'failed' || step.status === 'error') ? 'var(--status-fail)' : 'var(--text-secondary)';
  const badge = step.alumnium_type === 'check' ?
    '<span class="call-badge check">check</span>' :
    '<span class="call-badge do">do</span>';
  const stIcon = step.status === 'passed' ?
    `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--status-pass)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/></svg>` :
    (step.status === 'failed' || step.status === 'error') ?
    `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--status-fail)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m15 9-6 6M9 9l6 6"/></svg>` :
    step.status === 'untested' ? `<span style="color:var(--text-muted);font-size:12px">&#9675;</span>` :
    `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--status-skip)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M8 12h8"/></svg>`;
  let extras = '';
  if ((step.status === 'failed' || step.status === 'error') && step.error_message) {{
    const errLabel = step.status === 'error'
      ? `<span class="error-type-badge">${{esc(step.exception_type || 'Error')}}</span>`
      : `<span class="error-type-badge assertion">Assertion failed</span>`;
    extras += `<div class="error-block">${{errLabel}}${{esc(step.error_message)}}</div>`;
  }}
  if (step.doc_string) {{
    extras += `<div class="doc-string">${{esc(step.doc_string)}}</div>`;
  }}
  if (step.data_table && step.data_table.length) {{
    const thead = step.data_table[0].map(c => `<th>${{esc(c)}}</th>`).join('');
    const tbody = step.data_table.slice(1).map(row =>
      '<tr>' + row.map(c => `<td>${{esc(c)}}</td>`).join('') + '</tr>'
    ).join('');
    extras += `<div class="table-wrap"><table class="step-table"><thead><tr>${{thead}}</tr></thead><tbody>${{tbody}}</tbody></table></div>`;
  }}
  const thumbHtml = step.screenshot_path
    ? `<span class="step-thumb-wrap" onclick="openScenarioScreenshots('${{scenarioId}}', ${{stepIdx}})">
        <img src="${{step.screenshot_path}}" class="step-thumb-img" alt="screenshot" />
        <div class="step-thumb-popover"><img src="${{step.screenshot_path}}" /></div>
      </span>`
    : '';
  return `<div class="step-row">
    <div class="step-main">
      <span class="step-kw" style="color:${{kwColor}}">${{esc(step.keyword)}}</span>
      <span class="step-text" style="color:${{stColor}}">${{esc(step.text)}}</span>
      ${{badge}}
      <span class="step-icon">${{stIcon}}</span>
      <span class="step-dur">${{fmt(step.duration)}}</span>
      ${{thumbHtml}}
    </div>
    ${{extras}}
  </div>`;
}}

function renderAiAnalysis(ai) {{
  if (ai.error) {{
    return `<div class="ai-panel">
      <div class="ai-panel-header" onclick="toggleAiPanel(this)">
        <span class="ai-panel-label">{_SVG_SPARKLES_INLINE} AI Failure Analysis</span>
        <span class="ai-chevron">{_SVG_CHEVRON_DOWN_INLINE}</span>
      </div>
      <div class="ai-panel-body">
        <div class="ai-unavail">AI analysis unavailable: ${{esc(ai.error)}}</div>
      </div>
    </div>`;
  }}
  const sevColors = {{
    critical: '#ff2200', high: 'var(--status-fail)',
    medium: 'var(--ai-accent)', low: 'var(--status-skip)', unknown: 'var(--text-muted)',
  }};
  const sevColor = sevColors[ai.severity] || 'var(--text-muted)';
  return `<div class="ai-panel">
    <div class="ai-panel-header" onclick="toggleAiPanel(this)">
      <span class="ai-panel-label">{_SVG_SPARKLES_INLINE} AI Failure Analysis</span>
      <span class="sev-badge" style="color:${{sevColor}}">${{esc(ai.severity.toUpperCase())}}</span>
      <span class="ai-provider">${{esc(ai.provider)}}</span>
      <span class="ai-chevron">{_SVG_CHEVRON_DOWN_INLINE}</span>
    </div>
    <div class="ai-panel-body">
      <div class="ai-summary">${{esc(ai.summary)}}</div>
      <div class="ai-section"><span class="ai-section-label">ROOT CAUSE</span><div class="ai-section-val">${{esc(ai.root_cause)}}</div></div>
      <div class="ai-section"><span class="ai-section-label">SUGGESTED FIX</span><div class="ai-section-val">${{esc(ai.suggestion)}}</div></div>
    </div>
  </div>`;
}}

function toggleAiPanel(header) {{
  const body = header.nextElementSibling;
  const chev = header.querySelector('.ai-chevron');
  const isOpen = body.style.display !== 'none';
  body.style.display = isOpen ? 'none' : 'block';
  if (chev) chev.innerHTML = isOpen ? `{_SVG_CHEVRON_RIGHT_INLINE}` : `{_SVG_CHEVRON_DOWN_INLINE}`;
}}

// ── Screenshot Panel ───────────────────────────────────────────────────
let _spScreenshots = [];
let _spIdx = 0;

function openScenarioScreenshots(scenarioId, clickedStepIdx) {{
  let scenario = null;
  for (const feat of REPORT_DATA.features) {{
    scenario = feat.scenarios.find(s => s.id === scenarioId);
    if (scenario) break;
  }}
  if (!scenario) return;
  _spScreenshots = [];
  let startIdx = 0;
  scenario.steps.forEach((step, i) => {{
    if (step.screenshot_path) {{
      if (i + 1 === clickedStepIdx) startIdx = _spScreenshots.length;
      _spScreenshots.push({{ src: step.screenshot_path, text: step.text }});
    }}
  }});
  if (!_spScreenshots.length) return;
  _spIdx = startIdx;
  document.getElementById('screenshotPanel').classList.add('visible');
  _renderSpPanel();
}}

function _renderSpPanel() {{
  const panel = document.getElementById('screenshotPanel');
  const item = _spScreenshots[_spIdx];
  const total = _spScreenshots.length;
  const hasPrev = _spIdx > 0;
  const hasNext = _spIdx < total - 1;
  const dots = _spScreenshots.map((_, i) =>
    `<span class="sp-dot${{i === _spIdx ? ' active' : ''}}" onclick="spGoTo(${{i}})"></span>`
  ).join('');
  panel.innerHTML = `
    <div class="sp-header">
      <span class="sp-title">\U0001F4F7 ${{_spIdx + 1}} / ${{total}}</span>
      <button class="sp-close" onclick="closeScreenshotPanel()" title="Close">&#x2715;</button>
    </div>
    <div class="sp-step-text">${{esc(item.text)}}</div>
    <div class="sp-image-wrap">
      <img src="${{item.src}}" class="sp-image" onclick="openLightbox('${{item.src}}')" title="Click to enlarge" />
    </div>
    <div class="sp-nav">
      <button class="sp-nav-btn" onclick="spPrev()" ${{hasPrev ? '' : 'disabled'}}>&#8592; Prev</button>
      <div class="sp-dots">${{dots}}</div>
      <button class="sp-nav-btn" onclick="spNext()" ${{hasNext ? '' : 'disabled'}}>Next &#8594;</button>
    </div>`;
}}

function spPrev() {{ if (_spIdx > 0) {{ _spIdx--; _renderSpPanel(); }} }}
function spNext() {{ if (_spIdx < _spScreenshots.length - 1) {{ _spIdx++; _renderSpPanel(); }} }}
function spGoTo(i) {{ _spIdx = i; _renderSpPanel(); }}

function closeScreenshotPanel() {{
  _spScreenshots = []; _spIdx = 0;
  const panel = document.getElementById('screenshotPanel');
  panel.classList.remove('visible');
  panel.innerHTML = `<div class="sp-placeholder">
    <span class="sp-placeholder-icon">\U0001F4F7</span>
    <span class="sp-placeholder-text">Click a step thumbnail to preview</span>
  </div>`;
}}

// ── Lightbox ───────────────────────────────────────────────────────────
function openLightbox(src) {{
  const overlay = document.createElement('div');
  overlay.style.cssText = 'position:fixed;inset:0;z-index:500;background:rgba(0,0,0,.85);'
    + 'display:flex;align-items:center;justify-content:center;cursor:zoom-out;';
  const img = document.createElement('img');
  img.src = src;
  img.style.cssText = 'max-width:95vw;max-height:90vh;border-radius:8px;'
    + 'box-shadow:0 8px 40px rgba(0,0,0,.6);';
  overlay.appendChild(img);
  overlay.addEventListener('click', () => overlay.remove());
  document.addEventListener('keydown', function esc(e) {{
    if (e.key === 'Escape') {{ overlay.remove(); document.removeEventListener('keydown', esc); }}
  }});
  document.body.appendChild(overlay);
}}

// ── Boot ────────────────────────────────────────────────────────────────
renderDashboard();
document.addEventListener('keydown', function(e) {{
  if (!_spScreenshots.length) return;
  if (e.key === 'ArrowLeft') spPrev();
  else if (e.key === 'ArrowRight') spNext();
}});
</script>
</body>
</html>"""
    return html


# SVG icons

_SVG_MOON = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>'
_SVG_SUN = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>'

# JS-safe versions (used inside f-string JS template literals, need single quotes for SVG attrs)
_SVG_MOON_JS = _SVG_MOON.replace('"', "'")
_SVG_SUN_JS = _SVG_SUN.replace('"', "'")

_SVG_SPARKLES_INLINE = '<svg style="display:inline;vertical-align:-2px" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--ai-accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/></svg>'
_SVG_MSG_INLINE = '<svg style="display:inline;vertical-align:-2px" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>'
_SVG_KEY_INLINE = '<svg style="display:inline;vertical-align:-2px" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="7.5" cy="15.5" r="5.5"/><path d="m21 2-9.6 9.6"/><path d="m15.5 7.5 3 3L22 7l-3-3"/></svg>'
_SVG_SEND_INLINE = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>'
_SVG_CLOCK_INLINE = '<svg style="display:inline;vertical-align:-2px" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>'
_SVG_CHEVRON_RIGHT_INLINE = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>'
_SVG_CHEVRON_DOWN_INLINE = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>'


def _esc(s: str) -> str:
    """HTML-escape a string."""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


_CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

[data-theme="dark"] {
  --bg: #0a0b10; --bg-secondary: #0f1117; --surface: #141720; --surface-hover: #1a1e2d;
  --border: #1e2235; --border-subtle: #181c2a;
  --text-primary: #e4e8f4; --text-secondary: #8892a8; --text-muted: #4a5168;
  --accent-primary: #4f8ef7; --accent-secondary: #00cba9;
  --accent-gradient: linear-gradient(135deg, #4f8ef7, #00cba9);
  --status-pass: #22c97a; --status-fail: #f04f5f; --status-skip: #f5a623; --status-pending: #5b8af5;
  --ai-accent: #f5a623; --risk-green: #22c97a; --risk-amber: #f5a623; --risk-red: #f04f5f;
  --shadow: 0 2px 12px rgba(0,0,0,0.4); --shadow-lg: 0 8px 32px rgba(0,0,0,0.5);
}
[data-theme="light"] {
  --bg: #f5f6fa; --bg-secondary: #ffffff; --surface: #ffffff; --surface-hover: #f0f2f8;
  --border: #e2e6f0; --border-subtle: #edf0f8;
  --text-primary: #111827; --text-secondary: #4b5773; --text-muted: #9ca3c0;
  --accent-primary: #2563eb; --accent-secondary: #0ea5a0;
  --accent-gradient: linear-gradient(135deg, #2563eb, #0ea5a0);
  --status-pass: #16a362; --status-fail: #dc2626; --status-skip: #d97706; --status-pending: #2563eb;
  --ai-accent: #d97706; --risk-green: #16a362; --risk-amber: #d97706; --risk-red: #dc2626;
  --shadow: 0 2px 8px rgba(0,0,0,0.08); --shadow-lg: 0 8px 24px rgba(0,0,0,0.12);
}
:root {
  --radius-sm: 4px; --radius: 8px; --radius-lg: 12px; --radius-pill: 999px;
  --transition: 150ms ease;
}

html, body { height: 100%; }
body {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 14px; line-height: 1.6;
  background: var(--bg); color: var(--text-primary);
  transition: background-color 200ms, color 200ms;
}

/* ── Header ── */
.header {
  position: sticky; top: 0; z-index: 100;
  height: 60px; display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px; gap: 16px;
  background: var(--bg); border-bottom: 1px solid var(--border);
  backdrop-filter: blur(12px);
}
.header-left { display: flex; align-items: center; gap: 10px; }
.logo-icon {
  width: 32px; height: 32px; border-radius: var(--radius);
  background: var(--accent-gradient); display: flex; align-items: center; justify-content: center;
}
.logo-wordmark { font-size: 16px; font-weight: 600; color: var(--text-primary); }
.logo-sub { font-size: 12px; color: var(--text-secondary); }
.header-nav { display: flex; gap: 4px; }
.tab-btn {
  background: none; border: none; cursor: pointer; padding: 8px 16px;
  font-size: 13px; font-weight: 500; color: var(--text-secondary);
  border-bottom: 2px solid transparent; transition: var(--transition);
  font-family: inherit;
}
.tab-btn:hover { color: var(--text-primary); }
.tab-btn.active { color: var(--accent-primary); border-bottom-color: var(--accent-primary); }
.header-right { display: flex; align-items: center; gap: 12px; }
.theme-toggle {
  background: none; border: 1px solid var(--border); border-radius: var(--radius);
  width: 32px; height: 32px; cursor: pointer; display: flex; align-items: center;
  justify-content: center; color: var(--text-secondary); transition: var(--transition);
}
.theme-toggle:hover { border-color: var(--accent-primary); color: var(--accent-primary); }
.run-id-badge {
  font-family: 'JetBrains Mono', monospace; font-size: 11px;
  color: var(--accent-primary); background: var(--surface);
  border: 1px solid var(--border); border-radius: var(--radius); padding: 3px 8px;
}

/* ── Views ── */
.view { display: none; }
.view.active { display: block; }

/* ── Dashboard ── */
.main-content { max-width: 1280px; margin: 0 auto; padding: 24px 24px 48px; }
.run-hero {
  padding: 28px 32px; margin-bottom: 24px; border-radius: var(--radius-lg);
  background: linear-gradient(135deg, var(--bg-secondary), var(--bg));
  border: 1px solid var(--border);
}
.run-title { font-size: 24px; font-weight: 700; color: var(--text-primary); margin-bottom: 8px; }
.run-meta { font-family: 'JetBrains Mono', monospace; font-size: 13px; color: var(--text-secondary); }
.meta-label { font-weight: 700; font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; opacity: 0.7; }
.screenshot-mode-badge { font-size: 11px; color: var(--text-2, var(--text-secondary)); background: var(--surface); border: 1px solid var(--border); border-radius: 20px; padding: 3px 10px; font-family: 'JetBrains Mono', monospace; }
.cards-grid {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px;
}
@media (max-width: 768px) { .cards-grid { grid-template-columns: repeat(2, 1fr); } }
.summary-card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); border-left: 3px solid; padding: 20px;
  box-shadow: var(--shadow);
}
.card-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-muted); margin-bottom: 8px; }
.card-value { font-size: 40px; font-weight: 800; line-height: 1; margin-bottom: 6px; }
.card-sub { font-size: 12px; color: var(--text-muted); }
.summary-card-link { cursor: pointer; user-select: none; }
.summary-card-link:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,.25); }
.filter-banner { display:flex; align-items:center; gap:10px; padding:9px 14px;
  background:rgba(0,203,169,0.07); border:1px solid rgba(0,203,169,0.2);
  border-radius:var(--radius); margin-bottom:16px; font-size:13px; color:var(--text-secondary); }
.filter-banner strong { color:var(--text-primary); }
.filter-clear-btn { margin-left:auto; background:none; border:1px solid var(--border);
  border-radius:var(--radius); color:var(--text-muted); font-size:11px; padding:3px 10px;
  cursor:pointer; transition:var(--transition); font-family:inherit; }
.filter-clear-btn:hover { border-color:var(--accent-primary); color:var(--accent-primary); }
.detail-main-wrap { flex:1; display:flex; flex-direction:column; overflow:hidden; min-width:0; }
.progress-section { margin-bottom: 24px; }
.progress-bar-track {
  height: 6px; background: var(--surface); border-radius: var(--radius-pill);
  overflow: hidden; display: flex;
}
.progress-segment {
  height: 100%; width: 0; transition: width 0.8s cubic-bezier(0.4,0,0.2,1);
}
.progress-segment.pass { background: var(--status-pass); }
.progress-segment.fail { background: var(--status-fail); }
.progress-segment.skip { background: var(--status-skip); }
.two-col-section {
  display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px;
}
@media (max-width: 900px) { .two-col-section { grid-template-columns: 1fr; } }
.narrative-panel, .chat-panel {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-lg); padding: 20px; box-shadow: var(--shadow);
}
.chat-panel { padding: 0; display: flex; flex-direction: column; overflow: hidden; min-height: 380px; }
.panel-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 12px; flex-shrink: 0;
}
.chat-panel .panel-header { padding: 16px 20px 12px; border-bottom: 1px solid var(--border); margin-bottom: 0; }
.ai-label { font-size: 12px; font-weight: 600; color: var(--ai-accent); display: flex; align-items: center; gap: 6px; }
.chat-label { font-size: 12px; font-weight: 600; color: var(--text-primary); display: flex; align-items: center; gap: 6px; }
.provider-badge {
  font-family: 'JetBrains Mono', monospace; font-size: 11px;
  color: var(--accent-primary); background: var(--bg); border: 1px solid var(--border);
  border-radius: var(--radius-pill); padding: 2px 8px;
}
.risk-badge {
  font-size: 10px; font-weight: 700; letter-spacing: 0.06em;
  border-radius: var(--radius-pill); padding: 3px 10px; border: 1px solid;
}
.risk-green { color: var(--risk-green); background: rgba(34,201,122,0.12); border-color: var(--risk-green); }
.risk-amber { color: var(--risk-amber); background: rgba(245,166,35,0.12); border-color: var(--risk-amber); }
.risk-red   { color: var(--risk-red);   background: rgba(240,79,95,0.12);  border-color: var(--risk-red); }
.narrative-headline { font-size: 16px; font-weight: 600; color: var(--text-primary); margin-bottom: 12px; }
.narrative-body p { font-size: 14px; color: var(--text-secondary); line-height: 1.7; margin-bottom: 10px; }
.narrative-footer { font-size: 11px; color: var(--text-muted); margin-top: 12px; }
.narrative-fallback { font-size: 13px; color: var(--text-muted); display: flex; align-items: center; gap: 6px; margin-top: 8px; }

/* Chat internals */
.key-entry-area { padding: 12px 16px; flex-shrink: 0; }
.key-prompt { font-size: 12px; color: var(--text-secondary); margin-bottom: 8px; display: flex; align-items: center; gap: 6px; }
.key-input-row { display: flex; gap: 8px; }
.key-input {
  flex: 1; background: var(--bg-secondary); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 8px 12px; color: var(--text-primary);
  font-size: 13px; font-family: 'JetBrains Mono', monospace;
}
.key-submit-btn {
  background: var(--accent-gradient); border: none; border-radius: var(--radius);
  color: #fff; padding: 8px 14px; cursor: pointer; font-size: 16px;
}
.key-note { font-size: 11px; color: var(--text-muted); margin-top: 6px; }
.key-set-area {
  padding: 10px 16px; font-size: 12px; color: var(--status-pass);
  display: flex; align-items: center; gap: 8px; flex-shrink: 0;
  border-bottom: 1px solid var(--border);
}
.key-set-area a { color: var(--accent-primary); text-decoration: none; }
.suggestions-area { padding: 10px 16px; display: flex; flex-wrap: wrap; gap: 8px; flex-shrink: 0; }
.suggestion-btn {
  background: none; border: 1px solid var(--border); border-radius: var(--radius-pill);
  color: var(--text-secondary); font-size: 11px; padding: 5px 12px; cursor: pointer;
  transition: var(--transition); font-family: inherit;
}
.suggestion-btn:hover { border-color: var(--accent-primary); color: var(--accent-primary); }
.messages-area { flex: 1; overflow-y: auto; padding: 12px 16px; min-height: 120px; }
.message {
  max-width: 85%; margin-bottom: 12px; padding: 10px 14px;
  font-size: 13px; line-height: 1.5; word-break: break-word;
}
.message.user {
  margin-left: auto; background: rgba(79,142,247,0.12);
  border: 1px solid rgba(79,142,247,0.3); color: var(--text-primary);
  border-radius: var(--radius-lg) var(--radius-lg) 4px var(--radius-lg);
}
.message.ai {
  background: var(--surface-hover); border: 1px solid var(--border);
  color: var(--text-secondary);
  border-radius: var(--radius-lg) var(--radius-lg) var(--radius-lg) 4px;
}
.message.error {
  background: rgba(240,79,95,0.08); border: 1px solid rgba(240,79,95,0.3);
  color: var(--status-fail); border-radius: var(--radius);
}
.message.typing { display: flex; gap: 6px; align-items: center; background: var(--surface-hover); border-radius: var(--radius-lg); }
.dot { width: 8px; height: 8px; border-radius: 50%; background: var(--text-muted); animation: bounce 1.2s infinite; }
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce { 0%,80%,100% { transform: scale(0.8); opacity: 0.5; } 40% { transform: scale(1.2); opacity: 1; } }
.input-row {
  display: flex; gap: 10px; padding: 12px 16px; border-top: 1px solid var(--border);
  flex-shrink: 0;
}
.chat-input {
  flex: 1; background: var(--bg-secondary); border: 1px solid var(--border);
  border-radius: var(--radius-pill); padding: 10px 16px; color: var(--text-primary);
  font-size: 13px; font-family: inherit;
}
.chat-input:focus { outline: none; border-color: var(--accent-primary); }
.send-btn {
  background: var(--accent-gradient); border: none; border-radius: var(--radius-pill);
  color: #fff; width: 38px; height: 38px; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; transition: opacity var(--transition);
}
.send-btn:disabled { opacity: 0.4; cursor: not-allowed; }

/* Feature table */
.feature-table-section { margin-bottom: 24px; }
.feature-table-container {
  border-radius: var(--radius-lg); overflow: hidden;
  border: 1px solid var(--border); box-shadow: var(--shadow);
}
.feature-table { width: 100%; border-collapse: collapse; }
.feature-table th {
  background: var(--surface-hover); font-size: 11px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-secondary);
  padding: 12px 16px; text-align: left; border-bottom: 1px solid var(--border);
}
.feature-table td { padding: 12px 16px; border-bottom: 1px solid var(--border-subtle); }
.feature-table tr:last-child td { border-bottom: none; }
.feat-row { cursor: pointer; transition: background var(--transition); }
.feat-row:hover td { background: var(--surface-hover) !important; }
.ft-name { font-weight: 600; color: var(--text-primary); font-size: 14px; }
.ft-num { font-family: 'JetBrains Mono', monospace; text-align: center; }
.ft-dur { font-family: 'JetBrains Mono', monospace; color: var(--text-muted); font-size: 12px; }
.badge { font-size: 10px; font-weight: 700; letter-spacing: 0.06em; border-radius: var(--radius-pill); padding: 3px 8px; }
.badge-pass { color: var(--status-pass); background: rgba(34,201,122,0.1); }
.badge-fail { color: var(--status-fail); background: rgba(240,79,95,0.1); }
.badge-skip { color: var(--status-skip); background: rgba(245,166,35,0.1); }
.tag-badge {
  font-size: 11px; color: var(--accent-secondary); background: rgba(0,203,169,0.1);
  border: 1px solid rgba(0,203,169,0.25); border-radius: var(--radius-pill); padding: 2px 8px;
  font-family: 'JetBrains Mono', monospace;
}

/* CTA */
.cta-row { text-align: center; padding: 16px 0; }
.cta-btn {
  border: 1px solid var(--accent-primary); border-radius: var(--radius-pill);
  color: var(--accent-primary); background: none; font-size: 14px; font-weight: 600;
  padding: 10px 28px; cursor: pointer; transition: var(--transition); font-family: inherit;
}
.cta-btn:hover { background: rgba(79,142,247,0.08); }

/* ── Full Report ── */
.full-report-layout { display: flex; height: calc(100vh - 60px); }
.sidebar {
  width: 260px; flex-shrink: 0; background: var(--bg-secondary);
  border-right: 1px solid var(--border); overflow-y: auto;
  position: sticky; top: 60px; height: calc(100vh - 60px);
}
.sidebar-title {
  padding: 16px 16px 8px; font-size: 10px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-muted);
}
.sf-header {
  display: flex; align-items: center; gap: 8px; padding: 8px 12px;
  cursor: pointer; transition: background var(--transition);
}
.sf-header:hover { background: var(--surface-hover); }
.sf-name { flex: 1; font-size: 13px; font-weight: 500; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sf-count {
  font-size: 10px; font-family: 'JetBrains Mono', monospace; color: var(--text-muted);
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-pill); padding: 1px 6px;
}
.sf-chevron { color: var(--text-muted); flex-shrink: 0; }
.sf-scenario {
  display: flex; align-items: center; gap: 8px; padding: 6px 12px 6px 28px;
  cursor: pointer; transition: background var(--transition);
  border-left: 2px solid transparent;
}
.sf-scenario:hover { background: var(--surface-hover); }
.sf-scenario.active { background: var(--surface-hover); border-left-color: var(--accent-primary); }
.sfs-name { font-size: 12px; font-family: 'JetBrains Mono', monospace; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.detail-main { flex: 1; overflow-y: auto; padding: 32px 40px 32px; max-width: 960px; }
.detail-main-wrap .filter-banner { margin: 16px 40px 0; }
.feat-section { margin-bottom: 48px; }
.feat-heading {
  display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 8px;
}
.feat-title { font-size: 18px; font-weight: 700; color: var(--text-primary); }
.feat-file { font-size: 11px; font-family: 'JetBrains Mono', monospace; color: var(--text-muted); margin-left: auto; }
.feat-desc {
  font-size: 13px; color: var(--text-secondary); font-family: 'JetBrains Mono', monospace;
  line-height: 1.5; margin-bottom: 20px;
}
.scenario-card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-lg); margin-bottom: 16px; overflow: hidden;
  border-left: 3px solid; scroll-margin-top: 76px;
}
.sc-header {
  padding: 16px 20px; display: flex; align-items: center; gap: 12px; cursor: pointer;
  transition: background var(--transition);
}
.sc-header:hover { background: var(--surface-hover); }
.sc-name { flex: 1; font-size: 14px; font-weight: 600; color: var(--text-primary); }
.sc-dur { font-size: 12px; font-family: 'JetBrains Mono', monospace; color: var(--text-muted); display: flex; align-items: center; gap: 4px; }
.sc-chevron { color: var(--text-muted); }
.sc-body { padding: 0 20px 20px; }
.steps-list { margin-top: 4px; }
.step-row { padding: 6px 0; border-top: 1px solid var(--border-subtle); }
.step-row:first-child { border-top: none; }
.step-main {
  display: flex; align-items: center; gap: 10px; padding: 4px 0;
}
.step-kw {
  width: 56px; text-align: right; font-size: 12px; font-weight: 600;
  font-family: 'JetBrains Mono', monospace; flex-shrink: 0;
}
.step-text { flex: 1; font-size: 13px; font-family: 'JetBrains Mono', monospace; }
.call-badge {
  font-size: 10px; font-weight: 700; font-family: 'JetBrains Mono', monospace;
  letter-spacing: 0.06em; border-radius: var(--radius-pill); padding: 2px 7px; border: 1px solid;
}
.call-badge.do { color: var(--accent-primary); background: rgba(79,142,247,0.1); border-color: rgba(79,142,247,0.3); }
.call-badge.check { color: var(--accent-secondary); background: rgba(0,203,169,0.1); border-color: rgba(0,203,169,0.3); }
.step-icon { width: 20px; text-align: center; flex-shrink: 0; }
.step-dur { width: 56px; text-align: right; font-size: 11px; font-family: 'JetBrains Mono', monospace; color: var(--text-muted); flex-shrink: 0; }
.error-block {
  background: rgba(240,79,95,0.06); border: 1px solid rgba(240,79,95,0.2);
  border-radius: var(--radius); padding: 12px 14px; margin: 6px 0 6px 66px;
  color: var(--status-fail); font-size: 12px; font-family: 'JetBrains Mono', monospace;
  white-space: pre-wrap; word-break: break-all; line-height: 1.6; max-height: 220px; overflow-y: auto;
}
.error-type-badge { display:block; font-size:10px; font-weight:600; letter-spacing:.04em;
  padding:2px 6px; border-radius:3px; margin-bottom:8px; width:fit-content;
  background:rgba(240,79,95,0.18); color:var(--status-fail); font-family:inherit; text-transform:uppercase; }
.error-type-badge.assertion { background:rgba(240,79,95,0.08); }
.doc-string {
  background: var(--bg); border-left: 2px solid var(--border); padding: 8px 12px;
  margin: 4px 0 4px 66px; font-size: 12px; font-family: 'JetBrains Mono', monospace;
  color: var(--text-muted); border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}
.table-wrap { margin: 6px 0 6px 66px; overflow-x: auto; }
.step-table { border-collapse: collapse; font-size: 12px; font-family: 'JetBrains Mono', monospace; }
.step-table th, .step-table td { border: 1px solid var(--border); padding: 4px 10px; }
.step-table thead { background: var(--surface-hover); }
.step-thumb-wrap { position: relative; display: inline-flex; align-items: center; margin-left: 6px; flex-shrink: 0; cursor: pointer; }
.step-thumb-img { width: 28px; height: 20px; object-fit: cover; border-radius: 3px; border: 1px solid var(--border); vertical-align: middle; transition: border-color .15s, opacity .15s; display: block; }
.step-thumb-wrap:hover .step-thumb-img { border-color: var(--accent-primary); opacity: .9; }
.step-thumb-popover { display: none; position: absolute; bottom: calc(100% + 8px); right: 0; z-index: 60; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 6px; box-shadow: var(--shadow-lg); width: 320px; pointer-events: none; }
.step-thumb-popover img { width: 100%; border-radius: 4px; display: block; }
.step-thumb-wrap:hover .step-thumb-popover { display: block; }
.screenshot-panel { width: 0; flex-shrink: 0; background: var(--bg-secondary); border-left: 1px solid var(--border); overflow-y: auto; overflow-x: hidden; position: sticky; top: 60px; height: calc(100vh - 60px); transition: width .2s ease; display: flex; flex-direction: column; }
.screenshot-panel.visible { width: 600px; }
.sp-placeholder { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; gap: 10px; color: var(--text-muted); padding: 24px; text-align: center; }
.sp-placeholder-icon { font-size: 32px; opacity: .4; }
.sp-placeholder-text { font-size: 12px; font-family: 'JetBrains Mono', monospace; }
.sp-header { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; border-bottom: 1px solid var(--border); flex-shrink: 0; }
.sp-title { font-size: 12px; font-weight: 600; color: var(--text-primary); }
.sp-close { background: none; border: none; cursor: pointer; color: var(--text-muted); font-size: 16px; line-height: 1; padding: 0 2px; }
.sp-close:hover { color: var(--text-primary); }
.sp-step-text { padding: 8px 16px; font-size: 11px; font-family: 'JetBrains Mono', monospace; color: var(--text-secondary); border-bottom: 1px solid var(--border); line-height: 1.5; flex-shrink: 0; }
.sp-image-wrap { padding: 12px 12px 8px; flex-shrink: 0; }
.sp-image { width: 100%; max-height: calc(100vh - 220px); object-fit: contain; border-radius: 6px; display: block; cursor: zoom-in; border: 1px solid var(--border); transition: opacity .15s; background: var(--bg); }
.sp-image:hover { opacity: .9; }
.sp-nav { display:flex; align-items:center; justify-content:space-between; padding:10px 12px; border-top:1px solid var(--border); flex-shrink:0; gap:8px; min-height:52px; }
.sp-nav-btn { background:none; border:1px solid var(--border); border-radius:var(--radius); color:var(--text-secondary); font-size:12px; padding:5px 12px; cursor:pointer; transition:var(--transition); font-family:inherit; }
.sp-nav-btn:hover:not(:disabled) { border-color:var(--accent-primary); color:var(--accent-primary); }
.sp-nav-btn:disabled { opacity:.35; cursor:not-allowed; }
.sp-dots { display:flex; gap:5px; align-items:center; flex-wrap:wrap; justify-content:center; flex:1; }
.sp-dot { width:7px; height:7px; border-radius:50%; background:var(--border); cursor:pointer; transition:background .15s; flex-shrink:0; }
.sp-dot.active { background:var(--accent-primary); }
.sp-dot:hover:not(.active) { background:var(--text-muted); }

/* AI Panel */
.ai-panel {
  margin: 16px 0 4px; background: var(--surface-hover);
  border: 1px solid rgba(245,166,35,0.25); border-radius: var(--radius);
}
.ai-panel-header {
  display: flex; align-items: center; gap: 10px; padding: 12px 16px;
  cursor: pointer; transition: background var(--transition);
}
.ai-panel-header:hover { background: rgba(245,166,35,0.04); }
.ai-panel-label { font-size: 13px; font-weight: 600; color: var(--ai-accent); flex: 1; display: flex; align-items: center; gap: 6px; }
.sev-badge { font-size: 10px; font-weight: 700; letter-spacing: 0.06em; }
.ai-provider { font-size: 10px; font-family: 'JetBrains Mono', monospace; color: var(--text-muted); }
.ai-chevron { color: var(--text-muted); }
.ai-panel-body { padding: 0 16px 16px; }
.ai-summary {
  border-left: 3px solid var(--ai-accent); background: rgba(245,166,35,0.06);
  padding: 12px 16px; border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  font-size: 14px; font-weight: 600; color: var(--text-primary); margin-bottom: 16px;
}
.ai-section { margin-bottom: 12px; }
.ai-section-label {
  font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em;
  color: var(--ai-accent); opacity: 0.7; display: block; margin-bottom: 4px;
}
.ai-section-val { font-size: 13px; color: var(--text-secondary); line-height: 1.6; }
.ai-unavail { font-size: 12px; color: var(--text-muted); }

.empty-msg { padding: 24px; color: var(--text-muted); text-align: center; }
.sidebar-empty { padding: 16px; color: var(--text-muted); font-size: 13px; }

code { font-family: 'JetBrains Mono', monospace; font-size: 0.9em; }
"""


class ReportGenerator:
    """Writes HTML and JSON report files for a test run."""

    def __init__(self, output_dir: str | Path) -> None:
        """Initialise the generator.

        Args:
            output_dir: Directory where reports are written. Created if missing.
        """
        self._output_dir = Path(output_dir)

    def write(self, run_data: RunData) -> tuple[Path, Path, Path]:
        """Write HTML and JSON reports for the run into a per-run subdirectory.

        Args:
            run_data: The completed run data.

        Returns:
            Tuple of (run_dir, html_path, json_path).
        """
        self._output_dir.mkdir(parents=True, exist_ok=True)
        run_dir = self._output_dir / f"run_{run_data.run_id}"
        run_dir.mkdir(parents=True, exist_ok=True)

        html_path = run_dir / "report.html"
        json_path = run_dir / "report.json"

        json_path.write_text(generate_json(run_data), encoding="utf-8")
        html_path.write_text(generate_html(run_data), encoding="utf-8")

        from .server import _write_launcher_files  # noqa: PLC0415
        _write_launcher_files(run_dir, "report.html")

        return run_dir, html_path, json_path
