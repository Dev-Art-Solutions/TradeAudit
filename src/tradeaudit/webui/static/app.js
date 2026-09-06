// TradeAudit web UI - vanilla JS SPA talking to the FastAPI backend at /api/*.

const NAV = [
  { id: "dashboard", icon: "\u{1F4C8}", label: "Dashboard" },
  { id: "trades", icon: "\u{1F4CA}", label: "Trades" },
  { id: "strategies", icon: "\u{1F3AF}", label: "Strategies" },
  { id: "strategy-vs-trader", icon: "\u2696\uFE0F", label: "Strategy vs Trader" },
  { id: "breakdowns", icon: "\u{1F50D}", label: "Breakdowns" },
  { id: "live-journal", icon: "\u{1F4DD}", label: "Live Journal" },
  { id: "reports", icon: "\u{1F4C4}", label: "AI Reports" },
  { id: "quant", icon: "\u{1F52C}", label: "Quant & Risk" },
  { id: "trade-chart", icon: "\u{1F56F}\uFE0F", label: "Trade Chart" },
  { id: "settings", icon: "\u2699\uFE0F", label: "MT5 Settings" },
];

const PAGE_SUB = {
  dashboard: "Performance overview and equity curve",
  trades: "Aggregated trade history synced from MT5",
  strategies: "Define and manage execution rules",
  "strategy-vs-trader": "Four-quadrant discipline analysis",
  breakdowns: "Symbol, session, weekday and streak analytics",
  "live-journal": "Real-time open position monitor",
  reports: "Markdown & AI-ready export",
  quant: "Monte Carlo, Risk of Ruin & rolling metrics",
  "trade-chart": "Candlestick replay for a selected trade",
  settings: "MetaTrader 5 connection & storage",
};

let state = { route: "dashboard", trades: [], strategies: [], api: null, hasAccount: false };

function onboardingBannerHtml() {
  if (state.hasAccount) return "";
  return `
    <div class="onboarding-banner">
      <div>
        <div class="ob-title">\u{1F44B} Get started with TradeAudit</div>
        <div class="ob-sub">No MT5 account configured yet.</div>
        <div class="ob-steps">
          <b>1.</b> Open <b>MT5 Settings</b> ·
          <b>2.</b> Enter the Login, Server and Password from your MetaTrader 5 terminal (Tools → Options → Server, or ask your broker) ·
          <b>3.</b> Click <b>Connect</b>, then <b>Sync History</b> on the Trades tab.
        </div>
      </div>
      <button class="btn btn-primary" onclick="navigate('settings')">Open Settings</button>
    </div>`;
}

async function api(path, opts) {
  const res = await fetch("/api" + path, {
    headers: {
      "Content-Type": "application/json",
      "X-TradeAudit-Token": window.__TA_TOKEN__ || "",
    },
    ...opts,
  });
  let body = null;
  try { body = await res.json(); } catch (e) { /* no body */ }
  if (!res.ok) {
    const detail = (body && body.detail) ? body.detail : res.statusText;
    throw new Error(detail);
  }
  return body;
}
const apiGet = (p) => api(p);
const apiPost = (p, data) => api(p, { method: "POST", body: JSON.stringify(data || {}) });
const apiPut = (p, data) => api(p, { method: "PUT", body: JSON.stringify(data || {}) });
const apiDelete = (p) => api(p, { method: "DELETE" });

function fmtNum(v, digits = 2) {
  if (v === null || v === undefined || Number.isNaN(v)) return "\u2014";
  return Number(v).toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });
}
function fmtVolume(v) {
  if (v === null || v === undefined || Number.isNaN(v)) return "\u2014";
  // Lot sizes can be fractional down to micro-lots (0.001) - never truncate to 0.00.
  return Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 3 });
}
function fmtPct(v, digits = 1) {
  if (v === null || v === undefined) return "\u2014";
  return (Number(v) * 100).toFixed(digits) + "%";
}
function fmtDate(iso) {
  if (!iso) return "\u2014";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "\u2014";
  return d.toLocaleString(undefined, { year: "numeric", month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}
function signClass(v) { return (v || 0) >= 0 ? "text-win" : "text-loss"; }
function esc(s) { return (s ?? "").toString().replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }

function renderNav() {
  const nav = document.getElementById("nav");
  nav.innerHTML = NAV.map(
    (n) => `<div class="nav-item ${n.id === state.route ? "active" : ""}" data-route="${n.id}">
      <span class="icon">${n.icon}</span><span>${n.label}</span>
    </div>`
  ).join("");
  nav.querySelectorAll(".nav-item").forEach((el) => {
    el.addEventListener("click", () => navigate(el.dataset.route));
  });
}

function navigate(route) {
  if (location.hash.slice(1) === route) { syncFromHash(); return; }
  location.hash = route; // triggers hashchange -> syncFromHash()
}

async function refreshStatus() {
  try {
    const s = await apiGet("/state");
    state.hasAccount = !!(s.settings && s.settings.login);
    document.getElementById("version-footer").textContent = `${s.app_name} v${s.app_version}`;
    const badge = document.getElementById("status-badge");
    const text = document.getElementById("status-text");
    badge.className = "status-badge";
    if (s.connection_state === "CONNECTED") {
      badge.classList.add("connected");
      text.textContent = s.account ? `Connected \u00b7 ${s.account.login} (${s.account.server})` : "Connected";
    } else if (s.connection_state === "CONNECTING") {
      badge.classList.add("connecting");
      text.textContent = "Connecting\u2026";
    } else if (s.connection_state === "ERROR") {
      badge.classList.add("error");
      text.textContent = s.last_error || "Connection error";
    } else {
      text.textContent = "Disconnected";
    }
    return s;
  } catch (e) {
    return null;
  }
}

function content() { return document.getElementById("content"); }

function emptyState(icon, title, sub) {
  return `<div class="empty-state"><div class="icon">${icon}</div><div class="title">${esc(title)}</div><div class="sub">${esc(sub)}</div></div>`;
}

// ------------------------------------------------------------------ charts

function drawLineChart(canvas, series, opts = {}) {
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth, h = canvas.clientHeight;
  canvas.width = w * dpr; canvas.height = h * dpr;
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, w, h);
  if (!series || series.length < 2) {
    ctx.fillStyle = "#6e7681";
    ctx.font = "12px Segoe UI";
    ctx.fillText("Not enough data yet", 12, h / 2);
    return;
  }
  const pad = 8;
  const min = Math.min(...series, 0);
  const max = Math.max(...series, 0);
  const range = (max - min) || 1;
  const zeroY = h - pad - ((0 - min) / range) * (h - pad * 2);

  ctx.strokeStyle = "#21262d";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(0, zeroY);
  ctx.lineTo(w, zeroY);
  ctx.stroke();

  ctx.beginPath();
  ctx.strokeStyle = opts.color || "#58a6ff";
  ctx.lineWidth = 2;
  series.forEach((v, i) => {
    const x = (i / (series.length - 1)) * w;
    const y = h - pad - ((v - min) / range) * (h - pad * 2);
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  });
  ctx.stroke();

  const last = series[series.length - 1];
  const lx = w, ly = h - pad - ((last - min) / range) * (h - pad * 2);
  ctx.fillStyle = opts.color || "#58a6ff";
  ctx.beginPath();
  ctx.arc(lx - 4, ly, 3, 0, Math.PI * 2);
  ctx.fill();
}

// ------------------------------------------------------------------ dashboard

async function viewDashboard() {
  content().innerHTML = `<div id="dash-body">Loading\u2026</div>`;
  let data;
  try { data = await apiGet("/dashboard"); } catch (e) {
    content().innerHTML = emptyState("\u26A0\uFE0F", "Could not load dashboard", e.message);
    return;
  }
  const m = data.metrics;
  if (!m.total_trades) {
    content().innerHTML = onboardingBannerHtml() +
      emptyState("\u{1F4C8}", "No trades yet", "Connect your MT5 account and run a sync from the Trades tab to see performance analytics here.");
    return;
  }
  content().innerHTML = `
    <div class="grid grid-4">
      <div class="kpi"><div class="kpi-label">Win Rate</div><div class="kpi-value">${fmtPct(m.win_rate)}</div><div class="kpi-sub">${m.winning_trades}W / ${m.losing_trades}L / ${m.breakeven_trades}BE</div></div>
      <div class="kpi"><div class="kpi-label">Net Profit</div><div class="kpi-value ${m.net_profit >= 0 ? "win" : "loss"}">${fmtNum(m.net_profit)}</div><div class="kpi-sub">${m.total_trades} total trades</div></div>
      <div class="kpi"><div class="kpi-label">Expectancy (R)</div><div class="kpi-value ${m.expectancy_r >= 0 ? "win" : "loss"}">${fmtNum(m.expectancy_r, 3)}</div><div class="kpi-sub">${m.trades_with_r} trades with known R</div></div>
      <div class="kpi"><div class="kpi-label">Profit Factor</div><div class="kpi-value">${m.profit_factor === null ? "\u221E" : fmtNum(m.profit_factor)}</div><div class="kpi-sub">Verdict: ${m.verdict.replace(/_/g, " ")}</div></div>
    </div>
    <div class="two-col" style="margin-top:16px">
      <div class="card">
        <div class="card-title">Cumulative R</div>
        <canvas class="chart-canvas" id="chart-r"></canvas>
      </div>
      <div class="card">
        <div class="card-title">Cumulative P/L</div>
        <canvas class="chart-canvas" id="chart-money"></canvas>
      </div>
    </div>
    <div class="grid grid-3" style="margin-top:16px">
      <div class="card"><div class="card-title">Max Drawdown</div>
        <div class="kpi-value loss">${fmtNum(m.max_drawdown_r, 2)} R</div>
        <div class="kpi-sub">${fmtNum(m.max_drawdown_monetary)} monetary</div></div>
      <div class="card"><div class="card-title">Avg Win / Loss (R)</div>
        <div class="kpi-value win">${fmtNum(m.avg_win_r, 3)}</div>
        <div class="kpi-value loss">${fmtNum(m.avg_loss_r, 3)}</div></div>
      <div class="card"><div class="card-title">Streaks</div>
        <div class="kpi-sub">Max consecutive wins</div><div class="kpi-value win">${m.max_consecutive_wins}</div>
        <div class="kpi-sub" style="margin-top:8px">Max consecutive losses</div><div class="kpi-value loss">${m.max_consecutive_losses}</div></div>
    </div>
  `;
  drawLineChart(document.getElementById("chart-r"), m.cumulative_r_series, { color: "#58a6ff" });
  drawLineChart(document.getElementById("chart-money"), m.cumulative_monetary_series, { color: "#26a69a" });
}

// ------------------------------------------------------------------ trades

async function viewTrades() {
  content().innerHTML = `
    ${onboardingBannerHtml()}
    <div class="toolbar">
      <div class="chip" id="trades-count-chip">Loading…</div>
      <div class="right">
        <button class="btn btn-primary" id="btn-sync"><span id="sync-spinner"></span> Sync History</button>
      </div>
    </div>
    <div id="trades-body"></div>
  `;
  document.getElementById("btn-sync").addEventListener("click", doSync);
  await loadTrades();
  renderTradesTable();
}

function updateTradesCountChip() {
  const chip = document.getElementById("trades-count-chip");
  if (chip) chip.textContent = `${state.trades.length} trades loaded`;
}

async function loadTrades() {
  try { state.trades = await apiGet("/trades"); } catch (e) { state.trades = []; }
}

function renderTradesTable() {
  const body = document.getElementById("trades-body");
  if (!body) return;
  updateTradesCountChip();
  if (!state.trades.length) {
    body.innerHTML = emptyState("\u{1F4CA}", "No trades synced yet", "Configure your MT5 account in Settings, connect, then click Sync History above.");
    return;
  }
  const rows = state.trades.slice().sort((a, b) => new Date(b.open_time) - new Date(a.open_time)).map((t) => `
    <tr>
      <td>${esc(t.symbol)}</td>
      <td><span class="pill ${t.direction === "BUY" ? "buy" : "sell"}">${t.direction}</span></td>
      <td class="mono">${fmtVolume(t.volume)}</td>
      <td class="mono">${fmtDate(t.open_time)}</td>
      <td class="mono">${fmtDate(t.close_time)}</td>
      <td class="mono">${fmtNum(t.open_price, 5)}</td>
      <td class="mono">${t.close_price !== null ? fmtNum(t.close_price, 5) : "\u2014"}</td>
      <td class="mono ${signClass(t.net_profit ?? t.profit)}">${fmtNum(t.profit)}</td>
      <td class="mono">${t.realized_r !== null ? fmtNum(t.realized_r, 2) : "\u2014"}</td>
      <td><span class="pill ${(t.compliance_status || "unchecked").toLowerCase()}">${t.compliance_status || "UNCHECKED"}</span></td>
    </tr>`).join("");
  body.innerHTML = `
    <div class="table-wrap">
      <table>
        <thead><tr>
          <th>Symbol</th><th>Dir</th><th>Volume</th><th>Open Time</th><th>Close Time</th>
          <th>Open Px</th><th>Close Px</th><th>P/L</th><th>R</th><th>Compliance</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

async function doSync() {
  const btn = document.getElementById("btn-sync");
  const spinner = document.getElementById("sync-spinner");
  btn.disabled = true;
  if (spinner) spinner.className = "spinner";
  try {
    const result = await apiPost("/sync", {});
    await loadTrades();
    renderTradesTable();
    showTransientBanner(result.message || "Sync complete", true);
  } catch (e) {
    showTransientBanner(e.message, false);
  } finally {
    btn.disabled = false;
    if (spinner) spinner.className = "";
  }
}

function showTransientBanner(message, ok) {
  const existing = document.getElementById("transient-banner");
  if (existing) existing.remove();
  const el = document.createElement("div");
  el.id = "transient-banner";
  el.className = "banner " + (ok ? "success" : "error");
  el.style.position = "fixed";
  el.style.bottom = "20px";
  el.style.right = "20px";
  el.style.zIndex = "999";
  el.style.maxWidth = "420px";
  el.textContent = message;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 6000);
}

// ------------------------------------------------------------------ settings

async function viewSettings() {
  let s;
  try { s = await apiGet("/state"); } catch (e) { s = null; }
  const settings = (s && s.settings) || { mt5_path: "", login: 0, server: "", timeout_ms: 60000 };
  const connected = s && s.connection_state === "CONNECTED";

  content().innerHTML = `
    <div class="card">
      <div class="card-title">\u2699\uFE0F MetaTrader 5 Terminal Configuration</div>
      <div class="kpi-sub" style="margin-bottom:16px">
        Find your Login, Server and Password inside your MT5 terminal:
        open it, go to <b>Tools \u2192 Options \u2192 Server</b>, or check the account
        details your broker emailed you when you opened the account. A demo
        account works exactly the same way as a live one for this app.
      </div>
      <div class="field">
        <label>MT5 Terminal Path <span class="text-dim">(optional \u2014 leave blank to use the last-used terminal)</span></label>
        <div class="input-row">
          <input type="text" id="f-path" placeholder="C:\\Program Files\\MetaTrader 5\\terminal64.exe" value="${esc(settings.mt5_path)}" />
          <button type="button" class="btn" id="btn-browse-path">Browse\u2026</button>
        </div>
      </div>
      <div class="grid grid-2">
        <div class="field">
          <label>Account Login</label>
          <input type="text" inputmode="numeric" pattern="[0-9]*" id="f-login" placeholder="e.g. 50195" value="${settings.login || ""}" />
        </div>
        <div class="field">
          <label>Server</label>
          <input type="text" id="f-server" placeholder="e.g. MetaQuotes-Demo" value="${esc(settings.server)}" />
        </div>
      </div>
      <div class="grid grid-2">
        <div class="field">
          <label>Password</label>
          <input type="password" id="f-password" placeholder="Stored securely in OS Credential Locker" />
        </div>
        <div class="field">
          <label>Timeout (ms)</label>
          <input type="text" inputmode="numeric" id="f-timeout" value="${settings.timeout_ms || 60000}" />
        </div>
      </div>
      <div id="settings-banner" class="banner hidden"></div>
      <div class="btn-row">
        <button class="btn" id="btn-save">\u{1F4BE} Save Settings</button>
        <button class="btn btn-success" id="btn-connect">\u26A1 Connect to MT5</button>
        <button class="btn btn-danger" id="btn-disconnect" ${connected ? "" : "disabled"}>\u{1F50C} Disconnect</button>
      </div>
    </div>

    <div class="card">
      <div class="card-title">\u{1F4E6} Storage & Database Backups</div>
      <div class="kpi-sub" style="margin-bottom:14px">
        Data Directory: <span class="mono">${esc(s ? s.storage.data_dir : "")}</span><br/>
        Database: <span class="mono">${esc(s ? s.storage.database_url : "")}</span>
      </div>
      <div class="btn-row" style="margin-top:0">
        <button class="btn" id="btn-backup">\u{1F4BE} Create Backup Now</button>
      </div>
    </div>

    <div class="card">
      <div class="card-title">\u{1F6E0}️ Diagnostics</div>
      <div class="kpi-sub" style="margin-bottom:14px">
        Something not working? Show the recent log and copy it into a support message or bug report.
      </div>
      <div class="btn-row" style="margin-top:0">
        <button class="btn" id="btn-show-log">View Recent Log</button>
        <button class="btn" id="btn-copy-log" style="display:none">Copy to Clipboard</button>
      </div>
      <div id="log-box" class="markdown-box" style="display:none;margin-top:14px;max-height:320px"></div>
    </div>
  `;

  function readForm() {
    return {
      mt5_path: document.getElementById("f-path").value.trim(),
      login: parseInt(document.getElementById("f-login").value.trim() || "0", 10) || 0,
      server: document.getElementById("f-server").value.trim(),
      timeout_ms: parseInt(document.getElementById("f-timeout").value.trim() || "60000", 10) || 60000,
    };
  }
  function banner(msg, ok) {
    const el = document.getElementById("settings-banner");
    el.textContent = msg;
    el.className = "banner " + (ok ? "success" : "error");
  }

  document.getElementById("btn-save").addEventListener("click", async () => {
    try { await apiPost("/settings", readForm()); banner("\u2705 Settings saved successfully.", true); }
    catch (e) { banner("\u274C " + e.message, false); }
  });

  document.getElementById("btn-browse-path").addEventListener("click", async () => {
    if (!(window.pywebview && window.pywebview.api)) {
      banner("\u26A0\uFE0F File browsing only works inside the TradeAudit desktop app, not a plain browser tab.", false);
      return;
    }
    try {
      const path = await window.pywebview.api.browse_mt5_path();
      if (path) document.getElementById("f-path").value = path;
    } catch (e) {
      banner("\u274C Could not open file picker: " + e.message, false);
    }
  });

  document.getElementById("btn-connect").addEventListener("click", async () => {
    const btn = document.getElementById("btn-connect");
    btn.disabled = true;
    try {
      const payload = { ...readForm(), password: document.getElementById("f-password").value };
      const res = await apiPost("/connect", payload);
      banner(`\u2705 Connected! Account: ${res.account.login} (${res.account.name}) \u00b7 Balance: ${fmtNum(res.account.balance)} ${res.account.currency}`, true);
      await refreshStatus();
      document.getElementById("btn-disconnect").disabled = false;
    } catch (e) {
      banner("\u274C Connection failed: " + e.message, false);
      await refreshStatus();
    } finally {
      btn.disabled = false;
    }
  });

  document.getElementById("btn-disconnect").addEventListener("click", async () => {
    await apiPost("/disconnect", {});
    banner("\u{1F50C} Disconnected from MT5 terminal.", true);
    await refreshStatus();
    document.getElementById("btn-disconnect").disabled = true;
  });

  document.getElementById("btn-backup").addEventListener("click", async () => {
    try {
      const res = await apiPost("/backup", {});
      showTransientBanner("Backup created: " + res.path, true);
    } catch (e) { showTransientBanner(e.message, false); }
  });

  document.getElementById("btn-show-log").addEventListener("click", async () => {
    const box = document.getElementById("log-box");
    const copyBtn = document.getElementById("btn-copy-log");
    try {
      const res = await apiGet("/logs/recent?lines=300");
      box.textContent = res.lines.length ? res.lines.join("\n") : `(no log entries yet at ${res.path})`;
      box.style.display = "block";
      copyBtn.style.display = "inline-flex";
    } catch (e) {
      showTransientBanner(e.message, false);
    }
  });

  document.getElementById("btn-copy-log").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(document.getElementById("log-box").textContent);
      showTransientBanner("Log copied to clipboard.", true);
    } catch (e) {
      showTransientBanner("Could not copy automatically - select the text manually.", false);
    }
  });
}

// ------------------------------------------------------------------ strategies

async function viewStrategies() {
  try { state.strategies = await apiGet("/strategies"); } catch (e) { state.strategies = []; }
  content().innerHTML = `
    <div class="two-col">
      <div class="card">
        <div class="card-title">Strategies</div>
        <div id="strategy-list"></div>
      </div>
      <div class="card">
        <div class="card-title" id="form-title">New Strategy</div>
        <div class="field"><label>Name</label><input type="text" id="s-name" /></div>
        <div class="field"><label>Description</label><textarea id="s-desc" rows="2"></textarea></div>
        <div class="grid grid-2">
          <div class="field"><label>Min R:R</label><input type="text" id="s-minrr" /></div>
          <div class="field"><label>Max Risk %</label><input type="text" id="s-maxrisk" /></div>
        </div>
        <div class="grid grid-2">
          <div class="field"><label>Max Trades / Day</label><input type="text" id="s-maxtrades" /></div>
          <div class="field"><label>Allowed Direction</label>
            <select id="s-direction"><option value="ALL">ALL</option><option value="BUY">BUY</option><option value="SELL">SELL</option></select>
          </div>
        </div>
        <div class="checkbox-row" style="margin-bottom:10px"><input type="checkbox" id="s-reqsl" /><label>Requires Stop Loss</label></div>
        <div class="checkbox-row" style="margin-bottom:16px"><input type="checkbox" id="s-reqtp" /><label>Requires Take Profit</label></div>
        <input type="hidden" id="s-id" />
        <div class="btn-row">
          <button class="btn btn-primary" id="btn-save-strategy">Save Strategy</button>
          <button class="btn" id="btn-clear-strategy">Clear</button>
        </div>
      </div>
    </div>
  `;
  renderStrategyList();
  document.getElementById("btn-clear-strategy").addEventListener("click", clearStrategyForm);
  document.getElementById("btn-save-strategy").addEventListener("click", saveStrategyForm);
}

function renderStrategyList() {
  const el = document.getElementById("strategy-list");
  if (!state.strategies.length) {
    el.innerHTML = emptyState("\u{1F3AF}", "No strategies yet", "Create one on the right to start tracking rule compliance.");
    return;
  }
  el.innerHTML = state.strategies.map((s) => `
    <div class="card" style="padding:14px;margin-bottom:10px">
      <div style="display:flex;justify-content:space-between;align-items:start">
        <div>
          <strong>${esc(s.name)}</strong>
          <div class="kpi-sub">${esc(s.description || "")}</div>
          <div class="kpi-sub" style="margin-top:6px">Min R:R ${s.min_rr ?? "\u2014"} \u00b7 Max Risk ${s.max_risk_pct ?? "\u2014"}% \u00b7 ${s.allowed_direction}</div>
        </div>
        <div class="btn-row" style="margin-top:0">
          <button class="btn" data-edit="${s.id}">Edit</button>
          <button class="btn btn-danger" data-del="${s.id}">Delete</button>
        </div>
      </div>
    </div>`).join("");
  el.querySelectorAll("[data-edit]").forEach((b) => b.addEventListener("click", () => fillStrategyForm(b.dataset.edit)));
  el.querySelectorAll("[data-del]").forEach((b) => b.addEventListener("click", () => deleteStrategy(b.dataset.del)));
}

function clearStrategyForm() {
  document.getElementById("form-title").textContent = "New Strategy";
  ["s-id"].forEach((id) => document.getElementById(id).value = "");
  document.getElementById("s-name").value = "";
  document.getElementById("s-desc").value = "";
  document.getElementById("s-minrr").value = "";
  document.getElementById("s-maxrisk").value = "";
  document.getElementById("s-maxtrades").value = "";
  document.getElementById("s-direction").value = "ALL";
  document.getElementById("s-reqsl").checked = false;
  document.getElementById("s-reqtp").checked = false;
}

function fillStrategyForm(id) {
  const s = state.strategies.find((x) => String(x.id) === String(id));
  if (!s) return;
  document.getElementById("form-title").textContent = "Edit Strategy #" + s.id;
  document.getElementById("s-id").value = s.id;
  document.getElementById("s-name").value = s.name;
  document.getElementById("s-desc").value = s.description || "";
  document.getElementById("s-minrr").value = s.min_rr ?? "";
  document.getElementById("s-maxrisk").value = s.max_risk_pct ?? "";
  document.getElementById("s-maxtrades").value = s.max_trades_per_day ?? "";
  document.getElementById("s-direction").value = s.allowed_direction || "ALL";
  document.getElementById("s-reqsl").checked = !!s.requires_sl;
  document.getElementById("s-reqtp").checked = !!s.requires_tp;
}

async function saveStrategyForm() {
  const id = document.getElementById("s-id").value;
  const payload = {
    name: document.getElementById("s-name").value.trim(),
    description: document.getElementById("s-desc").value.trim(),
    allowed_symbols: [],
    allowed_sessions: [],
    min_rr: document.getElementById("s-minrr").value ? parseFloat(document.getElementById("s-minrr").value) : null,
    max_risk_pct: document.getElementById("s-maxrisk").value ? parseFloat(document.getElementById("s-maxrisk").value) : null,
    max_trades_per_day: document.getElementById("s-maxtrades").value ? parseInt(document.getElementById("s-maxtrades").value, 10) : null,
    requires_sl: document.getElementById("s-reqsl").checked,
    requires_tp: document.getElementById("s-reqtp").checked,
    allowed_direction: document.getElementById("s-direction").value,
    is_active: true,
  };
  try {
    if (id) await apiPut("/strategies/" + id, payload); else await apiPost("/strategies", payload);
    state.strategies = await apiGet("/strategies");
    renderStrategyList();
    clearStrategyForm();
    showTransientBanner("Strategy saved.", true);
  } catch (e) { showTransientBanner(e.message, false); }
}

async function deleteStrategy(id) {
  try {
    await apiDelete("/strategies/" + id);
    state.strategies = await apiGet("/strategies");
    renderStrategyList();
  } catch (e) { showTransientBanner(e.message, false); }
}

// ------------------------------------------------------------------ strategy vs trader

async function viewStrategyVsTrader() {
  content().innerHTML = `<div id="svt-body">Loading\u2026</div>`;
  let c;
  try { c = await apiGet("/strategy-vs-trader"); } catch (e) {
    content().innerHTML = emptyState("\u26A0\uFE0F", "Could not load", e.message); return;
  }
  if (!c.total_performance.total_trades) {
    content().innerHTML = emptyState("\u2696\uFE0F", "No data yet", "Sync trades and assign strategies to see the compliance quadrant.");
    return;
  }
  const q = c.four_quadrants;
  content().innerHTML = `
    <div class="grid grid-4">
      <div class="kpi"><div class="kpi-label">Good Wins</div><div class="kpi-value win">${q.good_wins_count}</div><div class="kpi-sub">${fmtNum(q.good_wins_net_r, 2)} R</div></div>
      <div class="kpi"><div class="kpi-label">Good Losses</div><div class="kpi-value">${q.good_losses_count}</div><div class="kpi-sub">${fmtNum(q.good_losses_net_r, 2)} R</div></div>
      <div class="kpi"><div class="kpi-label">Bad Wins</div><div class="kpi-value">${q.bad_wins_count}</div><div class="kpi-sub">${fmtNum(q.bad_wins_net_r, 2)} R</div></div>
      <div class="kpi"><div class="kpi-label">Bad Losses</div><div class="kpi-value loss">${q.bad_losses_count}</div><div class="kpi-sub">${fmtNum(q.bad_losses_net_r, 2)} R</div></div>
    </div>
    <div class="card" style="margin-top:16px">
      <div class="card-title">Deviation Cost</div>
      <div class="grid grid-2">
        <div><div class="kpi-label">Cost in R</div><div class="kpi-value loss">${fmtNum(c.deviation_cost_r, 2)}</div></div>
        <div><div class="kpi-label">Cost Monetary</div><div class="kpi-value loss">${fmtNum(c.deviation_cost_monetary)}</div></div>
      </div>
      <div class="kpi-sub" style="margin-top:12px">Quality verdict: ${esc(c.quality_verdict)}</div>
    </div>
    ${perfRow("Compliant", c.compliant_performance)}
    ${perfRow("Deviation", c.deviation_performance)}
  `;
}

function perfRow(label, m) {
  if (!m || !m.total_trades) return "";
  return `<div class="card"><div class="card-title">${label} Trades (${m.total_trades})</div>
    <div class="grid grid-3">
      <div><div class="kpi-label">Win Rate</div><div class="kpi-value">${fmtPct(m.win_rate)}</div></div>
      <div><div class="kpi-label">Expectancy R</div><div class="kpi-value ${m.expectancy_r >= 0 ? "win" : "loss"}">${fmtNum(m.expectancy_r, 3)}</div></div>
      <div><div class="kpi-label">Net Profit</div><div class="kpi-value ${m.net_profit >= 0 ? "win" : "loss"}">${fmtNum(m.net_profit)}</div></div>
    </div></div>`;
}

// ------------------------------------------------------------------ breakdowns

async function viewBreakdowns() {
  content().innerHTML = `<div id="bd-body">Loading\u2026</div>`;
  let b;
  try { b = await apiGet("/breakdown"); } catch (e) {
    content().innerHTML = emptyState("\u26A0\uFE0F", "Could not load", e.message); return;
  }
  const dims = [
    ["By Symbol", b.by_symbol], ["By Direction", b.by_direction], ["By Session", b.by_session],
    ["By Weekday", b.by_weekday], ["By Hour", b.by_hour], ["By Emotion", b.by_emotion],
  ];
  const nonEmpty = dims.filter(([, d]) => d && Object.keys(d).length);
  if (!nonEmpty.length) {
    content().innerHTML = emptyState("\u{1F50D}", "No data yet", "Sync trades to see multi-dimensional breakdowns.");
    return;
  }
  content().innerHTML = nonEmpty.map(([title, dict]) => breakdownTable(title, dict)).join("");
}

function breakdownTable(title, dict) {
  const rows = Object.entries(dict).map(([key, m]) => `
    <tr>
      <td>${esc(String(key))}</td>
      <td class="mono">${m.total_trades}</td>
      <td class="mono">${fmtPct(m.win_rate)}</td>
      <td class="mono ${m.expectancy_r >= 0 ? "text-win" : "text-loss"}">${fmtNum(m.expectancy_r, 3)}</td>
      <td class="mono ${m.net_profit >= 0 ? "text-win" : "text-loss"}">${fmtNum(m.net_profit)}</td>
    </tr>`).join("");
  return `<div class="card">
    <div class="card-title">${title}</div>
    <div class="table-wrap" style="max-height:260px">
      <table><thead><tr><th></th><th>Trades</th><th>Win Rate</th><th>Expectancy R</th><th>Net P/L</th></tr></thead>
      <tbody>${rows}</tbody></table>
    </div></div>`;
}

// ------------------------------------------------------------------ live journal

async function viewLiveJournal() {
  content().innerHTML = `
    <div class="toolbar"><div id="lj-status" class="chip">Idle</div>
      <div class="right"><button class="btn btn-primary" id="btn-poll">\u{1F504} Poll Positions</button></div>
    </div>
    <div id="lj-body"></div>
  `;
  document.getElementById("btn-poll").addEventListener("click", pollLiveJournal);
  await pollLiveJournal();
}

async function pollLiveJournal() {
  let data;
  try { data = await apiGet("/live-journal/positions"); } catch (e) {
    document.getElementById("lj-body").innerHTML = emptyState("\u26A0\uFE0F", "Could not load", e.message); return;
  }
  document.getElementById("lj-status").textContent = data.status;
  const body = document.getElementById("lj-body");
  if (!data.positions.length) {
    body.innerHTML = emptyState("\u{1F4DD}", "No open positions", "Connect MT5 and poll to see live positions here.");
    return;
  }
  const rows = data.positions.map((p) => `
    <tr>
      <td>${esc(p.symbol)}</td><td><span class="pill ${p.type === "BUY" ? "buy" : "sell"}">${p.type}</span></td>
      <td class="mono">${fmtVolume(p.volume)}</td><td class="mono">${fmtNum(p.price_open, 5)}</td>
      <td class="mono">${fmtNum(p.sl, 5)}</td><td class="mono">${fmtNum(p.tp, 5)}</td>
      <td class="mono ${signClass(p.profit)}">${fmtNum(p.profit)}</td>
    </tr>`).join("");
  body.innerHTML = `<div class="table-wrap"><table><thead><tr>
    <th>Symbol</th><th>Dir</th><th>Volume</th><th>Open Px</th><th>SL</th><th>TP</th><th>P/L</th>
  </tr></thead><tbody>${rows}</tbody></table></div>`;
}

// ------------------------------------------------------------------ reports

async function viewReports() {
  content().innerHTML = `
    <div class="toolbar"><div></div><div class="right"><button class="btn btn-primary" id="btn-gen-report">Generate Report</button></div></div>
    <div class="card"><div class="markdown-box" id="report-box">Click "Generate Report" to build a Markdown / AI-ready audit dossier from your synced trades.</div></div>
  `;
  document.getElementById("btn-gen-report").addEventListener("click", async () => {
    document.getElementById("report-box").textContent = "Generating\u2026";
    try {
      const res = await apiGet("/report");
      document.getElementById("report-box").textContent = res.markdown;
    } catch (e) {
      document.getElementById("report-box").textContent = "Error: " + e.message;
    }
  });
}

// ------------------------------------------------------------------ quant

async function viewQuant() {
  content().innerHTML = `<div id="quant-body">Loading\u2026</div>`;
  let q;
  try { q = await apiGet("/quant"); } catch (e) {
    content().innerHTML = emptyState("\u26A0\uFE0F", "Could not load", e.message); return;
  }
  if (!q.trades_with_r_count) {
    content().innerHTML = emptyState("\u{1F52C}", "Not enough data", "Quant research needs closed trades with a known R-multiple.");
    return;
  }
  const mc = q.monte_carlo, ror = q.risk_of_ruin;
  content().innerHTML = `
    <div class="grid grid-3">
      <div class="kpi"><div class="kpi-label">Median Final R</div><div class="kpi-value">${fmtNum(mc.final_r_median, 2)}</div></div>
      <div class="kpi"><div class="kpi-label">5th / 95th Percentile</div><div class="kpi-value">${fmtNum(mc.final_r_5th, 1)} / ${fmtNum(mc.final_r_95th, 1)}</div></div>
      <div class="kpi"><div class="kpi-label">Median Max Drawdown</div><div class="kpi-value loss">${fmtNum(mc.max_drawdown_median, 2)} R</div></div>
    </div>
    <div class="card" style="margin-top:16px">
      <div class="card-title">Risk of Ruin</div>
      <div class="grid grid-3">
        <div><div class="kpi-label">Risk Level</div><div class="kpi-value">${esc(ror.risk_level.replace(/_/g, " "))}</div></div>
        <div><div class="kpi-label">Empirical Probability</div><div class="kpi-value">${fmtNum(ror.empirical_ruin_probability, 1)}%</div></div>
        <div><div class="kpi-label">Formulaic Probability</div><div class="kpi-value">${fmtNum(ror.formulaic_ruin_probability, 1)}%</div></div>
      </div>
      <div class="kpi-sub" style="margin-top:12px">${esc(ror.summary_verdict)}</div>
    </div>
    ${renderRollingTable(q.rolling_analytics)}
  `;
}

function renderRollingTable(rolling) {
  const windows = Object.keys(rolling || {});
  if (!windows.length) return "";
  const rows = windows.map((w) => {
    const r = rolling[w];
    return `<tr><td class="mono">${w}</td><td class="mono">${fmtNum(r.stability_score, 2)}</td><td>${esc(r.edge_stability_verdict)}</td><td>${esc(r.current_expectancy_trend)}</td></tr>`;
  }).join("");
  return `<div class="card"><div class="card-title">Rolling Window Stability</div>
    <div class="table-wrap" style="max-height:220px"><table><thead><tr><th>Window</th><th>Stability Score</th><th>Verdict</th><th>Trend</th></tr></thead>
    <tbody>${rows}</tbody></table></div></div>`;
}

// ------------------------------------------------------------------ trade chart

// TC holds all Trade Chart tab state: loaded data, replay playback, and the
// pixel<->price/time mapping from the last draw (needed for click-to-annotate).
const TC = {
  tradeId: null, candles: [], overlay: null, annotations: [],
  visibleCount: 0, playing: false, timer: null, speed: 1,
  drawMode: null, pendingPoint: null, geom: null,
};

const DRAW_TOOLS = [
  { type: "TREND_LINE", label: "\u{1F4C8} Trendline" },
  { type: "HORIZONTAL_RAY", label: "\u2796 H-Ray" },
  { type: "TEXT_NOTE", label: "\u{1F4DD} Note" },
];

async function viewTradeChart() {
  await loadTrades();
  const options = state.trades
    .slice().sort((a, b) => new Date(b.open_time) - new Date(a.open_time))
    .map((t) => `<option value="${t.id}">${esc(t.symbol)} ${t.direction} \u00b7 ${fmtDate(t.open_time)}</option>`).join("");
  content().innerHTML = `
    <div class="card">
      <div class="toolbar">
        <div class="field" style="margin-bottom:0;min-width:320px"><label>Select Trade</label><select id="tc-trade">${options || "<option>No trades</option>"}</select></div>
        <div class="right">
          <select id="tc-timeframe">${["M1","M5","M15","M30","H1","H4","D1"].map((tf) => `<option ${tf === "M15" ? "selected" : ""}>${tf}</option>`).join("")}</select>
          <button class="btn btn-primary" id="tc-load">Load Chart</button>
        </div>
      </div>

      <div class="toolbar">
        <div class="right">
          <button class="btn" id="tc-reset" title="Jump back to the start of the replay">\u23ee Reset</button>
          <button class="btn" id="tc-step-back" title="Step back one bar">\u23f4</button>
          <button class="btn btn-primary" id="tc-play">\u25b6 Play</button>
          <button class="btn" id="tc-step-fwd" title="Step forward one bar">\u23f5</button>
          <select id="tc-speed">
            <option value="0.5">0.5x</option>
            <option value="1" selected>1x</option>
            <option value="2">2x</option>
            <option value="4">4x</option>
          </select>
        </div>
        <div class="right">
          ${DRAW_TOOLS.map((t) => `<button class="btn" data-draw="${t.type}">${t.label}</button>`).join("")}
          <button class="btn btn-danger" id="tc-clear-annotations">Clear Drawings</button>
          <button class="btn" id="tc-screenshot">\u{1F4F7} Screenshot</button>
        </div>
      </div>

      <canvas id="tc-canvas" style="width:100%;height:420px;display:block;cursor:crosshair"></canvas>
      <div id="tc-overlay" class="kpi-sub" style="margin-top:12px"></div>
      <div id="tc-drawhint" class="kpi-sub text-dim" style="margin-top:4px"></div>
    </div>

    <div class="card">
      <div class="card-title">\u{1F4D3} Trade Journal</div>
      <div class="grid grid-2">
        <div class="field"><label>Setup Name</label><input type="text" id="tj-setup" /></div>
        <div class="field"><label>Grade</label>
          <select id="tj-rating">${["A+","A","B","C","D","F"].map((g) => `<option>${g}</option>`).join("")}</select>
        </div>
      </div>
      <div class="field"><label>Pre-Trade Thesis</label><textarea id="tj-pre" rows="2"></textarea></div>
      <div class="field"><label>Post-Trade Review</label><textarea id="tj-post" rows="2"></textarea></div>
      <div class="field"><label>Lessons Learned</label><textarea id="tj-lessons" rows="2"></textarea></div>
      <div class="kpi-sub" id="tj-screenshots" style="margin-bottom:10px"></div>
      <div class="btn-row" style="margin-top:0"><button class="btn btn-primary" id="tj-save">Save Journal Entry</button></div>
    </div>
  `;
  if (!state.trades.length) {
    content().querySelector(".card").insertAdjacentHTML("beforeend", emptyState("\u{1F56F}\uFE0F", "No trades to chart", "Sync trade history first."));
    return;
  }

  document.getElementById("tc-load").addEventListener("click", loadTradeChart);
  document.getElementById("tc-play").addEventListener("click", toggleReplay);
  document.getElementById("tc-reset").addEventListener("click", resetReplay);
  document.getElementById("tc-step-back").addEventListener("click", () => stepReplay(-1));
  document.getElementById("tc-step-fwd").addEventListener("click", () => stepReplay(1));
  document.getElementById("tc-speed").addEventListener("change", (e) => { TC.speed = parseFloat(e.target.value); if (TC.playing) { stopReplayTimer(); startReplayTimer(); } });
  document.querySelectorAll("[data-draw]").forEach((b) => b.addEventListener("click", () => setDrawMode(b.dataset.draw)));
  document.getElementById("tc-clear-annotations").addEventListener("click", clearAnnotations);
  document.getElementById("tc-screenshot").addEventListener("click", takeScreenshot);
  document.getElementById("tc-canvas").addEventListener("click", onCanvasClick);
  document.getElementById("tj-save").addEventListener("click", saveJournalEntry);

  await loadTradeChart();
}

async function loadTradeChart() {
  stopReplayTimer();
  const tradeId = document.getElementById("tc-trade").value;
  const tf = document.getElementById("tc-timeframe").value;
  if (!tradeId) return;
  TC.tradeId = tradeId;

  let data;
  try { data = await apiGet(`/trade-chart/${tradeId}?timeframe=${tf}`); }
  catch (e) { showTransientBanner(e.message, false); return; }
  TC.candles = data.candles || [];
  TC.overlay = data.overlay;
  TC.visibleCount = TC.candles.length; // show the full chart by default; Reset scrubs back for replay
  document.getElementById("tc-play").innerHTML = "\u25b6 Play";
  TC.playing = false;

  try { TC.annotations = await apiGet(`/trades/${tradeId}/annotations?timeframe=${tf}`); }
  catch (e) { TC.annotations = []; }

  renderTradeChart();

  let note;
  try { note = await apiGet(`/trades/${tradeId}/journal`); } catch (e) { note = null; }
  document.getElementById("tj-setup").value = note ? note.setup_name : "";
  document.getElementById("tj-rating").value = note ? note.rating : "A";
  document.getElementById("tj-pre").value = note ? note.pre_trade_thesis : "";
  document.getElementById("tj-post").value = note ? note.post_trade_review : "";
  document.getElementById("tj-lessons").value = note ? note.lessons_learned : "";
  document.getElementById("tj-screenshots").textContent = note && note.screenshot_paths.length
    ? `${note.screenshot_paths.length} screenshot(s) saved to disk.` : "No screenshots saved yet.";
}

function renderTradeChart() {
  const o = TC.overlay;
  document.getElementById("tc-overlay").innerHTML =
    `Entry ${fmtNum(o.entry_price, 5)} \u00b7 Exit ${o.exit_price !== null ? fmtNum(o.exit_price, 5) : "\u2014"} \u00b7 ` +
    `SL ${o.initial_sl !== null ? fmtNum(o.initial_sl, 5) : "\u2014"} \u00b7 TP ${o.initial_tp !== null ? fmtNum(o.initial_tp, 5) : "\u2014"} \u00b7 ` +
    `R: ${o.realized_r !== null ? fmtNum(o.realized_r, 2) : "unknown"} \u00b7 Bar ${TC.visibleCount}/${TC.candles.length}`;
  drawCandles(document.getElementById("tc-canvas"), TC.candles.slice(0, TC.visibleCount), TC.overlay, TC.annotations);
}

// ------------------------------------------------------------- replay controls

function startReplayTimer() {
  const baseMs = 400;
  TC.timer = setInterval(() => {
    if (TC.visibleCount >= TC.candles.length) { stopReplayTimer(); return; }
    TC.visibleCount += 1;
    renderTradeChart();
  }, baseMs / TC.speed);
}
function stopReplayTimer() {
  if (TC.timer) clearInterval(TC.timer);
  TC.timer = null;
}
function toggleReplay() {
  TC.playing = !TC.playing;
  document.getElementById("tc-play").innerHTML = TC.playing ? "\u23f8 Pause" : "\u25b6 Play";
  if (TC.playing) startReplayTimer(); else stopReplayTimer();
}
function resetReplay() {
  stopReplayTimer();
  TC.playing = false;
  document.getElementById("tc-play").innerHTML = "\u25b6 Play";
  TC.visibleCount = Math.min(15, TC.candles.length);
  renderTradeChart();
}
function stepReplay(delta) {
  stopReplayTimer();
  TC.playing = false;
  document.getElementById("tc-play").innerHTML = "\u25b6 Play";
  TC.visibleCount = Math.max(2, Math.min(TC.candles.length, TC.visibleCount + delta));
  renderTradeChart();
}

// ------------------------------------------------------------- drawing tools

function setDrawMode(type) {
  TC.drawMode = (TC.drawMode === type) ? null : type;
  TC.pendingPoint = null;
  document.querySelectorAll("[data-draw]").forEach((b) => b.classList.toggle("btn-primary", b.dataset.draw === TC.drawMode));
  const hint = document.getElementById("tc-drawhint");
  if (!TC.drawMode) { hint.textContent = ""; return; }
  hint.textContent = TC.drawMode === "TEXT_NOTE"
    ? "Click on the chart to place a note."
    : "Click two points on the chart to draw.";
}

async function onCanvasClick(evt) {
  if (!TC.drawMode || !TC.geom) return;
  const rect = evt.target.getBoundingClientRect();
  const x = evt.clientX - rect.left, y = evt.clientY - rect.top;
  const point = { time: TC.geom.timeAt(x), price: TC.geom.priceAt(y) };

  if (TC.drawMode === "TEXT_NOTE") {
    const text = prompt("Note text:");
    if (text) await postAnnotation({ annotation_type: "TEXT_NOTE", p1_time: point.time, p1_price: point.price, p2_time: point.time, p2_price: point.price, text });
    return;
  }
  if (TC.drawMode === "HORIZONTAL_RAY") {
    await postAnnotation({ annotation_type: "HORIZONTAL_RAY", p1_time: point.time, p1_price: point.price, p2_time: point.time, p2_price: point.price });
    return;
  }
  // TREND_LINE: two clicks
  if (!TC.pendingPoint) { TC.pendingPoint = point; return; }
  await postAnnotation({ annotation_type: "TREND_LINE", p1_time: TC.pendingPoint.time, p1_price: TC.pendingPoint.price, p2_time: point.time, p2_price: point.price });
  TC.pendingPoint = null;
}

async function postAnnotation(fields) {
  try {
    const tf = document.getElementById("tc-timeframe").value;
    const saved = await apiPost(`/trades/${TC.tradeId}/annotations`, { timeframe: tf, color: "#58a6ff", line_width: 2, ...fields });
    TC.annotations.push(saved);
    renderTradeChart();
  } catch (e) { showTransientBanner(e.message, false); }
}

async function clearAnnotations() {
  try {
    const tf = document.getElementById("tc-timeframe").value;
    await api(`/trades/${TC.tradeId}/annotations?timeframe=${tf}`, { method: "DELETE" });
    TC.annotations = [];
    renderTradeChart();
  } catch (e) { showTransientBanner(e.message, false); }
}

async function takeScreenshot() {
  const canvas = document.getElementById("tc-canvas");
  try {
    const dataUrl = canvas.toDataURL("image/png");
    const res = await apiPost(`/trades/${TC.tradeId}/screenshot`, { image_base64: dataUrl });
    document.getElementById("tj-screenshots").textContent = `${res.note.screenshot_paths.length} screenshot(s) saved to disk.`;
    showTransientBanner("Screenshot saved to " + res.path, true);
  } catch (e) { showTransientBanner(e.message, false); }
}

async function saveJournalEntry() {
  try {
    await apiPost(`/trades/${TC.tradeId}/journal`, {
      setup_name: document.getElementById("tj-setup").value,
      rating: document.getElementById("tj-rating").value,
      pre_trade_thesis: document.getElementById("tj-pre").value,
      post_trade_review: document.getElementById("tj-post").value,
      lessons_learned: document.getElementById("tj-lessons").value,
      mistakes_identified: [],
      checklist_data: {},
    });
    showTransientBanner("Journal entry saved.", true);
  } catch (e) { showTransientBanner(e.message, false); }
}

// ------------------------------------------------------------- chart rendering

function drawCandles(canvas, candles, overlay, annotations) {
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth, h = canvas.clientHeight;
  canvas.width = w * dpr; canvas.height = h * dpr;
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, w, h);
  if (!candles || !candles.length) {
    ctx.fillStyle = "#6e7681"; ctx.fillText("No candle data available", 12, h / 2);
    TC.geom = null;
    return;
  }
  const highs = candles.map((c) => c.high), lows = candles.map((c) => c.low);
  let min = Math.min(...lows), max = Math.max(...highs);
  if (overlay.initial_sl) { min = Math.min(min, overlay.initial_sl); max = Math.max(max, overlay.initial_sl); }
  if (overlay.initial_tp) { min = Math.min(min, overlay.initial_tp); max = Math.max(max, overlay.initial_tp); }
  const pad = (max - min) * 0.08 || 0.0001;
  min -= pad; max += pad;
  const range = max - min;
  const cw = w / candles.length;
  const y = (price) => h - ((price - min) / range) * h;
  const priceAt = (py) => min + ((h - py) / h) * range;
  const timestamps = candles.map((c) => new Date(c.timestamp).getTime());
  const xAt = (isoTime) => {
    const t = new Date(isoTime).getTime();
    let idx = timestamps.findIndex((ct) => ct >= t);
    if (idx === -1) idx = timestamps.length - 1;
    return idx * cw + cw / 2;
  };
  const timeAt = (px) => {
    const idx = Math.max(0, Math.min(candles.length - 1, Math.floor(px / cw)));
    return candles[idx].timestamp;
  };
  TC.geom = { priceAt, timeAt };

  candles.forEach((c, i) => {
    const x = i * cw + cw / 2;
    const up = c.close >= c.open;
    ctx.strokeStyle = up ? "#26a69a" : "#ef5350";
    ctx.fillStyle = up ? "#26a69a" : "#ef5350";
    ctx.beginPath();
    ctx.moveTo(x, y(c.high)); ctx.lineTo(x, y(c.low)); ctx.stroke();
    const bodyTop = y(Math.max(c.open, c.close));
    const bodyH = Math.max(1, Math.abs(y(c.open) - y(c.close)));
    ctx.fillRect(x - cw * 0.35, bodyTop, cw * 0.7, bodyH);
  });

  function hline(price, color, label) {
    if (price === null || price === undefined) return;
    const yy = y(price);
    ctx.strokeStyle = color; ctx.setLineDash([4, 4]);
    ctx.beginPath(); ctx.moveTo(0, yy); ctx.lineTo(w, yy); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = color; ctx.font = "11px Segoe UI";
    ctx.fillText(label, 4, yy - 4);
  }
  hline(overlay.entry_price, "#58a6ff", "Entry " + overlay.entry_price);
  hline(overlay.initial_sl, "#ef5350", "SL");
  hline(overlay.initial_tp, "#26a69a", "TP");

  (annotations || []).forEach((a) => {
    ctx.strokeStyle = a.color || "#f59e0b";
    ctx.fillStyle = a.color || "#f59e0b";
    ctx.lineWidth = a.line_width || 2;
    ctx.font = "11px Segoe UI";
    if (a.annotation_type === "TREND_LINE") {
      ctx.beginPath();
      ctx.moveTo(xAt(a.p1_time), y(a.p1_price));
      ctx.lineTo(xAt(a.p2_time), y(a.p2_price));
      ctx.stroke();
    } else if (a.annotation_type === "HORIZONTAL_RAY") {
      const yy = y(a.p1_price);
      ctx.beginPath();
      ctx.moveTo(xAt(a.p1_time), yy);
      ctx.lineTo(w, yy);
      ctx.stroke();
    } else if (a.annotation_type === "TEXT_NOTE") {
      ctx.fillText(a.text || "\u{1F4CC}", xAt(a.p1_time), y(a.p1_price));
    }
    ctx.lineWidth = 1;
  });
}

// ------------------------------------------------------------------ router

const VIEWS = {
  dashboard: viewDashboard,
  trades: viewTrades,
  strategies: viewStrategies,
  "strategy-vs-trader": viewStrategyVsTrader,
  breakdowns: viewBreakdowns,
  "live-journal": viewLiveJournal,
  reports: viewReports,
  quant: viewQuant,
  "trade-chart": viewTradeChart,
  settings: viewSettings,
};

async function renderRoute() {
  const fn = VIEWS[state.route] || viewDashboard;
  await fn();
}

function syncFromHash() {
  const requested = (location.hash || "#dashboard").slice(1);
  const route = NAV.some((n) => n.id === requested) ? requested : "dashboard";
  state.route = route;
  renderNav();
  document.getElementById("page-title").textContent = NAV.find((n) => n.id === route).label;
  document.getElementById("page-sub").textContent = PAGE_SUB[route] || "";
  return renderRoute();
}

window.addEventListener("hashchange", syncFromHash);

async function init() {
  await refreshStatus();
  await syncFromHash();
  setInterval(refreshStatus, 15000);
}

init();
