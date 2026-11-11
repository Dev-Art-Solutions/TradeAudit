// TradeAudit web UI - vanilla JS SPA talking to the FastAPI backend at /api/*.

const NAV = [
  { id: "dashboard", icon: "dashboard", label: "Dashboard" },
  { id: "trades", icon: "trades", label: "Trades" },
  { id: "strategies", icon: "target", label: "Strategies" },
  { id: "strategy-vs-trader", icon: "balance", label: "Strategy vs Trader" },
  { id: "breakdowns", icon: "search", label: "Breakdowns" },
  { id: "live-journal", icon: "journal", label: "Live Journal" },
  { id: "reports", icon: "report", label: "AI Reports" },
  { id: "quant", icon: "risk", label: "Quant & Risk" },
  { id: "trade-chart", icon: "chart", label: "Trade Chart" },
  { id: "settings", icon: "settings", label: "MT5 Settings" },
];

const ICONS = {
  dashboard: '<path d="M4 13h6V4H4v9Zm0 7h6v-3H4v3Zm10 0h6v-9h-6v9Zm0-16v3h6V4h-6Z"/>',
  trades: '<path d="M4 19V9m5 10V5m5 14v-7m5 7V3"/>',
  target: '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/><path d="m14 10 6-6"/>',
  balance: '<path d="M12 3v18M5 6h14M5 6l-3 7h6L5 6Zm14 0-3 7h6l-3-7ZM8 21h8"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
  journal: '<path d="M5 3h12a2 2 0 0 1 2 2v16H7a2 2 0 0 1-2-2V3Zm2 14h12M9 7h6M9 11h6"/>',
  report: '<path d="M6 3h9l3 3v15H6V3Zm8 0v4h4M9 11h6M9 15h6"/>',
  risk: '<path d="M4 18 9 9l4 6 3-5 4 8H4Z"/><path d="M4 21h16"/>',
  chart: '<path d="M4 19V5m0 14h16M7 15l4-4 3 2 5-7"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M19 12a7 7 0 0 0-.1-1l2-1.5-2-3.4-2.4 1A8 8 0 0 0 15 6l-.3-2.6h-4L10.4 6A8 8 0 0 0 9 7.1l-2.4-1-2 3.4 2 1.5a7 7 0 0 0 0 2l-2 1.5 2 3.4 2.4-1A8 8 0 0 0 10.4 18l.3 2.6h4L15 18a8 8 0 0 0 1.5-1.1l2.4 1 2-3.4-2-1.5c.1-.3.1-.7.1-1Z"/>',
};

function navIcon(name) {
  return `<svg class="nav-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${ICONS[name]}</svg>`;
}

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

let state = {
  route: "dashboard",
  trades: [],
  strategies: [],
  api: null,
  hasAccount: false,
  selectedTradeId: null,
  tradeFilter: {
    search: "",
    direction: "ALL",
    outcome: "ALL",
    strategyId: "ALL",
    compliance: "ALL",
    emotion: "ALL",
    dateRange: "ALL",
    symbol: "ALL",
    sortCol: "open_time",
    sortDir: "desc",
  },
};

async function loadStrategies() {
  try { state.strategies = await apiGet("/strategies"); } catch (e) { state.strategies = []; }
}

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
function fmtBytes(bytes) {
  if (bytes === null || bytes === undefined || Number.isNaN(bytes)) return "\u2014";
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
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
    (n) => `<button type="button" class="nav-item ${n.id === state.route ? "active" : ""}" data-route="${n.id}" ${n.id === state.route ? 'aria-current="page"' : ""}>
      <span class="icon">${navIcon(n.icon)}</span><span>${n.label}</span>
    </button>`
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
  const pad = 12;
  const min = Math.min(...series, 0);
  const max = Math.max(...series, 0);
  const range = (max - min) || 1;
  const zeroY = h - pad - ((0 - min) / range) * (h - pad * 2);

  // Zero reference baseline
  ctx.strokeStyle = "rgba(255, 255, 255, 0.08)";
  ctx.lineWidth = 1;
  ctx.setLineDash([3, 3]);
  ctx.beginPath();
  ctx.moveTo(0, zeroY);
  ctx.lineTo(w, zeroY);
  ctx.stroke();
  ctx.setLineDash([]);

  // Peak high-water mark line if positive
  if (max > 0) {
    const peakY = h - pad - ((max - min) / range) * (h - pad * 2);
    ctx.strokeStyle = "rgba(38, 166, 154, 0.25)";
    ctx.lineWidth = 1;
    ctx.setLineDash([2, 4]);
    ctx.beginPath();
    ctx.moveTo(0, peakY);
    ctx.lineTo(w, peakY);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = "rgba(38, 166, 154, 0.7)";
    ctx.font = "9px Cascadia Code, Consolas, monospace";
    ctx.fillText(`Peak ${fmtNum(max, 2)}`, w - 75, peakY - 3);
  }

  const mainColor = opts.color || "#58a6ff";

  // Gradient area fill under equity curve
  const grad = ctx.createLinearGradient(0, 0, 0, h);
  if (mainColor === "#26a69a" || mainColor.includes("166")) {
    grad.addColorStop(0, "rgba(38, 166, 154, 0.22)");
    grad.addColorStop(1, "rgba(38, 166, 154, 0.0)");
  } else {
    grad.addColorStop(0, "rgba(88, 166, 255, 0.22)");
    grad.addColorStop(1, "rgba(88, 166, 255, 0.0)");
  }
  ctx.beginPath();
  ctx.moveTo(0, zeroY);
  series.forEach((v, i) => {
    const x = (i / (series.length - 1)) * w;
    const y = h - pad - ((v - min) / range) * (h - pad * 2);
    ctx.lineTo(x, y);
  });
  ctx.lineTo(w, zeroY);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();

  // Equity curve line
  ctx.beginPath();
  ctx.strokeStyle = mainColor;
  ctx.lineWidth = 2.2;
  series.forEach((v, i) => {
    const x = (i / (series.length - 1)) * w;
    const y = h - pad - ((v - min) / range) * (h - pad * 2);
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  });
  ctx.stroke();

  // Last point indicator badge
  const last = series[series.length - 1];
  const lx = w, ly = h - pad - ((last - min) / range) * (h - pad * 2);
  ctx.fillStyle = mainColor;
  ctx.beginPath();
  ctx.arc(lx - 4, ly, 3.5, 0, Math.PI * 2);
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
  const q = data.data_quality;
  const snapshot = data.audit_snapshot;
  if (!m.total_trades) {
    content().innerHTML = onboardingBannerHtml() +
      emptyState("\u{1F4C8}", "No trades yet", "Connect your MT5 account and run a sync from the Trades tab to see performance analytics here.");
    return;
  }
  content().innerHTML = `
    <section class="dashboard-intro" aria-labelledby="dashboard-heading">
      <div>
        <div class="eyebrow">Audit snapshot</div>
        <h2 id="dashboard-heading">Performance at a glance</h2>
        <p>A decision-focused view of edge, execution quality and downside risk.</p>
      </div>
      <div class="verdict-card">
        <span>System verdict</span>
        <strong>${esc(m.verdict.replace(/_/g, " "))}</strong>
      </div>
    </section>
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
    <div class="grid grid-4" style="margin-top:16px">
      <div class="card"><div class="card-title">Max Drawdown</div>
        <div class="kpi-value loss">${fmtNum(m.max_drawdown_r, 2)} R</div>
        <div class="kpi-sub">${fmtNum(m.max_drawdown_monetary)} monetary</div></div>
      <div class="card"><div class="card-title">Recovery / Duration</div>
        <div class="kpi-value">${m.recovery_factor === null ? "N/A" : fmtNum(m.recovery_factor, 2)}</div>
        <div class="kpi-sub">Recovery factor</div>
        <div class="kpi-sub" style="margin-top:8px">${m.avg_duration_minutes === null ? "N/A" : `${fmtNum(m.avg_duration_minutes, 1)} min avg`} (${m.trades_with_duration}/${m.total_trades})</div></div>
      <div class="card"><div class="card-title">Avg Win / Loss (R)</div>
        <div class="kpi-value win">${fmtNum(m.avg_win_r, 3)}</div>
        <div class="kpi-value loss">${fmtNum(m.avg_loss_r, 3)}</div></div>
      <div class="card"><div class="card-title">Streaks</div>
        <div class="kpi-sub">Max consecutive wins</div><div class="kpi-value win">${m.max_consecutive_wins}</div>
        <div class="kpi-sub" style="margin-top:8px">Max consecutive losses</div><div class="kpi-value loss">${m.max_consecutive_losses}</div></div>
    </div>
    <section class="card quality-card" aria-labelledby="quality-heading">
      <div class="quality-header">
        <div>
          <div class="eyebrow">Evidence readiness</div>
          <div class="card-title" id="quality-heading">Audit Data Quality</div>
          <p>${esc(q.summary)}</p>
        </div>
        <div class="quality-score" aria-label="Data quality score ${q.score} out of 100">
          <strong>${q.score}</strong><span>/100</span><small>${esc(q.grade)}</small>
        </div>
      </div>
      <div class="quality-grid">
        ${q.dimensions.map((d) => `
          <div class="quality-row">
            <div><span>${esc(d.label)}</span><strong>${Math.round(d.coverage * 100)}%</strong></div>
            <div class="quality-track" role="progressbar" aria-label="${esc(d.label)}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.round(d.coverage * 100)}">
              <span style="width:${Math.round(d.coverage * 100)}%"></span>
            </div>
            <small>${d.complete} of ${d.total} trades</small>
          </div>`).join("")}
      </div>
      ${q.actions.length ? `<div class="quality-actions"><strong>Recommended next steps</strong><ul>${q.actions.map((action) => `<li>${esc(action)}</li>`).join("")}</ul></div>` : ""}
      <div class="evidence-strip">
        <div>
          <span>Dataset fingerprint · SHA-256</span>
          <code id="evidence-fingerprint" class="clickable-code" title="Click to copy full SHA-256 fingerprint">${esc(snapshot.dataset_sha256.slice(0, 16))}…${esc(snapshot.dataset_sha256.slice(-12))}</code>
        </div>
        <div class="evidence-meta">Schema v${snapshot.schema_version} · ${snapshot.trade_count} closed trades</div>
        <button class="btn" id="btn-copy-fingerprint" title="Copy full SHA-256 fingerprint">Copy Hash</button>
        <button class="btn" id="btn-export-snapshot">Export Evidence Snapshot</button>
      </div>
    </section>
  `;
  const copyFingerprint = async () => {
    try {
      await navigator.clipboard.writeText(snapshot.dataset_sha256);
      showTransientBanner("Dataset fingerprint SHA-256 copied to clipboard.", true);
    } catch (e) {
      showTransientBanner("Could not copy fingerprint: " + e.message, false);
    }
  };
  document.getElementById("btn-copy-fingerprint").addEventListener("click", copyFingerprint);
  document.getElementById("evidence-fingerprint").addEventListener("click", copyFingerprint);
  document.getElementById("btn-export-snapshot").addEventListener("click", () => {
    const blob = new Blob([JSON.stringify(snapshot, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `tradeaudit-audit-snapshot-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    showTransientBanner("Verifiable audit evidence snapshot exported.", true);
  });
  drawLineChart(document.getElementById("chart-r"), m.cumulative_r_series, { color: "#58a6ff" });
  drawLineChart(document.getElementById("chart-money"), m.cumulative_monetary_series, { color: "#26a69a" });
}

// ------------------------------------------------------------------ trades

async function viewTrades() {
  await Promise.all([loadTrades(), loadStrategies()]);
  const stratsOptions = state.strategies.map((s) => `<option value="${s.id}">${esc(s.name)}</option>`).join("");
  const symbols = [...new Set(state.trades.map((t) => t.symbol).filter(Boolean))].sort();
  const symbolOptions = symbols.map((s) => `<option value="${esc(s)}" ${state.tradeFilter.symbol === s ? "selected" : ""}>${esc(s)}</option>`).join("");

  content().innerHTML = `
    ${onboardingBannerHtml()}
    <div class="toolbar">
      <div class="chip" id="trades-count-chip">Loading…</div>
      <div class="right">
        <button class="btn" id="btn-export-csv" title="Export trade history to CSV">📥 Export CSV</button>
        <button class="btn" id="btn-analyze-behavior" title="Run revenge trading, FOMO and overtrading detection">🧠 Analyze Behavior</button>
        <button class="btn btn-primary" id="btn-sync"><span id="sync-spinner"></span> Sync History</button>
      </div>
    </div>
    <div class="filter-toolbar">
      <div class="search-box">
        <input type="text" id="trades-search" placeholder="🔍 Search symbol, comments, notes..." value="${esc(state.tradeFilter.search)}" />
      </div>
      <select id="filter-symbol" class="filter-select" title="Filter by symbol">
        <option value="ALL">All Symbols</option>
        ${symbolOptions}
      </select>
      <select id="filter-date" class="filter-select" title="Filter by date range">
        <option value="ALL" ${state.tradeFilter.dateRange === "ALL" ? "selected" : ""}>All Dates</option>
        <option value="TODAY" ${state.tradeFilter.dateRange === "TODAY" ? "selected" : ""}>Today</option>
        <option value="WEEK" ${state.tradeFilter.dateRange === "WEEK" ? "selected" : ""}>Last 7 Days</option>
        <option value="30D" ${state.tradeFilter.dateRange === "30D" ? "selected" : ""}>Last 30 Days</option>
        <option value="MONTH" ${state.tradeFilter.dateRange === "MONTH" ? "selected" : ""}>This Month</option>
      </select>
      <select id="filter-dir" class="filter-select">
        <option value="ALL">All Directions</option>
        <option value="BUY" ${state.tradeFilter.direction === "BUY" ? "selected" : ""}>BUY</option>
        <option value="SELL" ${state.tradeFilter.direction === "SELL" ? "selected" : ""}>SELL</option>
      </select>
      <select id="filter-outcome" class="filter-select">
        <option value="ALL">All Outcomes</option>
        <option value="WIN" ${state.tradeFilter.outcome === "WIN" ? "selected" : ""}>Wins</option>
        <option value="LOSS" ${state.tradeFilter.outcome === "LOSS" ? "selected" : ""}>Losses</option>
        <option value="BE" ${state.tradeFilter.outcome === "BE" ? "selected" : ""}>Breakeven</option>
      </select>
      <select id="filter-strat" class="filter-select">
        <option value="ALL">All Strategies</option>
        <option value="NONE" ${state.tradeFilter.strategyId === "NONE" ? "selected" : ""}>No Strategy</option>
        ${stratsOptions}
      </select>
      <select id="filter-comp" class="filter-select">
        <option value="ALL">All Compliance</option>
        <option value="COMPLIANT" ${state.tradeFilter.compliance === "COMPLIANT" ? "selected" : ""}>Compliant</option>
        <option value="DEVIATION" ${state.tradeFilter.compliance === "DEVIATION" ? "selected" : ""}>Deviation</option>
        <option value="UNCHECKED" ${state.tradeFilter.compliance === "UNCHECKED" ? "selected" : ""}>Unchecked</option>
      </select>
      <select id="filter-emotion" class="filter-select">
        <option value="ALL">All Emotions</option>
        <option value="CALM" ${state.tradeFilter.emotion === "CALM" ? "selected" : ""}>😌 Calm</option>
        <option value="FOMO" ${state.tradeFilter.emotion === "FOMO" ? "selected" : ""}>⚡ FOMO</option>
        <option value="REVENGE" ${state.tradeFilter.emotion === "REVENGE" ? "selected" : ""}>🔥 Revenge</option>
        <option value="GREED" ${state.tradeFilter.emotion === "GREED" ? "selected" : ""}>🤑 Greed</option>
        <option value="FEAR" ${state.tradeFilter.emotion === "FEAR" ? "selected" : ""}>😨 Fear</option>
        <option value="BOREDOM" ${state.tradeFilter.emotion === "BOREDOM" ? "selected" : ""}>🥱 Boredom</option>
      </select>
    </div>
    <div id="trades-body"></div>
  `;
  document.getElementById("btn-sync").addEventListener("click", doSync);
  document.getElementById("btn-export-csv").addEventListener("click", doExportCsv);
  document.getElementById("btn-analyze-behavior").addEventListener("click", doAnalyzeBehavior);

  const searchInput = document.getElementById("trades-search");
  searchInput.addEventListener("input", (e) => {
    state.tradeFilter.search = e.target.value;
    renderTradesTable();
  });
  document.getElementById("filter-symbol").addEventListener("change", (e) => {
    state.tradeFilter.symbol = e.target.value;
    renderTradesTable();
  });
  document.getElementById("filter-date").addEventListener("change", (e) => {
    state.tradeFilter.dateRange = e.target.value;
    renderTradesTable();
  });
  document.getElementById("filter-dir").addEventListener("change", (e) => {
    state.tradeFilter.direction = e.target.value;
    renderTradesTable();
  });
  document.getElementById("filter-outcome").addEventListener("change", (e) => {
    state.tradeFilter.outcome = e.target.value;
    renderTradesTable();
  });
  document.getElementById("filter-strat").addEventListener("change", (e) => {
    state.tradeFilter.strategyId = e.target.value;
    renderTradesTable();
  });
  document.getElementById("filter-comp").addEventListener("change", (e) => {
    state.tradeFilter.compliance = e.target.value;
    renderTradesTable();
  });
  document.getElementById("filter-emotion").addEventListener("change", (e) => {
    state.tradeFilter.emotion = e.target.value;
    renderTradesTable();
  });

  renderTradesTable();
}

function updateTradesCountChip() {
  const chip = document.getElementById("trades-count-chip");
  if (chip) chip.textContent = `${state.trades.length} trades loaded`;
}

async function loadTrades() {
  try { state.trades = await apiGet("/trades"); } catch (e) { state.trades = []; }
}

function getFilteredTrades() {
  const f = state.tradeFilter;
  return state.trades.filter((t) => {
    if (f.direction !== "ALL" && t.direction !== f.direction) return false;
    const pl = t.net_profit ?? t.profit ?? 0;
    if (f.outcome === "WIN" && pl <= 0) return false;
    if (f.outcome === "LOSS" && pl >= 0) return false;
    if (f.outcome === "BE" && pl !== 0) return false;
    if (f.compliance !== "ALL" && (t.compliance_status || "UNCHECKED").toUpperCase() !== f.compliance) return false;
    if (f.emotion !== "ALL" && (t.emotion_tag || "").toUpperCase() !== f.emotion) return false;
    if (f.symbol && f.symbol !== "ALL" && t.symbol !== f.symbol) return false;
    if (f.dateRange && f.dateRange !== "ALL") {
      const now = new Date();
      const tDate = new Date(t.close_time || t.open_time);
      if (f.dateRange === "TODAY") {
        if (tDate.toDateString() !== now.toDateString()) return false;
      } else if (f.dateRange === "WEEK") {
        if (now - tDate > 7 * 86400000) return false;
      } else if (f.dateRange === "30D") {
        if (now - tDate > 30 * 86400000) return false;
      } else if (f.dateRange === "MONTH") {
        if (tDate.getFullYear() !== now.getFullYear() || tDate.getMonth() !== now.getMonth()) return false;
      }
    }
    if (f.strategyId === "NONE" && t.strategy_id) return false;
    if (f.strategyId !== "ALL" && f.strategyId !== "NONE" && String(t.strategy_id) !== String(f.strategyId)) return false;
    if (f.search) {
      const q = f.search.toLowerCase();
      const sym = (t.symbol || "").toLowerCase();
      const notes = (t.behavior_notes || "").toLowerCase();
      if (!sym.includes(q) && !notes.includes(q)) return false;
    }
    return true;
  });
}

function renderTradesTable() {
  const body = document.getElementById("trades-body");
  if (!body) return;

  const filtered = getFilteredTrades();
  const sortCol = state.tradeFilter.sortCol || "open_time";
  const sortDir = state.tradeFilter.sortDir === "asc" ? 1 : -1;

  filtered.sort((a, b) => {
    let va = a[sortCol], vb = b[sortCol];
    if (sortCol === "profit") { va = a.net_profit ?? a.profit ?? 0; vb = b.net_profit ?? b.profit ?? 0; }
    if (sortCol === "open_time" || sortCol === "close_time") {
      va = va ? new Date(va).getTime() : 0;
      vb = vb ? new Date(vb).getTime() : 0;
    }
    if (va === null || va === undefined) return 1;
    if (vb === null || vb === undefined) return -1;
    if (typeof va === "string") return sortDir * va.localeCompare(vb);
    return sortDir * (va - vb);
  });

  const chip = document.getElementById("trades-count-chip");
  if (chip) chip.textContent = `${filtered.length} trades shown (${state.trades.length} total)`;

  if (!state.trades.length) {
    body.innerHTML = emptyState("\u{1F4CA}", "No trades synced yet", "Configure your MT5 account in Settings, connect, then click Sync History above.");
    return;
  }
  if (!filtered.length) {
    body.innerHTML = emptyState("\u{1F50D}", "No trades match filters", "Try clearing your search query or adjusting filter dropdowns.");
    return;
  }

  // Calculate live KPI summary for filtered trades
  let winCount = 0, totalPl = 0, totalR = 0, grossWin = 0, grossLoss = 0, countR = 0;
  for (const t of filtered) {
    const pl = t.net_profit ?? t.profit ?? 0;
    totalPl += pl;
    if (pl > 0) { winCount++; grossWin += pl; }
    else if (pl < 0) { grossLoss += Math.abs(pl); }
    if (t.realized_r !== null && t.realized_r !== undefined) {
      totalR += t.realized_r;
      countR++;
    }
  }
  const winRate = filtered.length > 0 ? (winCount / filtered.length) * 100 : 0;
  const profitFactor = grossLoss > 0 ? (grossWin / grossLoss) : (grossWin > 0 ? 99.9 : 0);
  const hasActiveFilters = state.tradeFilter.direction !== "ALL" ||
    state.tradeFilter.outcome !== "ALL" ||
    state.tradeFilter.strategyId !== "ALL" ||
    state.tradeFilter.compliance !== "ALL" ||
    state.tradeFilter.emotion !== "ALL" ||
    state.tradeFilter.symbol !== "ALL" ||
    state.tradeFilter.dateRange !== "ALL" ||
    Boolean(state.tradeFilter.search);

  const kpiStripHtml = `
    <div class="trades-kpi-strip">
      <div class="kpi-mini-card"><span class="kpi-mini-label">Filtered Trades:</span><b>${filtered.length}</b></div>
      <div class="kpi-divider"></div>
      <div class="kpi-mini-card"><span class="kpi-mini-label">Win Rate:</span><b>${winRate.toFixed(1)}%</b></div>
      <div class="kpi-divider"></div>
      <div class="kpi-mini-card"><span class="kpi-mini-label">Net P/L:</span><b class="${totalPl >= 0 ? 'win' : 'loss'}">${fmtNum(totalPl)}</b></div>
      <div class="kpi-divider"></div>
      <div class="kpi-mini-card"><span class="kpi-mini-label">Net Realized R:</span><b class="${totalR >= 0 ? 'win' : 'loss'}">${countR ? fmtNum(totalR, 2) + 'R' : '—'}</b></div>
      <div class="kpi-divider"></div>
      <div class="kpi-mini-card"><span class="kpi-mini-label">Profit Factor:</span><b>${profitFactor.toFixed(2)}</b></div>
      ${hasActiveFilters ? '<div style="margin-left:auto"><button class="btn btn-sm" id="btn-clear-filters">✕ Clear Filters</button></div>' : ''}
    </div>
  `;

  function sortHeader(label, col) {
    const isActive = (state.tradeFilter.sortCol === col);
    const arrow = isActive ? (state.tradeFilter.sortDir === "asc" ? " ▲" : " ▼") : "";
    return `<th class="sortable-th" data-sort-col="${col}" title="Click to sort by ${label}">${label}<span class="sort-arrow">${arrow}</span></th>`;
  }

  const EMOTIONS = ["", "CALM", "FOMO", "REVENGE", "GREED", "FEAR", "BOREDOM"];
  const rows = filtered.map((t) => {
    const stratOptions = `<option value="">None</option>` + state.strategies.map((s) =>
      `<option value="${s.id}" ${t.strategy_id === s.id ? "selected" : ""}>${esc(s.name)}</option>`
    ).join("");

    const emotionOptions = EMOTIONS.map((em) =>
      `<option value="${em}" ${(t.emotion_tag || "").toUpperCase() === em ? "selected" : ""}>${em ? esc(em) : "None"}</option>`
    ).join("");

    const flagsHtml = (t.auto_behavior_flags || []).map((fl) =>
      `<span class="pill flag" title="${esc(fl.reason || '')}">\u26A0\uFE0F ${esc((fl.flag_type || '').replace(/_/g, ' '))}</span>`
    ).join("");

    const compStatus = (t.compliance_status || "unchecked").toLowerCase();
    const compTitle = t.deviation_reason ? `Deviation: ${esc(t.deviation_reason)}` : "";

    return `
      <tr class="clickable-row">
        <td><b>${esc(t.symbol)}</b></td>
        <td><span class="pill ${t.direction === "BUY" ? "buy" : "sell"}">${t.direction}</span></td>
        <td class="mono">${fmtVolume(t.volume)}</td>
        <td class="mono">${fmtDate(t.open_time)}</td>
        <td class="mono">${fmtDate(t.close_time)}</td>
        <td class="mono">${fmtNum(t.open_price, 5)}</td>
        <td class="mono">${t.close_price !== null ? fmtNum(t.close_price, 5) : "\u2014"}</td>
        <td class="mono ${signClass(t.net_profit ?? t.profit)}"><b>${fmtNum(t.profit)}</b></td>
        <td class="mono">${t.realized_r !== null ? fmtNum(t.realized_r, 2) : "\u2014"}</td>
        <td>
          <select class="table-select" data-assign-strat="${t.id}" title="Assign strategy to trade">${stratOptions}</select>
        </td>
        <td>
          <span class="pill ${compStatus}" title="${compTitle}">${t.compliance_status || "UNCHECKED"}</span>
        </td>
        <td>
          <select class="table-select" data-assign-emotion="${t.id}" title="Tag trade emotion">${emotionOptions}</select>
        </td>
        <td>${flagsHtml || '<span class="text-dim" style="font-size:11px">\u2014</span>'}</td>
        <td>
          <button class="btn btn-sm btn-primary" data-jump-chart="${t.id}" title="Open candlestick replay for this trade">\u{1F4C8} Chart</button>
        </td>
      </tr>`;
  }).join("");

  body.innerHTML = `
    ${kpiStripHtml}
    <div class="table-wrap">
      <table>
        <thead><tr>
          ${sortHeader("Symbol", "symbol")}
          <th>Dir</th>
          ${sortHeader("Volume", "volume")}
          ${sortHeader("Open Time", "open_time")}
          ${sortHeader("Close Time", "close_time")}
          <th>Open Px</th>
          <th>Close Px</th>
          ${sortHeader("P/L", "profit")}
          ${sortHeader("R", "realized_r")}
          <th>Strategy</th>
          <th>Compliance</th>
          <th>Emotion</th>
          <th>Discipline Flags</th>
          <th>Action</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;

  body.querySelectorAll(".sortable-th").forEach((th) => {
    th.addEventListener("click", () => {
      const col = th.dataset.sortCol;
      if (state.tradeFilter.sortCol === col) {
        state.tradeFilter.sortDir = state.tradeFilter.sortDir === "asc" ? "desc" : "asc";
      } else {
        state.tradeFilter.sortCol = col;
        state.tradeFilter.sortDir = (col === "open_time" || col === "close_time" || col === "profit" || col === "realized_r") ? "desc" : "asc";
      }
      renderTradesTable();
    });
  });

  const btnClearFilters = document.getElementById("btn-clear-filters");
  if (btnClearFilters) {
    btnClearFilters.addEventListener("click", () => {
      state.tradeFilter = {
        search: "",
        direction: "ALL",
        outcome: "ALL",
        strategyId: "ALL",
        compliance: "ALL",
        emotion: "ALL",
        dateRange: "ALL",
        symbol: "ALL",
        sortCol: "open_time",
        sortDir: "desc",
      };
      const searchBox = document.getElementById("trades-search");
      if (searchBox) searchBox.value = "";
      const filterSym = document.getElementById("filter-symbol");
      if (filterSym) filterSym.value = "ALL";
      const filterDate = document.getElementById("filter-date");
      if (filterDate) filterDate.value = "ALL";
      const filterDir = document.getElementById("filter-dir");
      if (filterDir) filterDir.value = "ALL";
      const filterOut = document.getElementById("filter-outcome");
      if (filterOut) filterOut.value = "ALL";
      const filterStrat = document.getElementById("filter-strat");
      if (filterStrat) filterStrat.value = "ALL";
      const filterComp = document.getElementById("filter-comp");
      if (filterComp) filterComp.value = "ALL";
      const filterEmo = document.getElementById("filter-emotion");
      if (filterEmo) filterEmo.value = "ALL";
      renderTradesTable();
      showTransientBanner("Filters reset to default.", true);
    });
  }

  body.querySelectorAll("[data-assign-strat]").forEach((sel) => {
    sel.addEventListener("change", async () => {
      const tradeId = parseInt(sel.dataset.assignStrat, 10);
      const val = sel.value ? parseInt(sel.value, 10) : null;
      try {
        const res = await apiPost(`/trades/${tradeId}/assign-strategy`, { strategy_id: val });
        const idx = state.trades.findIndex((x) => x.id === tradeId);
        if (idx !== -1 && res.trade) state.trades[idx] = res.trade;
        renderTradesTable();
        showTransientBanner("Strategy assigned. Compliance updated.", true);
      } catch (err) {
        showTransientBanner(err.message, false);
      }
    });
  });

  body.querySelectorAll("[data-assign-emotion]").forEach((sel) => {
    sel.addEventListener("change", async () => {
      const tradeId = parseInt(sel.dataset.assignEmotion, 10);
      const val = sel.value || null;
      try {
        await apiPost(`/trades/${tradeId}/emotion`, { emotion_tag: val });
        const tr = state.trades.find((x) => x.id === tradeId);
        if (tr) tr.emotion_tag = val;
        renderTradesTable();
        showTransientBanner("Emotion tag updated.", true);
      } catch (err) {
        showTransientBanner(err.message, false);
      }
    });
  });

  body.querySelectorAll("[data-jump-chart]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const tradeId = btn.dataset.jumpChart;
      state.selectedTradeId = tradeId;
      navigate("trade-chart");
    });
  });
}

async function doExportCsv() {
  try {
    const res = await fetch("/api/trades/export-csv", {
      headers: { "X-TradeAudit-Token": window.__TA_TOKEN__ || "" },
    });
    if (!res.ok) throw new Error("Export failed: " + res.statusText);
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `tradeaudit_trades_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
    showTransientBanner("\u2705 Trades exported to CSV successfully.", true);
  } catch (e) {
    showTransientBanner("Could not export CSV: " + e.message, false);
  }
}

async function doAnalyzeBehavior() {
  const btn = document.getElementById("btn-analyze-behavior");
  if (btn) btn.disabled = true;
  try {
    const res = await apiPost("/behavior/analyze", {});
    await loadTrades();
    renderTradesTable();
    const totalFlags = Object.values(res.flags || {}).reduce((acc, fls) => acc + (fls ? fls.length : 0), 0);
    showTransientBanner(`\u{1F9E0} Behavioral analysis complete: ${totalFlags} issue(s) identified.`, true);
  } catch (e) {
    showTransientBanner("Behavior analysis failed: " + e.message, false);
  } finally {
    if (btn) btn.disabled = false;
  }
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
    const protectedBy = result.backup_protection && result.backup_protection.created
      ? ` Safety snapshot: ${result.backup_protection.filename}.`
      : " Recent safety snapshot verified.";
    showTransientBanner((result.message || "Sync complete") + protectedBy, true);
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
  let s, diagnostics, backups;
  try { [s, diagnostics, backups] = await Promise.all([apiGet("/state"), apiGet("/diagnostics"), apiGet("/backups")]); }
  catch (e) { s = null; diagnostics = null; backups = []; }
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
        Database: <span class="mono">${esc(s ? s.storage.database_url : "")}</span><br/>
        Protection policy: automatic pre-sync snapshot (at most once per 24h), retaining the latest 10 backups.
      </div>
      <div id="backup-status" class="kpi-sub" style="margin-bottom:14px">
        ${backups && backups.length
          ? `Latest backup: <strong>${esc(backups[0].filename)}</strong> (${fmtBytes(backups[0].size_bytes)}) · ${backups.length} snapshot(s) retained`
          : `No database backups found yet. Create one manually below or run a sync.`}
      </div>
      <div class="btn-row" style="margin-top:0">
        <button class="btn" id="btn-backup">\u{1F4BE} Create Backup Now</button>
      </div>
    </div>

    <div class="card">
      <div class="card-title">\u{1F6E0}️ Diagnostics</div>
      ${diagnostics ? `
        <div class="diagnostics-head">
          <div><div class="eyebrow">Operational readiness</div><strong>${esc(diagnostics.overall.toUpperCase())}</strong></div>
          <span>v${esc(diagnostics.app_version)} · Python ${esc(diagnostics.runtime.python)} · ${esc(diagnostics.runtime.architecture)}</span>
        </div>
        <div class="diagnostics-grid">
          ${diagnostics.checks.map((check) => `
            <div class="diagnostic-check ${esc(check.status)}">
              <span class="diagnostic-dot" aria-hidden="true"></span>
              <div><strong>${esc(check.label)}</strong><small>${esc(check.detail)}</small></div>
              <span class="diagnostic-status">${esc(check.status)}</span>
            </div>`).join("")}
        </div>` : `<div class="banner error">Diagnostics are temporarily unavailable.</div>`}
      <div class="kpi-sub" style="margin:16px 0 14px">
        Export a privacy-safe runtime snapshot or inspect the recent log for support. Credentials and account identifiers are excluded.
      </div>
      <div class="btn-row" style="margin-top:0">
        <button class="btn" id="btn-export-diagnostics" ${diagnostics ? "" : "disabled"}>Export Diagnostics JSON</button>
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
      const retention = res.pruned ? ` · ${res.pruned} old backup(s) pruned` : "";
      showTransientBanner("Backup created: " + (res.filename || res.path) + retention, true);
      try {
        const updated = await apiGet("/backups");
        if (updated && updated.length) {
          const el = document.getElementById("backup-status");
          if (el) el.innerHTML = `Latest backup: <strong>${esc(updated[0].filename)}</strong> (${fmtBytes(updated[0].size_bytes)}) · ${updated.length} snapshot(s) retained`;
        }
      } catch (_) {}
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

  document.getElementById("btn-export-diagnostics").addEventListener("click", () => {
    if (!diagnostics) return;
    const blob = new Blob([JSON.stringify(diagnostics, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `tradeaudit-diagnostics-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    showTransientBanner("Privacy-safe diagnostics exported.", true);
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

const VERDICT_DETAILS = {
  HIGH_DISCIPLINE: {
    title: "High Discipline",
    icon: "🛡️",
    badge: "badge-success",
    desc: "Exceptional rule adherence. Your strategy edge is translating cleanly to your bottom line without execution drag.",
    recommendation: "Maintain current risk habits and rule adherence. Your execution is an asset.",
  },
  EXECUTION_BREAKDOWN: {
    title: "Execution Breakdown",
    icon: "🚨",
    badge: "badge-danger",
    desc: "Your core strategy has positive expectancy, but manual deviations and impulsive errors are actively erasing your edge.",
    recommendation: "Stop taking unassigned setups and eliminate Bad Losses. Strict rule compliance will immediately restore profits.",
  },
  FLAWED_STRATEGY_LUCKY_DEVIATIONS: {
    title: "False Edge / Lucky Deviations",
    icon: "⚠️",
    badge: "badge-warning",
    desc: "Your defined strategy generated negative returns, but undisciplined deviations temporarily produced positive P/L.",
    recommendation: "Beware of false security. Re-audit your core strategy rules before luck runs out.",
  },
  FLAWED_STRATEGY_AND_EXECUTION: {
    title: "Dual Deficit (System & Execution)",
    icon: "⛔",
    badge: "badge-danger",
    desc: "Both your strategy edge and trader execution show negative expectancy during this audit period.",
    recommendation: "Reduce size or trade demo. Address entry edge first, then establish strict execution discipline.",
  },
  ALL_TRADES_DEVIATIONS: {
    title: "Pure Discretionary / No Adherence",
    icon: "🔄",
    badge: "badge-warning",
    desc: "None of your closed trades complied with your strategy rules. You are currently trading purely off-script.",
    recommendation: "Review whether your defined strategies match your actual trading style, or commit to waiting for valid setups.",
  },
  NO_STRATEGY_ASSIGNED: {
    title: "No Strategy Assigned",
    icon: "ℹ️",
    badge: "badge-info",
    desc: "Trades have not been checked against defined strategies yet.",
    recommendation: "Navigate to the Trades tab and assign strategies to audit your execution discipline.",
  },
  BALANCED: {
    title: "Balanced Execution",
    icon: "⚖️",
    badge: "badge-info",
    desc: "Solid execution baseline with moderate adherence and standard market variance.",
    recommendation: "Focus on turning partial deviations into 100% compliant executions.",
  },
};

function filterTradesByQuadrant(compliance, outcome) {
  state.tradeFilter = {
    search: "",
    direction: "ALL",
    outcome: outcome || "ALL",
    strategyId: "ALL",
    compliance: compliance || "ALL",
    emotion: "ALL",
    dateRange: "ALL",
    symbol: "ALL",
    sortCol: "open_time",
    sortDir: "desc",
  };
  navigate("trades");
}

function renderCohortCard(title, m, extraClass, subtitle) {
  if (!m || !m.total_trades) {
    return `
      <div class="svt-cohort-card ${extraClass || ""}">
        <div class="svt-cohort-title">${esc(title)}</div>
        <div class="svt-cohort-sub">${esc(subtitle || "")}</div>
        <div class="svt-cohort-empty">No trades in this cohort</div>
      </div>`;
  }
  return `
    <div class="svt-cohort-card ${extraClass || ""}">
      <div class="svt-cohort-title">${esc(title)}</div>
      <div class="svt-cohort-sub">${esc(subtitle || "")}</div>
      <div class="svt-cohort-kpis">
        <div><span class="lbl">Trades:</span> <b>${m.total_trades}</b></div>
        <div><span class="lbl">Win Rate:</span> <b>${fmtPct(m.win_rate)}</b></div>
        <div><span class="lbl">Expectancy R:</span> <b class="${m.expectancy_r >= 0 ? "win" : "loss"}">${fmtNum(m.expectancy_r, 3)}</b></div>
        <div><span class="lbl">Profit Factor:</span> <b>${m.profit_factor ? fmtNum(m.profit_factor, 2) : "—"}</b></div>
        <div><span class="lbl">Net Profit:</span> <b class="${m.net_profit >= 0 ? "win" : "loss"}">${fmtNum(m.net_profit)}</b></div>
        <div><span class="lbl">Max DD:</span> <b class="loss">${fmtNum(m.max_drawdown_monetary)}</b></div>
      </div>
      <div class="win-rate-bar-wrap" style="margin-top: 10px;">
        <span class="lbl" style="font-size: 11px;">Win %</span>
        <div class="win-rate-bar-bg">
          <div class="win-rate-bar-fill" style="width: ${Math.min(100, Math.max(0, m.win_rate * 100))}%"></div>
        </div>
        <span style="font-size: 11px; font-weight: 600;">${(m.win_rate * 100).toFixed(0)}%</span>
      </div>
    </div>`;
}

function drawDisciplineScatter(canvas, trades) {
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth || 800;
  const h = canvas.clientHeight || 280;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, w, h);

  const closedTrades = (trades || []).filter(
    (t) => t.status === "CLOSED" && t.realized_r !== null && t.realized_r !== undefined
  );

  const pad = { top: 32, bottom: 28, left: 45, right: 30 };
  const chartW = Math.max(100, w - pad.left - pad.right);
  const chartH = Math.max(100, h - pad.top - pad.bottom);
  const midY = pad.top + chartH / 2;

  // Determine R bounds
  let rVals = closedTrades.map((t) => t.realized_r);
  if (!rVals.length) rVals = [-2, 2];
  let minR = Math.min(-2, ...rVals);
  let maxR = Math.max(2, ...rVals);
  const span = Math.max(2.5, Math.max(Math.abs(minR), Math.abs(maxR)) * 1.15);
  minR = -span;
  maxR = span;
  const rRange = maxR - minR;

  function getX(r) {
    return pad.left + ((r - minR) / rRange) * chartW;
  }
  const zeroX = getX(0);

  // 1. Shaded Quadrant Backgrounds
  // Top-Left: Good Losses (Compliant, R < 0)
  ctx.fillStyle = "rgba(79, 140, 255, 0.05)";
  ctx.fillRect(pad.left, pad.top, zeroX - pad.left, midY - pad.top);

  // Top-Right: Good Wins (Compliant, R >= 0)
  ctx.fillStyle = "rgba(38, 166, 154, 0.08)";
  ctx.fillRect(zeroX, pad.top, pad.left + chartW - zeroX, midY - pad.top);

  // Bottom-Left: Bad Losses (Deviations, R < 0)
  ctx.fillStyle = "rgba(239, 83, 80, 0.07)";
  ctx.fillRect(pad.left, midY, zeroX - pad.left, pad.top + chartH - midY);

  // Bottom-Right: Bad Wins (Deviations, R >= 0)
  ctx.fillStyle = "rgba(245, 158, 11, 0.07)";
  ctx.fillRect(zeroX, midY, pad.left + chartW - zeroX, pad.top + chartH - midY);

  // 2. Grid & Axes
  ctx.lineWidth = 1;
  ctx.strokeStyle = "rgba(255, 255, 255, 0.06)";

  const rStep = span > 4 ? 2 : 1;
  for (let r = -Math.floor(span); r <= Math.floor(span); r += rStep) {
    if (r === 0) continue;
    const x = getX(r);
    ctx.beginPath();
    ctx.moveTo(x, pad.top);
    ctx.lineTo(x, pad.top + chartH);
    ctx.stroke();

    ctx.fillStyle = "#6e7681";
    ctx.font = "10px 'Cascadia Code', monospace";
    ctx.textAlign = "center";
    ctx.fillText(`${r > 0 ? "+" : ""}${r}R`, x, pad.top + chartH + 18);
  }

  // Horizontal Axis (Divider between Compliant & Deviations)
  ctx.strokeStyle = "rgba(255, 255, 255, 0.2)";
  ctx.setLineDash([4, 4]);
  ctx.beginPath();
  ctx.moveTo(pad.left, midY);
  ctx.lineTo(pad.left + chartW, midY);
  ctx.stroke();

  // Vertical Zero Baseline (Divider between Losses & Wins)
  ctx.strokeStyle = "rgba(255, 255, 255, 0.3)";
  ctx.setLineDash([]);
  ctx.beginPath();
  ctx.moveTo(zeroX, pad.top);
  ctx.lineTo(zeroX, pad.top + chartH);
  ctx.stroke();

  // Axis Labels
  ctx.font = "bold 10px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
  ctx.textAlign = "left";
  ctx.fillStyle = "rgba(38, 166, 154, 0.75)";
  ctx.fillText("▲ COMPLIANT (RULES FOLLOWED)", pad.left + 8, pad.top + 16);

  ctx.fillStyle = "rgba(239, 83, 80, 0.75)";
  ctx.fillText("▼ DEVIATIONS (RULES BROKEN)", pad.left + 8, midY + 18);

  ctx.textAlign = "center";
  ctx.fillStyle = "#e6edf3";
  ctx.fillText("0.0 R", zeroX, pad.top + chartH + 18);

  // Plot trade points
  const points = [];
  const topHalfH = midY - pad.top;
  const btmHalfH = pad.top + chartH - midY;

  closedTrades.forEach((t, i) => {
    const x = getX(t.realized_r);
    const isCompliant = (t.compliance_status === "COMPLIANT");
    const seed = (t.id || (i + 1)) * 37 + (t.ticket || 11) * 17;
    const jitter = 0.25 + ((seed % 100) / 100) * 0.5;

    let y;
    let fill, stroke, quadName;
    if (isCompliant) {
      y = pad.top + jitter * topHalfH;
      if (t.net_profit >= 0) {
        fill = "rgba(38, 166, 154, 0.85)";
        stroke = "#26a69a";
        quadName = "Good Win (Compliant)";
      } else {
        fill = "rgba(79, 140, 255, 0.85)";
        stroke = "#4f8cff";
        quadName = "Good Loss (Compliant)";
      }
    } else {
      y = midY + jitter * btmHalfH;
      if (t.net_profit >= 0) {
        fill = "rgba(245, 158, 11, 0.85)";
        stroke = "#f59e0b";
        quadName = "Bad Win (Deviation)";
      } else {
        fill = "rgba(239, 83, 80, 0.85)";
        stroke = "#ef5350";
        quadName = "Bad Loss (Deviation)";
      }
    }

    ctx.fillStyle = fill;
    ctx.strokeStyle = stroke;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(x, y, 5, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    points.push({ x, y, trade: t, quadName, fill, stroke });
  });

  const tooltip = document.getElementById("svt-scatter-tooltip");
  canvas.onmousemove = (e) => {
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    let closest = null;
    let minD = 15;
    points.forEach((p) => {
      const d = Math.hypot(p.x - mx, p.y - my);
      if (d < minD) {
        minD = d;
        closest = p;
      }
    });

    if (closest && tooltip) {
      const tr = closest.trade;
      const profitStr = tr.net_profit >= 0 ? `+$${fmtNum(tr.net_profit)}` : `-$${fmtNum(Math.abs(tr.net_profit))}`;
      const rStr = `${tr.realized_r >= 0 ? "+" : ""}${fmtNum(tr.realized_r, 2)} R`;
      const emotionStr = tr.emotion_tag ? ` · ${tr.emotion_tag}` : "";
      tooltip.innerHTML = `<b>${esc(tr.symbol || "Trade")} #${tr.ticket || tr.id}</b> · <span class="${tr.net_profit >= 0 ? "win" : "loss"}">${profitStr} (${rStr})</span> · <i>${closest.quadName}</i>${esc(emotionStr)}`;
      tooltip.style.display = "inline-block";
      canvas.style.cursor = "pointer";
    } else {
      if (tooltip) tooltip.style.display = "none";
      canvas.style.cursor = "default";
    }
  };

  canvas.onclick = (e) => {
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    let clicked = null;
    let minD = 15;
    points.forEach((p) => {
      const d = Math.hypot(p.x - mx, p.y - my);
      if (d < minD) {
        minD = d;
        clicked = p;
      }
    });
    if (clicked && clicked.trade) {
      state.selectedTradeId = clicked.trade.id;
      navigate("trade-chart");
    }
  };
}

async function viewStrategyVsTrader() {
  content().innerHTML = `<div id="svt-body">Loading…</div>`;
  let c;
  try {
    [c] = await Promise.all([
      apiGet("/strategy-vs-trader"),
      loadTrades(),
    ]);
  } catch (e) {
    content().innerHTML = emptyState("⚠️", "Could not load", e.message);
    return;
  }

  if (!c.total_performance || !c.total_performance.total_trades) {
    content().innerHTML = emptyState("⚖️", "No data yet", "Sync trades and assign strategies to see the compliance quadrant.");
    return;
  }

  const q = c.four_quadrants;
  const compliantCount = (c.compliant_performance && c.compliant_performance.total_trades) || 0;
  const deviationCount = (c.deviation_performance && c.deviation_performance.total_trades) || 0;
  const emotionalCount = (c.emotional_performance && c.emotional_performance.total_trades) || 0;
  const assignedTotal = compliantCount + deviationCount;
  const disciplineScore = assignedTotal > 0 ? (compliantCount / assignedTotal) * 100 : 0;

  const vInfo = VERDICT_DETAILS[c.quality_verdict] || {
    title: esc(c.quality_verdict),
    icon: "⚖️",
    badge: "badge-info",
    desc: "Execution audit complete.",
    recommendation: "Review your quadrant metrics below.",
  };

  const gwPct = assignedTotal > 0 ? ((q.good_wins_count / assignedTotal) * 100).toFixed(1) : "0.0";
  const glPct = assignedTotal > 0 ? ((q.good_losses_count / assignedTotal) * 100).toFixed(1) : "0.0";
  const bwPct = assignedTotal > 0 ? ((q.bad_wins_count / assignedTotal) * 100).toFixed(1) : "0.0";
  const blPct = assignedTotal > 0 ? ((q.bad_losses_count / assignedTotal) * 100).toFixed(1) : "0.0";

  content().innerHTML = `
    <!-- Top Hero Strip: Discipline Health & Diagnostics -->
    <div class="svt-hero-strip">
      <div class="svt-hero-card">
        <div class="kpi-label">Discipline Score</div>
        <div class="svt-score-wrap">
          <div class="svt-score-val ${disciplineScore >= 80 ? "win" : disciplineScore >= 60 ? "" : "loss"}">
            ${disciplineScore.toFixed(0)}%
          </div>
          <div class="svt-score-sub">${compliantCount} of ${assignedTotal} audited trades compliant</div>
        </div>
        <div class="svt-progress-bar">
          <div class="svt-progress-fill ${disciplineScore >= 80 ? "bg-win" : disciplineScore >= 60 ? "bg-warn" : "bg-loss"}" style="width: ${Math.min(100, Math.max(5, disciplineScore))}%"></div>
        </div>
      </div>

      <div class="svt-hero-card">
        <div class="kpi-label">Deviation Cost (Capital Leak)</div>
        <div class="kpi-value ${c.deviation_cost_r > 0 ? "loss" : "win"}">
          ${fmtNum(c.deviation_cost_r, 2)} R
        </div>
        <div class="kpi-sub">
          Monetary drag: <b class="${c.deviation_cost_monetary > 0 ? "loss" : "win"}">${fmtNum(c.deviation_cost_monetary)}</b>
        </div>
      </div>

      <div class="svt-hero-card">
        <div class="kpi-label">Bad Losses Drain</div>
        <div class="kpi-value loss">
          ${fmtNum(q.bad_losses_profit)}
        </div>
        <div class="kpi-sub">
          ${q.bad_losses_count} unforced error trades (${fmtNum(q.bad_losses_net_r, 2)} R)
        </div>
      </div>

      <div class="svt-hero-card svt-verdict-card">
        <div class="svt-verdict-header">
          <span class="svt-verdict-icon">${vInfo.icon}</span>
          <div>
            <div class="svt-verdict-title">${vInfo.title}</div>
            <span class="badge ${vInfo.badge}">${esc(c.quality_verdict)}</span>
          </div>
        </div>
        <div class="svt-verdict-desc">${vInfo.desc}</div>
      </div>
    </div>

    <!-- Four-Quadrant Matrix 2x2 -->
    <div class="card svt-matrix-container" style="margin-top: 16px;">
      <div class="card-header-row">
        <div>
          <div class="card-title">Four-Quadrant Execution Matrix</div>
          <div class="card-sub">Process Adherence (Rules) vs Outcome (Profit / Loss)</div>
        </div>
        <div class="svt-matrix-legend">
          <span class="svt-legend-item"><span class="svt-dot dot-good-win"></span> Good Win</span>
          <span class="svt-legend-item"><span class="svt-dot dot-good-loss"></span> Good Loss</span>
          <span class="svt-legend-item"><span class="svt-dot dot-bad-win"></span> Bad Win</span>
          <span class="svt-legend-item"><span class="svt-dot dot-bad-loss"></span> Bad Loss</span>
        </div>
      </div>

      <div class="svt-matrix-layout">
        <!-- Column Header Labels -->
        <div class="svt-col-headers">
          <div class="svt-corner-label">PROCESS \\ OUTCOME</div>
          <div class="svt-col-title svt-col-win">WINNING TRADES (P/L &gt; 0)</div>
          <div class="svt-col-title svt-col-loss">LOSING TRADES (P/L &lt; 0)</div>
        </div>

        <!-- Row 1: Followed Rules (Compliant) -->
        <div class="svt-matrix-row">
          <div class="svt-row-title svt-row-compliant">
            <div class="svt-row-badge">RULES FOLLOWED</div>
            <div class="svt-row-sub">Compliant Execution</div>
          </div>

          <!-- Quadrant I: Good Wins -->
          <div class="svt-quadrant-card quadrant-good-win">
            <div class="svt-quad-head">
              <span class="svt-quad-num">QUADRANT I</span>
              <span class="badge badge-success">OPTIMAL</span>
            </div>
            <div class="svt-quad-title">🟢 Good Wins</div>
            <div class="svt-quad-metrics">
              <div class="svt-quad-stat"><span class="lbl">Trades:</span> <b>${q.good_wins_count}</b> <span class="dim">(${gwPct}%)</span></div>
              <div class="svt-quad-stat"><span class="lbl">Net R:</span> <b class="win">+${fmtNum(q.good_wins_net_r, 2)} R</b></div>
              <div class="svt-quad-stat"><span class="lbl">Profit:</span> <b class="win">+${fmtNum(q.good_wins_profit)}</b></div>
            </div>
            <div class="svt-quad-desc">Flawless execution. Followed rules and captured edge. The foundation of compounding.</div>
            <button class="btn btn-sm svt-filter-btn" onclick="filterTradesByQuadrant('COMPLIANT', 'WIN')">Filter Good Wins</button>
          </div>

          <!-- Quadrant II: Good Losses -->
          <div class="svt-quadrant-card quadrant-good-loss">
            <div class="svt-quad-head">
              <span class="svt-quad-num">QUADRANT II</span>
              <span class="badge badge-info">DISCIPLINED</span>
            </div>
            <div class="svt-quad-title">🔵 Good Losses</div>
            <div class="svt-quad-metrics">
              <div class="svt-quad-stat"><span class="lbl">Trades:</span> <b>${q.good_losses_count}</b> <span class="dim">(${glPct}%)</span></div>
              <div class="svt-quad-stat"><span class="lbl">Net R:</span> <b>${fmtNum(q.good_losses_net_r, 2)} R</b></div>
              <div class="svt-quad-stat"><span class="lbl">Loss:</span> <b>${fmtNum(q.good_losses_profit)}</b></div>
            </div>
            <div class="svt-quad-desc">Followed rules, but took a loss. Healthy variance and normal cost of doing business.</div>
            <button class="btn btn-sm svt-filter-btn" onclick="filterTradesByQuadrant('COMPLIANT', 'LOSS')">Filter Good Losses</button>
          </div>
        </div>

        <!-- Row 2: Rules Broken (Deviations) -->
        <div class="svt-matrix-row">
          <div class="svt-row-title svt-row-deviation">
            <div class="svt-row-badge">RULES BROKEN</div>
            <div class="svt-row-sub">Manual Deviations</div>
          </div>

          <!-- Quadrant III: Bad Wins -->
          <div class="svt-quadrant-card quadrant-bad-win">
            <div class="svt-quad-head">
              <span class="svt-quad-num">QUADRANT III</span>
              <span class="badge badge-warning">TOXIC HABIT</span>
            </div>
            <div class="svt-quad-title">🟡 Bad Wins</div>
            <div class="svt-quad-metrics">
              <div class="svt-quad-stat"><span class="lbl">Trades:</span> <b>${q.bad_wins_count}</b> <span class="dim">(${bwPct}%)</span></div>
              <div class="svt-quad-stat"><span class="lbl">Net R:</span> <b class="win">+${fmtNum(q.bad_wins_net_r, 2)} R</b></div>
              <div class="svt-quad-stat"><span class="lbl">Profit:</span> <b class="win">+${fmtNum(q.bad_wins_profit)}</b></div>
            </div>
            <div class="svt-quad-desc">Broke rules and won. Highly toxic reinforcement! Builds illusion of skill on bad habits.</div>
            <button class="btn btn-sm svt-filter-btn" onclick="filterTradesByQuadrant('DEVIATION', 'WIN')">Filter Bad Wins</button>
          </div>

          <!-- Quadrant IV: Bad Losses -->
          <div class="svt-quadrant-card quadrant-bad-loss">
            <div class="svt-quad-head">
              <span class="svt-quad-num">QUADRANT IV</span>
              <span class="badge badge-danger">CAPITAL LEAK</span>
            </div>
            <div class="svt-quad-title">🔴 Bad Losses</div>
            <div class="svt-quad-metrics">
              <div class="svt-quad-stat"><span class="lbl">Trades:</span> <b>${q.bad_losses_count}</b> <span class="dim">(${blPct}%)</span></div>
              <div class="svt-quad-stat"><span class="lbl">Net R:</span> <b class="loss">${fmtNum(q.bad_losses_net_r, 2)} R</b></div>
              <div class="svt-quad-stat"><span class="lbl">Loss:</span> <b class="loss">${fmtNum(q.bad_losses_profit)}</b></div>
            </div>
            <div class="svt-quad-desc">Broke rules and lost. Pure unforced error. Eliminating this single quadrant restores capital.</div>
            <button class="btn btn-sm svt-filter-btn" onclick="filterTradesByQuadrant('DEVIATION', 'LOSS')">Filter Bad Losses</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 2D Discipline Scatter Plot Canvas -->
    <div class="card" style="margin-top: 16px;">
      <div class="card-header-row">
        <div>
          <div class="card-title">Discipline Scatter Distribution</div>
          <div class="card-sub">Realized R vs Process Adherence (Hover for details, click to inspect trade)</div>
        </div>
        <div id="svt-scatter-tooltip" class="svt-tooltip"></div>
      </div>
      <canvas id="svt-scatter-canvas" class="svt-scatter-canvas"></canvas>
      <div class="svt-scatter-footer">
        <span>X-Axis: Realized R (Zero baseline at center)</span>
        <span>Y-Axis: Top = Compliant · Bottom = Deviation / Partial</span>
      </div>
    </div>

    <!-- Cohort Comparison Strip: Compliant vs Deviation vs Emotional -->
    <div class="card" style="margin-top: 16px;">
      <div class="card-title">Execution Cohort Deep-Dive</div>
      <div class="card-sub" style="margin-bottom: 12px;">Contrasting strategy rules against manual overrides and emotional trades</div>
      <div class="svt-cohort-grid">
        ${renderCohortCard("Compliant (Strategy Edge)", c.compliant_performance, "cohort-compliant", "Rules followed 100%")}
        ${renderCohortCard("Deviation (Discipline Leaks)", c.deviation_performance, "cohort-deviation", "Manual overrides & partial setups")}
        ${renderCohortCard("Emotional (Psychology Drag)", c.emotional_performance, "cohort-emotional", "FOMO, Revenge, Fear or Greed tags")}
      </div>
    </div>
  `;

  const canvas = document.getElementById("svt-scatter-canvas");
  if (canvas) {
    drawDisciplineScatter(canvas, state.trades);
  }
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

const BREAKDOWN_DIM_LABELS = {
  POST_WIN: "🟢 Post-Win Trade",
  POST_LOSS: "🔴 Post-Loss Trade",
  INITIAL_OR_BE: "⚪ Initial / Post-BE",
  STREAK_0: "⚪ Initial Trade (Streak 0)",
  WIN_STREAK_1: "🏆 Win Streak: 1",
  WIN_STREAK_2: "🏆 Win Streak: 2",
  WIN_STREAK_3_PLUS: "🔥 Win Streak: 3+",
  LOSS_STREAK_1: "⚠️ Loss Streak: 1",
  LOSS_STREAK_2: "⚠️ Loss Streak: 2",
  LOSS_STREAK_3_PLUS: "🚨 Loss Streak: 3+",
  CALM: "😌 Calm",
  FOMO: "⚡ FOMO",
  REVENGE: "🔥 Revenge",
  GREED: "🤑 Greed",
  FEAR: "😨 Fear",
  BOREDOM: "🥱 Boredom",
};

function formatBreakdownKey(key) {
  const k = String(key).trim();
  return BREAKDOWN_DIM_LABELS[k] || esc(k);
}

function drawHourlyBarChart(canvas, hourlyData) {
  if (!canvas || !hourlyData) return;
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth, h = canvas.clientHeight;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, w, h);

  const hours = Array.from({ length: 24 }, (_, i) => String(i));
  const profits = hours.map((hr) => {
    const m = hourlyData[hr] || hourlyData[parseInt(hr, 10)];
    return m ? (m.net_profit || 0) : 0;
  });
  const trades = hours.map((hr) => {
    const m = hourlyData[hr] || hourlyData[parseInt(hr, 10)];
    return m ? (m.total_trades || 0) : 0;
  });

  const minP = Math.min(...profits, 0);
  const maxP = Math.max(...profits, 0);
  const range = (maxP - minP) || 10;

  const pad = { top: 24, bottom: 26, left: 16, right: 16 };
  const chartW = w - pad.left - pad.right;
  const chartH = h - pad.top - pad.bottom;

  function getY(p) {
    return pad.top + chartH - ((p - minP) / range) * chartH;
  }

  const zeroY = getY(0);

  // Zero baseline
  ctx.strokeStyle = "rgba(255, 255, 255, 0.12)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(pad.left, zeroY);
  ctx.lineTo(pad.left + chartW, zeroY);
  ctx.stroke();

  const slotW = chartW / 24;
  const barW = Math.max(4, slotW * 0.7);

  hours.forEach((hr, i) => {
    const count = trades[i];
    const p = profits[i];
    const x = pad.left + i * slotW + (slotW - barW) / 2;

    if (count > 0 && Math.abs(p) > 0.001) {
      const y = getY(p);
      const barH = Math.abs(zeroY - y);
      const topY = p >= 0 ? y : zeroY;

      ctx.fillStyle = p >= 0 ? "rgba(38, 166, 154, 0.85)" : "rgba(239, 83, 80, 0.85)";
      ctx.fillRect(x, topY, barW, Math.max(2, barH));

      ctx.strokeStyle = p >= 0 ? "#26a69a" : "#ef5350";
      ctx.lineWidth = 1;
      ctx.strokeRect(x, topY, barW, Math.max(2, barH));
    } else if (count > 0) {
      ctx.fillStyle = "#8b949e";
      ctx.fillRect(x, zeroY - 2, barW, 4);
    }

    if (i % 2 === 0 || count > 0) {
      ctx.fillStyle = count > 0 ? "#e6edf3" : "#6e7681";
      ctx.font = count > 0 ? "bold 10px 'Cascadia Code', monospace" : "9px 'Cascadia Code', monospace";
      ctx.textAlign = "center";
      ctx.fillText(hr.padStart(2, "0"), x + barW / 2, h - 8);
    }
  });

  ctx.textAlign = "left";
  ctx.font = "11px Segoe UI";
  ctx.fillStyle = "#8b949e";
  ctx.fillText("Net P/L by Trade Entry Hour (00:00 – 23:00 UTC)", pad.left, 14);
}

function renderBreakdownInsights(b) {
  const insights = [];

  if (b.by_symbol) {
    const symbols = Object.entries(b.by_symbol).filter(([, m]) => m.total_trades > 0);
    if (symbols.length) {
      symbols.sort((a, b) => (b[1].net_profit || 0) - (a[1].net_profit || 0));
      const best = symbols[0];
      insights.push(`
        <div class="bd-insight-card">
          <div class="bd-insight-label">Top Instrument</div>
          <div class="bd-insight-val">${esc(best[0])}</div>
          <div class="bd-insight-sub text-win">${fmtNum(best[1].net_profit)} (${fmtNum(best[1].expectancy_r, 2)}R · ${fmtPct(best[1].win_rate)} WR)</div>
        </div>
      `);
    }
  }

  if (b.by_session) {
    const sessions = Object.entries(b.by_session).filter(([, m]) => m.total_trades > 0);
    if (sessions.length) {
      sessions.sort((a, b) => (b[1].net_profit || 0) - (a[1].net_profit || 0));
      const best = sessions[0];
      insights.push(`
        <div class="bd-insight-card">
          <div class="bd-insight-label">Optimal Session</div>
          <div class="bd-insight-val">${esc(best[0])}</div>
          <div class="bd-insight-sub text-win">${fmtNum(best[1].net_profit)} (${fmtNum(best[1].expectancy_r, 2)}R · ${best[1].total_trades} trades)</div>
        </div>
      `);
    }
  }

  if (b.by_weekday) {
    const days = Object.entries(b.by_weekday).filter(([, m]) => m.total_trades > 0);
    if (days.length) {
      days.sort((a, b) => (b[1].net_profit || 0) - (a[1].net_profit || 0));
      const best = days[0];
      insights.push(`
        <div class="bd-insight-card">
          <div class="bd-insight-label">Prime Weekday</div>
          <div class="bd-insight-val">${esc(best[0])}</div>
          <div class="bd-insight-sub text-win">${fmtNum(best[1].net_profit)} (${fmtPct(best[1].win_rate)} WR)</div>
        </div>
      `);
    }
  }

  if (b.by_context && b.by_context.POST_LOSS && b.by_context.POST_WIN) {
    const pl = b.by_context.POST_LOSS;
    const pw = b.by_context.POST_WIN;
    if (pl.total_trades > 0 && pw.total_trades > 0) {
      const isDrag = pl.expectancy_r < pw.expectancy_r && pl.expectancy_r < 0;
      insights.push(`
        <div class="bd-insight-card">
          <div class="bd-insight-label">Post-Loss Sequence</div>
          <div class="bd-insight-val ${isDrag ? 'text-loss' : 'text-win'}">${fmtNum(pl.expectancy_r, 2)}R Exp</div>
          <div class="bd-insight-sub">${isDrag ? '⚠️ Post-loss drag vs ' + fmtNum(pw.expectancy_r, 2) + 'R post-win' : 'Disciplined post-loss execution'}</div>
        </div>
      `);
    }
  }

  if (!insights.length) return "";
  return `<div class="bd-insights-grid">${insights.join("")}</div>`;
}

function breakdownTable(title, dict, categoryClass = "") {
  if (!dict || !Object.keys(dict).length) return "";
  const rows = Object.entries(dict)
    .filter(([, m]) => m.total_trades > 0)
    .map(([key, m]) => {
      const pf = m.profit_factor !== null && m.profit_factor !== undefined ? fmtNum(m.profit_factor, 2) : "—";
      const winPct = Math.round((m.win_rate || 0) * 100);
      return `
        <tr>
          <td><b>${formatBreakdownKey(key)}</b></td>
          <td class="mono">${m.total_trades}</td>
          <td>
            <div class="win-rate-bar-wrap">
              <div class="win-rate-bar-bg"><div class="win-rate-bar-fill" style="width:${winPct}%"></div></div>
              <span class="mono">${fmtPct(m.win_rate)}</span>
            </div>
          </td>
          <td class="mono">${pf}</td>
          <td class="mono ${m.expectancy_r >= 0 ? "text-win" : "text-loss"}">${fmtNum(m.expectancy_r, 3)}R</td>
          <td class="mono ${m.net_profit >= 0 ? "text-win" : "text-loss"}"><b>${fmtNum(m.net_profit)}</b></td>
        </tr>`;
    }).join("");

  if (!rows) return "";
  return `
    <div class="card bd-card ${categoryClass}" style="margin-top:12px">
      <div class="card-title">${title}</div>
      <div class="table-wrap" style="max-height:280px">
        <table>
          <thead><tr><th>Category</th><th>Trades</th><th>Win Rate</th><th>Profit Factor</th><th>Expectancy</th><th>Net P/L</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </div>`;
}

async function viewBreakdowns() {
  content().innerHTML = `<div id="bd-body">Loading…</div>`;
  let b;
  try { b = await apiGet("/breakdown"); } catch (e) {
    content().innerHTML = emptyState("⚠️", "Could not load", e.message); return;
  }

  const hasData = Object.values(b).some((d) => d && Object.keys(d).length && Object.values(d).some(m => m && m.total_trades > 0));
  if (!hasData) {
    content().innerHTML = emptyState("🔍", "No data yet", "Sync trades to see multi-dimensional breakdowns.");
    return;
  }

  content().innerHTML = `
    ${renderBreakdownInsights(b)}

    <div class="toolbar" style="margin-bottom:12px">
      <div class="dimension-filter-bar">
        <button class="btn btn-sm bd-filter-btn active" data-bd-cat="all">All Dimensions</button>
        <button class="btn btn-sm btn-subtle bd-filter-btn" data-bd-cat="instrument">Symbol & Direction</button>
        <button class="btn btn-sm btn-subtle bd-filter-btn" data-bd-cat="time">Time & Sessions</button>
        <button class="btn btn-sm btn-subtle bd-filter-btn" data-bd-cat="sequence">Sequence & Streaks</button>
        <button class="btn btn-sm btn-subtle bd-filter-btn" data-bd-cat="emotion">Psychology & Emotion</button>
      </div>
    </div>

    <div id="bd-content">
      <div class="bd-group cat-instrument">
        ${breakdownTable("By Symbol", b.by_symbol)}
        ${breakdownTable("By Direction (BUY vs SELL)", b.by_direction)}
      </div>

      <div class="bd-group cat-time">
        <div class="card" style="margin-top:12px">
          <div class="card-title" style="margin-bottom:4px">Hourly P/L & Distribution (24-Hour Cycle)</div>
          <canvas id="hourly-bar-canvas" class="hourly-bar-canvas"></canvas>
        </div>
        ${breakdownTable("By Trading Session", b.by_session)}
        ${breakdownTable("By Day of Week", b.by_weekday)}
      </div>

      <div class="bd-group cat-sequence">
        ${breakdownTable("Contextual Trade Sequence (Post-Win vs Post-Loss)", b.by_context)}
        ${breakdownTable("Win & Loss Streaks Preceding Entry", b.by_streak)}
      </div>

      <div class="bd-group cat-emotion">
        ${breakdownTable("Psychological Emotion Tags", b.by_emotion)}
      </div>
    </div>
  `;

  const canvas = document.getElementById("hourly-bar-canvas");
  if (canvas && b.by_hour) {
    drawHourlyBarChart(canvas, b.by_hour);
    window.addEventListener("resize", () => {
      const c = document.getElementById("hourly-bar-canvas");
      if (c && b.by_hour) drawHourlyBarChart(c, b.by_hour);
    }, { once: true });
  }

  document.querySelectorAll(".bd-filter-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".bd-filter-btn").forEach((b) => {
        b.classList.add("btn-subtle");
        b.classList.remove("active");
      });
      btn.classList.remove("btn-subtle");
      btn.classList.add("active");

      const cat = btn.dataset.bdCat;
      document.querySelectorAll("#bd-content .bd-group").forEach((group) => {
        if (cat === "all") {
          group.style.display = "block";
        } else if (group.classList.contains(`cat-${cat}`)) {
          group.style.display = "block";
        } else {
          group.style.display = "none";
        }
      });
    });
  });
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

function renderMarkdownHtml(md) {
  if (!md) return "";
  const lines = md.split("\n");
  const html = [];
  let inCode = false;
  let codeBuffer = [];
  let inTable = false;
  let tableRows = [];

  function flushTable() {
    if (!inTable || !tableRows.length) return;
    let tableHtml = '<div class="table-wrap"><table class="report-table">';
    let isHeader = true;
    for (const row of tableRows) {
      if (row.trim().match(/^\|(\s*:?-+:?\s*\|)+$/)) {
        isHeader = false;
        continue;
      }
      const cells = row.split("|").slice(1, -1);
      const tag = isHeader ? "th" : "td";
      tableHtml += "<tr>" + cells.map((c) => `<${tag}>${formatInline(c.trim())}</${tag}>`).join("") + "</tr>";
    }
    tableHtml += "</table></div>";
    html.push(tableHtml);
    inTable = false;
    tableRows = [];
  }

  function formatInline(text) {
    return esc(text)
      .replace(/\*\*(.+?)\*\*/g, "<b>$1</b>")
      .replace(/\*(.+?)\*/g, "<i>$1</i>")
      .replace(/`([^`]+)`/g, "<code>$1</code>");
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (line.trim().startsWith("```")) {
      if (inTable) flushTable();
      if (inCode) {
        html.push(`<pre class="report-code-block"><code>${esc(codeBuffer.join("\n"))}</code></pre>`);
        codeBuffer = [];
        inCode = false;
      } else {
        inCode = true;
      }
      continue;
    }
    if (inCode) {
      codeBuffer.push(line);
      continue;
    }

    if (line.trim().startsWith("|") && line.trim().endsWith("|")) {
      inTable = true;
      tableRows.push(line);
      continue;
    } else if (inTable) {
      flushTable();
    }

    if (line.startsWith("# ")) {
      html.push(`<h1 class="report-h1">${formatInline(line.slice(2))}</h1>`);
    } else if (line.startsWith("## ")) {
      html.push(`<h2 class="report-h2">${formatInline(line.slice(3))}</h2>`);
    } else if (line.startsWith("### ")) {
      html.push(`<h3 class="report-h3">${formatInline(line.slice(4))}</h3>`);
    } else if (line.trim() === "---") {
      html.push('<hr class="report-divider" />');
    } else if (line.startsWith("> ")) {
      html.push(`<blockquote class="report-quote">${formatInline(line.slice(2))}</blockquote>`);
    } else if (line.trim().startsWith("- ") || line.trim().startsWith("* ")) {
      html.push(`<li class="report-list-item">${formatInline(line.trim().slice(2))}</li>`);
    } else if (line.trim().length > 0) {
      html.push(`<p class="report-p">${formatInline(line)}</p>`);
    }
  }
  if (inTable) flushTable();
  if (inCode) {
    html.push(`<pre class="report-code-block"><code>${esc(codeBuffer.join("\n"))}</code></pre>`);
  }
  return html.join("\n");
}

let currentReportData = {
  markdown: "",
  aiPrompt: "",
  depth: "Standard",
  period: "ALL_TIME",
  symbol: "ALL",
};

async function viewReports() {
  await loadTrades();
  const symbols = [...new Set(state.trades.map((t) => t.symbol).filter(Boolean))].sort();
  const symbolOptions = symbols.map((s) => `<option value="${esc(s)}">${esc(s)}</option>`).join("");

  content().innerHTML = `
    <div class="card" style="margin-bottom:12px">
      <div class="toolbar" style="flex-wrap:wrap;gap:12px">
        <div style="display:flex;align-items:center;gap:6px">
          <label for="sel-report-depth" style="margin:0;font-size:12px;color:var(--text-dim)">Depth:</label>
          <select id="sel-report-depth" style="width:auto;padding:5px 8px;font-size:12px">
            <option value="Summary">Summary</option>
            <option value="Standard" selected>Standard</option>
            <option value="Full">Full (with ledger)</option>
          </select>
        </div>

        <div style="display:flex;align-items:center;gap:6px">
          <label for="sel-report-period" style="margin:0;font-size:12px;color:var(--text-dim)">Period:</label>
          <select id="sel-report-period" style="width:auto;padding:5px 8px;font-size:12px">
            <option value="ALL_TIME" selected>All Time</option>
            <option value="TODAY">Today</option>
            <option value="THIS_WEEK">This Week</option>
            <option value="LAST_WEEK">Last Week</option>
            <option value="THIS_MONTH">This Month</option>
            <option value="LAST_MONTH">Last Month</option>
          </select>
        </div>

        <div style="display:flex;align-items:center;gap:6px">
          <label for="sel-report-symbol" style="margin:0;font-size:12px;color:var(--text-dim)">Symbol:</label>
          <select id="sel-report-symbol" style="width:auto;padding:5px 8px;font-size:12px">
            <option value="ALL" selected>All Symbols</option>
            ${symbolOptions}
          </select>
        </div>

        <div style="display:flex;align-items:center;gap:6px">
          <label style="margin:0;font-size:12px;color:var(--text-dim);cursor:pointer;display:inline-flex;align-items:center;gap:4px">
            <input type="checkbox" id="chk-report-anonymize" checked /> Anonymize
          </label>
        </div>

        <div class="right">
          <button class="btn btn-primary" id="btn-gen-report">Generate Report</button>
        </div>
      </div>
    </div>

    <div class="toolbar" style="margin-bottom:8px">
      <div style="display:flex;gap:4px">
        <button class="btn btn-sm" id="btn-view-formatted" style="font-weight:600">👁️ Formatted View</button>
        <button class="btn btn-sm btn-subtle" id="btn-view-raw">📄 Raw Markdown</button>
      </div>
      <div class="right" style="gap:8px">
        <button class="btn btn-sm" id="btn-copy-prompt" style="display:none">🤖 Copy AI Prompt</button>
        <button class="btn btn-sm" id="btn-copy-report" style="display:none">📋 Copy Report</button>
        <button class="btn btn-sm" id="btn-download-report" style="display:none">💾 Download .md</button>
      </div>
    </div>

    <div class="card">
      <div id="report-rendered" class="report-rendered-view">Click "Generate Report" to build an AI-ready audit dossier from your synced trades.</div>
      <div class="markdown-box" id="report-box" style="display:none">Click "Generate Report" to build a Markdown / AI-ready audit dossier from your synced trades.</div>
    </div>
  `;

  let viewMode = "formatted";

  function setViewMode(mode) {
    viewMode = mode;
    const btnFormatted = document.getElementById("btn-view-formatted");
    const btnRaw = document.getElementById("btn-view-raw");
    const elRendered = document.getElementById("report-rendered");
    const elRaw = document.getElementById("report-box");

    if (mode === "formatted") {
      btnFormatted.classList.remove("btn-subtle");
      btnFormatted.style.fontWeight = "600";
      btnRaw.classList.add("btn-subtle");
      btnRaw.style.fontWeight = "normal";
      elRendered.style.display = "block";
      elRaw.style.display = "none";
    } else {
      btnRaw.classList.remove("btn-subtle");
      btnRaw.style.fontWeight = "600";
      btnFormatted.classList.add("btn-subtle");
      btnFormatted.style.fontWeight = "normal";
      elRendered.style.display = "none";
      elRaw.style.display = "block";
    }
  }

  document.getElementById("btn-view-formatted").addEventListener("click", () => setViewMode("formatted"));
  document.getElementById("btn-view-raw").addEventListener("click", () => setViewMode("raw"));

  document.getElementById("btn-gen-report").addEventListener("click", async () => {
    document.getElementById("report-rendered").innerHTML = "<i>Generating audit dossier…</i>";
    document.getElementById("report-box").textContent = "Generating…";
    document.getElementById("btn-copy-prompt").style.display = "none";
    document.getElementById("btn-copy-report").style.display = "none";
    document.getElementById("btn-download-report").style.display = "none";

    const depth = document.getElementById("sel-report-depth").value;
    const period = document.getElementById("sel-report-period").value;
    const symbol = document.getElementById("sel-report-symbol").value;
    const anonymize = document.getElementById("chk-report-anonymize").checked;

    currentReportData.depth = depth;
    currentReportData.period = period;
    currentReportData.symbol = symbol;

    try {
      const qs = new URLSearchParams({
        export_type: depth,
        period: period,
        symbol: symbol,
        mask_account: anonymize ? "true" : "false",
        hide_broker: anonymize ? "true" : "false",
        mask_tickets: anonymize ? "true" : "false",
      });
      const res = await apiGet(`/report?${qs.toString()}`);
      currentReportData.markdown = res.markdown;
      currentReportData.aiPrompt = res.ai_prompt || "";

      document.getElementById("report-box").textContent = res.markdown;
      document.getElementById("report-rendered").innerHTML = renderMarkdownHtml(res.markdown);

      document.getElementById("btn-copy-prompt").style.display = "inline-flex";
      document.getElementById("btn-copy-report").style.display = "inline-flex";
      document.getElementById("btn-download-report").style.display = "inline-flex";
    } catch (e) {
      document.getElementById("report-rendered").innerHTML = `<span class="loss">Error: ${esc(e.message)}</span>`;
      document.getElementById("report-box").textContent = "Error: " + e.message;
    }
  });

  document.getElementById("btn-copy-prompt").addEventListener("click", async () => {
    if (!currentReportData.aiPrompt) return;
    try {
      await navigator.clipboard.writeText(currentReportData.aiPrompt);
      showTransientBanner("🤖 AI System Prompt copied! Paste into ChatGPT or Claude.", true);
    } catch (e) {
      showTransientBanner("Could not copy AI Prompt automatically.", false);
    }
  });

  document.getElementById("btn-copy-report").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(document.getElementById("report-box").textContent);
      showTransientBanner("📋 Full audit report copied to clipboard!", true);
    } catch (e) {
      showTransientBanner("Could not copy automatically - select the text manually.", false);
    }
  });

  document.getElementById("btn-download-report").addEventListener("click", () => {
    const text = document.getElementById("report-box").textContent;
    if (!text) return;
    const depth = (currentReportData.depth || "standard").toLowerCase();
    const sym = (currentReportData.symbol || "all").toLowerCase();
    const blob = new Blob([text], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `tradeaudit-report-${depth}-${sym}-${new Date().toISOString().slice(0, 10)}.md`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    showTransientBanner("Markdown audit report downloaded.", true);
  });
}

// ------------------------------------------------------------------ quant

function drawMonteCarloCone(canvas, mc) {
  if (!canvas || !mc) return;
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth, h = canvas.clientHeight;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, w, h);

  const p5 = mc.percentile_5th_r || [];
  const p25 = mc.percentile_25th_r || [];
  const p50 = mc.percentile_50th_r || [];
  const p75 = mc.percentile_75th_r || [];
  const p95 = mc.percentile_95th_r || [];

  if (p50.length < 2) {
    ctx.fillStyle = "#6e7681";
    ctx.font = "12px Segoe UI";
    ctx.fillText("Not enough simulation points", 16, h / 2);
    return;
  }

  const allVals = [...p5, ...p95, 0];
  const min = Math.min(...allVals);
  const max = Math.max(...allVals);
  const range = (max - min) || 1;

  const pad = { top: 20, bottom: 25, left: 16, right: 85 };
  const chartW = w - pad.left - pad.right;
  const chartH = h - pad.top - pad.bottom;

  function getX(i, n) {
    return pad.left + (i / (n - 1)) * chartW;
  }
  function getY(val) {
    return pad.top + chartH - ((val - min) / range) * chartH;
  }

  // Zero baseline
  const zeroY = getY(0);
  ctx.strokeStyle = "rgba(255, 255, 255, 0.15)";
  ctx.lineWidth = 1;
  ctx.setLineDash([4, 4]);
  ctx.beginPath();
  ctx.moveTo(pad.left, zeroY);
  ctx.lineTo(pad.left + chartW, zeroY);
  ctx.stroke();
  ctx.setLineDash([]);

  // Shaded Band 1: 5th to 95th Percentile (90% envelope)
  ctx.beginPath();
  p95.forEach((v, i) => {
    const x = getX(i, p95.length);
    const y = getY(v);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  for (let i = p5.length - 1; i >= 0; i--) {
    const x = getX(i, p5.length);
    const y = getY(p5[i]);
    ctx.lineTo(x, y);
  }
  ctx.closePath();
  ctx.fillStyle = "rgba(88, 166, 255, 0.10)";
  ctx.fill();

  // Shaded Band 2: 25th to 75th Percentile (50% envelope)
  ctx.beginPath();
  p75.forEach((v, i) => {
    const x = getX(i, p75.length);
    const y = getY(v);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  for (let i = p25.length - 1; i >= 0; i--) {
    const x = getX(i, p25.length);
    const y = getY(p25[i]);
    ctx.lineTo(x, y);
  }
  ctx.closePath();
  ctx.fillStyle = "rgba(88, 166, 255, 0.22)";
  ctx.fill();

  // 95th percentile upper boundary
  ctx.strokeStyle = "#26a69a";
  ctx.lineWidth = 1.5;
  ctx.setLineDash([4, 3]);
  ctx.beginPath();
  p95.forEach((v, i) => {
    const x = getX(i, p95.length);
    const y = getY(v);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
  ctx.setLineDash([]);

  // 5th percentile lower boundary
  ctx.strokeStyle = "#ef5350";
  ctx.lineWidth = 1.5;
  ctx.setLineDash([4, 3]);
  ctx.beginPath();
  p5.forEach((v, i) => {
    const x = getX(i, p5.length);
    const y = getY(v);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
  ctx.setLineDash([]);

  // 50th percentile Median trajectory line
  ctx.strokeStyle = "#58a6ff";
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  p50.forEach((v, i) => {
    const x = getX(i, p50.length);
    const y = getY(v);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  // Endpoint labels at the right
  const lastIdx = p50.length - 1;
  const labelX = pad.left + chartW + 6;
  ctx.font = "11px 'Cascadia Code', Consolas, monospace";

  ctx.fillStyle = "#26a69a";
  ctx.fillText(`${fmtNum(p95[lastIdx], 1)}R (95%)`, labelX, getY(p95[lastIdx]) + 4);

  ctx.fillStyle = "#58a6ff";
  ctx.fillText(`${fmtNum(p50[lastIdx], 1)}R (Med)`, labelX, getY(p50[lastIdx]) + 4);

  ctx.fillStyle = "#ef5350";
  ctx.fillText(`${fmtNum(p5[lastIdx], 1)}R (5%)`, labelX, getY(p5[lastIdx]) + 4);

  // Axis labels
  ctx.fillStyle = "#8b949e";
  ctx.font = "10px Segoe UI";
  ctx.fillText("Trade 0", pad.left, h - 8);
  ctx.fillText(`Trade ${mc.horizon_trades || lastIdx}`, pad.left + chartW - 45, h - 8);
}

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
  const mc = q.monte_carlo, ror = q.risk_of_ruin, ci = q.confidence_intervals || {};
  content().innerHTML = `
    <div class="grid grid-4">
      <div class="kpi"><div class="kpi-label">Median Final R</div><div class="kpi-value ${mc.final_r_median >= 0 ? 'win' : 'loss'}">${fmtNum(mc.final_r_median, 2)} R</div><div class="kpi-sub">50th percentile</div></div>
      <div class="kpi"><div class="kpi-label">5th / 95th Percentile</div><div class="kpi-value">${fmtNum(mc.final_r_5th, 1)} / ${fmtNum(mc.final_r_95th, 1)}</div><div class="kpi-sub">Simulation envelope</div></div>
      <div class="kpi"><div class="kpi-label">Median Max Drawdown</div><div class="kpi-value loss">${fmtNum(mc.max_drawdown_median, 2)} R</div><div class="kpi-sub">Expected path MDD</div></div>
      <div class="kpi"><div class="kpi-label">95th %ile Max Drawdown</div><div class="kpi-value loss">${fmtNum(mc.max_drawdown_95th, 2)} R</div><div class="kpi-sub">Worst 5% tail risk</div></div>
    </div>

    <div class="card" style="margin-top:16px">
      <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px">
        <div class="card-title" style="margin:0">Monte Carlo Equity Simulation Envelope</div>
        <div class="chip">${mc.simulations_count} runs · ${mc.horizon_trades} trades horizon · ${esc(mc.sampling_method.replace(/_/g, " "))}</div>
      </div>
      <canvas id="mc-cone-canvas" class="mc-cone-canvas" style="width:100%;height:320px;display:block"></canvas>
      <div class="mc-legend">
        <div class="mc-legend-item"><span class="mc-legend-dot" style="background:#26a69a"></span> <b>95th Percentile</b> (Optimistic path)</div>
        <div class="mc-legend-item"><span class="mc-legend-dot" style="background:#58a6ff"></span> <b>50th Percentile</b> (Median expected equity)</div>
        <div class="mc-legend-item"><span class="mc-legend-dot" style="background:#ef5350"></span> <b>5th Percentile</b> (Downside stress test)</div>
        <div class="mc-legend-item"><span class="mc-legend-dot" style="background:rgba(88,166,255,0.25)"></span> <b>50% Interquartile Band</b> (25th–75th)</div>
      </div>
    </div>

    ${ci.win_rate_ci ? `
    <div class="card" style="margin-top:16px">
      <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-bottom:12px">
        <div class="card-title" style="margin:0">Bootstrap 95% Confidence Intervals & Statistical Edge</div>
        <span class="pill ${ci.is_statistically_significant ? 'win' : 'warn'}">
          ${ci.is_statistically_significant ? '✅ Statistically Significant (p < 0.05)' : '⚠️ Edge Not Statistically Confirmed'}
        </span>
      </div>
      <div class="grid grid-4">
        <div class="kpi">
          <div class="kpi-label">Win Rate (95% CI)</div>
          <div class="kpi-value">${fmtNum(ci.win_rate_ci[0], 1)}% — ${fmtNum(ci.win_rate_ci[1], 1)}%</div>
          <div class="kpi-sub">Sample size: ${ci.sample_size} trades</div>
        </div>
        <div class="kpi">
          <div class="kpi-label">Expectancy (95% CI)</div>
          <div class="kpi-value ${ci.expectancy_ci[0] >= 0 ? 'win' : 'loss'}">${fmtNum(ci.expectancy_ci[0], 2)}R — ${fmtNum(ci.expectancy_ci[1], 2)}R</div>
          <div class="kpi-sub">${ci.expectancy_ci[0] > 0 ? 'Robust positive edge' : 'Lower bound includes negative R'}</div>
        </div>
        <div class="kpi">
          <div class="kpi-label">Profit Factor (95% CI)</div>
          <div class="kpi-value">${fmtNum(ci.profit_factor_ci[0], 2)} — ${fmtNum(ci.profit_factor_ci[1], 2)}</div>
          <div class="kpi-sub">${ci.profit_factor_ci[0] >= 1.0 ? 'Profitable in >=95% of bootstrap paths' : 'Includes sub-1.0 breakeven'}</div>
        </div>
        <div class="kpi">
          <div class="kpi-label">Average R (95% CI)</div>
          <div class="kpi-value ${ci.avg_r_ci[0] >= 0 ? 'win' : 'loss'}">${fmtNum(ci.avg_r_ci[0], 2)}R — ${fmtNum(ci.avg_r_ci[1], 2)}R</div>
          <div class="kpi-sub">Mean expected return per trade</div>
        </div>
      </div>
      ${ci.warnings && ci.warnings.length ? `<ul class="kpi-sub" style="margin-top:12px;color:var(--warn)">${ci.warnings.map(w => `<li>⚠️ ${esc(w)}</li>`).join("")}</ul>` : ''}
    </div>
    ` : ''}

    <div class="card" style="margin-top:16px">
      <div class="card-title">Stress Testing & Risk of Ruin</div>
      <div class="grid grid-3">
        <div><div class="kpi-label">Risk Level</div><div class="kpi-value">${esc(ror.risk_level.replace(/_/g, " "))}</div></div>
        <div><div class="kpi-label">Empirical Ruin Probability</div><div class="kpi-value">${fmtNum(ror.empirical_ruin_probability, 1)}%</div></div>
        <div><div class="kpi-label">Formulaic Ruin Probability</div><div class="kpi-value">${fmtNum(ror.formulaic_ruin_probability, 1)}%</div></div>
      </div>
      <div class="grid grid-3" style="margin-top:12px">
        <div><div class="kpi-label">Worst 95% Consecutive Losses</div><div class="kpi-value loss">${mc.worst_consecutive_losses_95th} trades</div></div>
        <div><div class="kpi-label">Target (+20R) Achievement Prob</div><div class="kpi-value win">${fmtNum(mc.probability_of_target_r, 1)}%</div></div>
        <div><div class="kpi-label">Ruin (-10R) Threshold Prob</div><div class="kpi-value ${mc.probability_of_ruin_threshold > 5 ? 'loss' : 'win'}">${fmtNum(mc.probability_of_ruin_threshold, 1)}%</div></div>
      </div>
      <div class="kpi-sub" style="margin-top:14px">${esc(ror.summary_verdict)}</div>
      <ul class="kpi-sub" style="margin-top:8px">${(ror.assumptions || []).map((a) => `<li>${esc(a)}</li>`).join("")}</ul>
    </div>

    ${renderRollingTable(q.rolling_analytics)}
  `;

  const canvas = document.getElementById("mc-cone-canvas");
  if (canvas) {
    drawMonteCarloCone(canvas, mc);
    window.addEventListener("resize", () => {
      const c = document.getElementById("mc-cone-canvas");
      if (c) drawMonteCarloCone(c, mc);
    }, { once: true });
  }
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

// TC holds all Trade Chart tab state: loaded data, replay playback, the
// zoom/pan viewport into the revealed candles, pixel<->price/time mapping,
// active technical indicators (EMA, Volume, VWAP, Bollinger, RSI), and crosshairs.
const TC = {
  tradeId: null, candles: [], overlay: null, annotations: [],
  visibleCount: 0, playing: false, timer: null, speed: 1,
  drawMode: null, pendingPoint: null, geom: null,
  viewStart: 0, viewSize: null, // null viewSize = show the whole revealed range (no zoom)
  dragging: false, dragStartX: 0, dragStartViewStart: 0, suppressNextClick: false,
  hoverPoint: null,
  indicators: {
    ema20: true,
    ema50: false,
    volume: true,
    vwap: false,
    bollinger: false,
    rsi: false,
  },
  ema20: [],
  ema50: [],
  vwap: [],
  bollinger: { upper: [], middle: [], lower: [] },
  rsi: [],
};

const MIN_ZOOM_CANDLES = 8;

function computeEMA(candles, period) {
  if (!candles || !candles.length) return [];
  const k = 2 / (period + 1);
  const result = new Array(candles.length);
  let prev = candles[0].close;
  result[0] = prev;
  for (let i = 1; i < candles.length; i++) {
    prev = candles[i].close * k + prev * (1 - k);
    result[i] = prev;
  }
  return result;
}

function computeVWAP(candles) {
  if (!candles || !candles.length) return [];
  let cumVol = 0;
  let cumVolPrice = 0;
  const result = new Array(candles.length);
  for (let i = 0; i < candles.length; i++) {
    const c = candles[i];
    const vol = c.volume || 1;
    const typicalPrice = (c.high + c.low + c.close) / 3;
    cumVol += vol;
    cumVolPrice += typicalPrice * vol;
    result[i] = cumVolPrice / cumVol;
  }
  return result;
}

function computeBollingerBands(candles, period = 20, numStd = 2) {
  if (!candles || !candles.length) return { upper: [], middle: [], lower: [] };
  const upper = new Array(candles.length);
  const middle = new Array(candles.length);
  const lower = new Array(candles.length);

  for (let i = 0; i < candles.length; i++) {
    const start = Math.max(0, i - period + 1);
    const window = candles.slice(start, i + 1);
    const mean = window.reduce((sum, c) => sum + c.close, 0) / window.length;
    const variance = window.reduce((sum, c) => sum + Math.pow(c.close - mean, 2), 0) / window.length;
    const std = Math.sqrt(variance);
    middle[i] = mean;
    upper[i] = mean + numStd * std;
    lower[i] = mean - numStd * std;
  }
  return { upper, middle, lower };
}

function computeRSI(candles, period = 14) {
  if (!candles || candles.length < 2) return [];
  const rsi = new Array(candles.length).fill(null);
  let gains = 0, losses = 0;

  for (let i = 1; i < candles.length; i++) {
    const diff = candles[i].close - candles[i - 1].close;
    const gain = diff > 0 ? diff : 0;
    const loss = diff < 0 ? -diff : 0;

    if (i <= period) {
      gains += gain;
      losses += loss;
      if (i === period) {
        const avgGain = gains / period;
        const avgLoss = losses / period;
        const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
        rsi[i] = 100 - (100 / (1 + rs));
      }
    } else {
      const prevAvgGain = gains / period;
      const prevAvgLoss = losses / period;
      const avgGain = (prevAvgGain * (period - 1) + gain) / period;
      const avgLoss = (prevAvgLoss * (period - 1) + loss) / period;
      gains = avgGain * period;
      losses = avgLoss * period;
      const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
      rsi[i] = 100 - (100 / (1 + rs));
    }
  }
  return rsi;
}

const DRAW_TOOLS = [
  { type: "TREND_LINE", label: "\u{1F4C8} Trendline" },
  { type: "HORIZONTAL_RAY", label: "\u2796 H-Ray" },
  { type: "RECTANGLE_ZONE", label: "\u25ad Zone" },
  { type: "ARROW_UP", label: "\u2b06\ufe0f Arrow Up" },
  { type: "ARROW_DOWN", label: "\u2b07\ufe0f Arrow Down" },
  { type: "TEXT_NOTE", label: "\u{1F4DD} Note" },
  { type: "ERASER", label: "\u{1F9F9} Eraser" },
];
const HIT_TOLERANCE_PX = 8;

async function viewTradeChart() {
  await Promise.all([loadTrades(), loadStrategies()]);
  const defaultSelectedId = state.selectedTradeId || (state.trades[0] ? state.trades[0].id : null);
  const options = state.trades
    .slice().sort((a, b) => new Date(b.open_time) - new Date(a.open_time))
    .map((t) => `<option value="${t.id}" ${String(t.id) === String(defaultSelectedId) ? "selected" : ""}>${esc(t.symbol)} ${t.direction} \u00b7 ${fmtDate(t.open_time)}</option>`).join("");
  content().innerHTML = `
    <div class="card">
      <div class="toolbar">
        <div class="field" style="margin-bottom:0;min-width:320px"><label>Select Trade</label><select id="tc-trade">${options || "<option>No trades</option>"}</select></div>
        <div class="right">
          <button class="btn btn-sm" id="tc-prev-trade" title="Previous trade">◀ Prev</button>
          <button class="btn btn-sm" id="tc-next-trade" title="Next trade">Next ▶</button>
          <select id="tc-timeframe">${["M1","M5","M15","M30","H1","H4","D1"].map((tf) => `<option ${tf === "M15" ? "selected" : ""}>${tf}</option>`).join("")}</select>
          <button class="btn btn-primary" id="tc-load">Load Chart</button>
        </div>
      </div>

      <div class="toolbar" style="flex-wrap:wrap;gap:8px">
        <div class="right" style="margin-right:auto">
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
        <div class="indicator-toggles">
          <button class="btn-toggle ${TC.indicators.ema20 ? 'active ema20' : ''}" id="tc-toggle-ema20" title="Toggle 20-period Exponential Moving Average"><span class="dot-indicator" style="background:#38bdf8"></span> EMA 20</button>
          <button class="btn-toggle ${TC.indicators.ema50 ? 'active ema50' : ''}" id="tc-toggle-ema50" title="Toggle 50-period Exponential Moving Average"><span class="dot-indicator" style="background:#f59e0b"></span> EMA 50</button>
          <button class="btn-toggle ${TC.indicators.vwap ? 'active vwap' : ''}" id="tc-toggle-vwap" title="Toggle Volume Weighted Average Price"><span class="dot-indicator" style="background:#a855f7"></span> VWAP</button>
          <button class="btn-toggle ${TC.indicators.bollinger ? 'active bollinger' : ''}" id="tc-toggle-bollinger" title="Toggle Bollinger Bands (20, 2)"><span class="dot-indicator" style="background:#38bdf8"></span> BB</button>
          <button class="btn-toggle ${TC.indicators.volume ? 'active volume' : ''}" id="tc-toggle-vol" title="Toggle Volume histogram"><span class="dot-indicator" style="background:var(--win)"></span> Volume</button>
          <button class="btn-toggle ${TC.indicators.rsi ? 'active rsi' : ''}" id="tc-toggle-rsi" title="Toggle Relative Strength Index (14)"><span class="dot-indicator" style="background:#c084fc"></span> RSI</button>
        </div>
        <div class="right">
          ${DRAW_TOOLS.map((t) => `<button class="btn" data-draw="${t.type}">${t.label}</button>`).join("")}
          <button class="btn btn-danger" id="tc-clear-annotations">Clear Drawings</button>
          <button class="btn" id="tc-zoom-in" title="Zoom in">+</button>
          <button class="btn" id="tc-zoom-out" title="Zoom out">−</button>
          <button class="btn" id="tc-fit-zoom" title="Reset zoom/pan to show the whole revealed range">\u{1F50D} Fit</button>
          <button class="btn" id="tc-screenshot">\u{1F4F7} Screenshot</button>
          <button class="btn" id="tc-copy-clipboard">\u{1F4CB} Copy Image</button>
        </div>
      </div>

      <canvas id="tc-canvas" style="width:100%;height:420px;display:block;cursor:crosshair"></canvas>
      <div id="tc-ohlc-bar" class="chart-ohlc-bar">Hover over the chart to inspect bar prices</div>
      <div id="tc-overlay" class="kpi-sub" style="margin-top:12px"></div>
      <div id="tc-trade-meta"></div>
      <div class="kpi-sub text-dim" style="margin-top:4px">Scroll or use +/- to zoom · drag to pan · crosshairs and indicators active.</div>
      <div id="tc-drawhint" class="kpi-sub text-dim" style="margin-top:4px"></div>
    </div>

    <div class="card">
      <div class="card-title">\u{1F4D3} Trade Journal & Classification</div>
      <div class="grid grid-2">
        <div class="field"><label>Setup Name</label><input type="text" id="tj-setup" /></div>
        <div class="field"><label>Grade</label>
          <select id="tj-rating">${["A+","A","B","C","D","F"].map((g) => `<option>${g}</option>`).join("")}</select>
        </div>
      </div>
      <div class="grid grid-2">
        <div class="field"><label>Strategy</label>
          <select id="tj-strategy">
            <option value="">None</option>
            ${state.strategies.map((s) => `<option value="${s.id}">${esc(s.name)}</option>`).join("")}
          </select>
        </div>
        <div class="field"><label>Emotion Tag</label>
          <select id="tj-emotion">
            <option value="">None</option>
            <option value="CALM">😌 Calm</option>
            <option value="FOMO">⚡ FOMO</option>
            <option value="REVENGE">🔥 Revenge</option>
            <option value="GREED">🤑 Greed</option>
            <option value="FEAR">😨 Fear</option>
            <option value="BOREDOM">🥱 Boredom</option>
          </select>
        </div>
      </div>
      <div class="field"><label>Pre-Trade Thesis</label><textarea id="tj-pre" rows="2"></textarea></div>
      <div class="field"><label>Post-Trade Review</label><textarea id="tj-post" rows="2"></textarea></div>
      <div class="field"><label>Lessons Learned</label><textarea id="tj-lessons" rows="2"></textarea></div>
      <div class="field">
        <label>Screenshots & Chart Snapshots</label>
        <div id="tj-screenshots-wrap">
          <div class="kpi-sub" id="tj-screenshots" style="margin-bottom:8px">No screenshots saved yet.</div>
          <div class="screenshot-gallery" id="tj-screenshot-gallery"></div>
        </div>
      </div>
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
  document.getElementById("tc-fit-zoom").addEventListener("click", fitZoom);
  document.getElementById("tc-zoom-in").addEventListener("click", () => zoomChart(1));
  document.getElementById("tc-zoom-out").addEventListener("click", () => zoomChart(-1));
  document.getElementById("tc-screenshot").addEventListener("click", takeScreenshot);
  document.getElementById("tc-copy-clipboard").addEventListener("click", copyChartToClipboard);

  document.getElementById("tc-prev-trade").addEventListener("click", () => stepTrade(1));
  document.getElementById("tc-next-trade").addEventListener("click", () => stepTrade(-1));

  function bindToggle(btnId, indicatorKey, activeClass) {
    const btn = document.getElementById(btnId);
    if (btn) {
      btn.addEventListener("click", () => {
        TC.indicators[indicatorKey] = !TC.indicators[indicatorKey];
        btn.classList.toggle("active", TC.indicators[indicatorKey]);
        btn.classList.toggle(activeClass, TC.indicators[indicatorKey]);
        renderTradeChart();
      });
    }
  }

  bindToggle("tc-toggle-ema20", "ema20", "ema20");
  bindToggle("tc-toggle-ema50", "ema50", "ema50");
  bindToggle("tc-toggle-vwap", "vwap", "vwap");
  bindToggle("tc-toggle-bollinger", "bollinger", "bollinger");
  bindToggle("tc-toggle-vol", "volume", "volume");
  bindToggle("tc-toggle-rsi", "rsi", "rsi");

  const canvas = document.getElementById("tc-canvas");
  canvas.addEventListener("mousedown", onCanvasMouseDown);
  canvas.addEventListener("mousemove", onCanvasMouseMove);
  canvas.addEventListener("mouseleave", () => {
    TC.hoverPoint = null;
    const el = document.getElementById("tc-ohlc-bar");
    if (el) el.textContent = "Hover over the chart to inspect bar prices";
    renderTradeChart();
  });
  window.addEventListener("mouseup", onCanvasMouseUp);
  canvas.addEventListener("click", onCanvasClick);
  canvas.addEventListener("wheel", onCanvasWheel, { passive: false });
  document.getElementById("tj-save").addEventListener("click", saveJournalEntry);

  await loadTradeChart();
}

function stepTrade(delta) {
  const select = document.getElementById("tc-trade");
  if (!select || !select.options.length) return;
  const curIdx = select.selectedIndex;
  const newIdx = curIdx + delta;
  if (newIdx >= 0 && newIdx < select.options.length) {
    select.selectedIndex = newIdx;
    loadTradeChart();
  }
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
  TC.ema20 = computeEMA(TC.candles, 20);
  TC.ema50 = computeEMA(TC.candles, 50);
  TC.vwap = computeVWAP(TC.candles);
  TC.bollinger = computeBollingerBands(TC.candles, 20, 2);
  TC.rsi = computeRSI(TC.candles, 14);
  TC.visibleCount = TC.candles.length; // show the full chart by default; Reset scrubs back for replay
  TC.viewStart = 0;
  TC.viewSize = null; // fresh trade/timeframe always loads fully zoomed out
  TC.hoverPoint = null;
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
  renderScreenshotGallery(note ? note.screenshot_paths : []);

  const currTrade = state.trades.find((x) => String(x.id) === String(tradeId));
  if (currTrade) {
    const sEl = document.getElementById("tj-strategy");
    if (sEl) sEl.value = currTrade.strategy_id || "";
    const eEl = document.getElementById("tj-emotion");
    if (eEl) eEl.value = (currTrade.emotion_tag || "").toUpperCase();
  }
}

function getViewSize(revealedLen) {
  return TC.viewSize || revealedLen;
}
function clampViewStart(revealedLen, viewSize) {
  TC.viewStart = Math.max(0, Math.min(TC.viewStart, Math.max(0, revealedLen - viewSize)));
}
function fitZoom() {
  TC.viewStart = 0;
  TC.viewSize = null;
  renderTradeChart();
}

function zoomChart(step) {
  if (!TC.candles || !TC.candles.length) return;
  const revealed = TC.candles.slice(0, TC.visibleCount);
  const oldViewSize = getViewSize(revealed.length);
  const factor = step > 0 ? 0.75 : 1.33;
  let newViewSize = Math.round(oldViewSize * factor);
  newViewSize = Math.max(MIN_ZOOM_CANDLES, Math.min(revealed.length, newViewSize));
  const centerAbs = TC.viewStart + oldViewSize / 2;
  TC.viewSize = newViewSize >= revealed.length ? null : newViewSize;
  TC.viewStart = Math.round(centerAbs - newViewSize / 2);
  clampViewStart(revealed.length, newViewSize);
  renderTradeChart();
}

function renderTradeChart() {
  const o = TC.overlay;
  if (!o) return;
  document.getElementById("tc-overlay").innerHTML =
    `Entry ${fmtNum(o.entry_price, 5)} \u00b7 Exit ${o.exit_price !== null ? fmtNum(o.exit_price, 5) : "\u2014"} \u00b7 ` +
    `SL ${o.initial_sl !== null ? fmtNum(o.initial_sl, 5) : "\u2014"} \u00b7 TP ${o.initial_tp !== null ? fmtNum(o.initial_tp, 5) : "\u2014"} \u00b7 ` +
    `R: ${o.realized_r !== null ? fmtNum(o.realized_r, 2) : "unknown"} \u00b7 Bar ${TC.visibleCount}/${TC.candles.length}`;

  const metaEl = document.getElementById("tc-trade-meta");
  if (metaEl && TC.tradeId) {
    const t = state.trades.find((x) => String(x.id) === String(TC.tradeId));
    if (t) {
      const pl = t.net_profit ?? t.profit ?? 0;
      const isWin = pl >= 0;
      const pnlColor = isWin ? "var(--color-win)" : "var(--color-loss)";
      const dirBadge = (t.direction || "").toUpperCase() === "BUY"
        ? '<span class="badge badge-win">▲ BUY</span>'
        : '<span class="badge badge-loss">▼ SELL</span>';
      const strat = state.strategies.find((s) => s.id === t.strategy_id);
      const stratName = strat ? strat.name : (t.strategy_id ? `Strategy #${t.strategy_id}` : "Unclassified");
      const rVal = t.realized_r !== null && t.realized_r !== undefined ? `${fmtNum(t.realized_r, 2)}R` : "—";
      const volVal = t.volume ? `${fmtVolume(t.volume)} lots` : "—";
      const durVal = t.duration_minutes ? (t.duration_minutes >= 60 ? `${Math.floor(t.duration_minutes / 60)}h ${Math.round(t.duration_minutes % 60)}m` : `${Math.round(t.duration_minutes)}m`) : "—";

      metaEl.innerHTML = `
        <div class="trade-meta-strip">
          <div class="trade-meta-item"><strong>${esc(t.symbol)}</strong> ${dirBadge}</div>
          <div class="trade-meta-item">Volume: <strong>${volVal}</strong></div>
          <div class="trade-meta-item">PnL: <strong style="color:${pnlColor}">${fmtNum(pl, 2)}</strong></div>
          <div class="trade-meta-item">Return: <strong>${rVal}</strong></div>
          <div class="trade-meta-item">Strategy: <strong>${esc(stratName)}</strong></div>
          <div class="trade-meta-item">Duration: <strong>${durVal}</strong></div>
          <div class="trade-meta-item">Opened: <strong>${fmtDate(t.open_time)}</strong></div>
        </div>
      `;
    } else {
      metaEl.innerHTML = "";
    }
  }

  const revealed = TC.candles.slice(0, TC.visibleCount);
  const viewSize = getViewSize(revealed.length);
  clampViewStart(revealed.length, viewSize);
  const visible = revealed.slice(TC.viewStart, TC.viewStart + viewSize);
  drawCandles(document.getElementById("tc-canvas"), visible, TC.overlay, TC.annotations);
}

// ------------------------------------------------------------- zoom & pan

function onCanvasWheel(evt) {
  if (!TC.geom || !TC.candles.length) return;
  evt.preventDefault();
  const revealed = TC.candles.slice(0, TC.visibleCount);
  const oldViewSize = getViewSize(revealed.length);
  const rect = evt.target.getBoundingClientRect();
  const cursorX = evt.clientX - rect.left;
  const plotW = TC.geom.plotWidth || rect.width;
  if (cursorX > plotW) return;
  const cursorIndexAbs = TC.viewStart + cursorX / TC.geom.cw;

  const normalizedDelta = Math.min(Math.max(evt.deltaY, -100), 100);
  const factor = Math.exp(normalizedDelta * 0.0018);
  let newViewSize = Math.round(oldViewSize * factor);
  if (newViewSize === oldViewSize) {
    newViewSize = evt.deltaY < 0 ? oldViewSize - 1 : oldViewSize + 1;
  }
  newViewSize = Math.max(MIN_ZOOM_CANDLES, Math.min(revealed.length, newViewSize));
  const cursorRatio = Math.max(0, Math.min(1, cursorX / plotW));
  TC.viewSize = newViewSize >= revealed.length ? null : newViewSize;
  TC.viewStart = Math.round(cursorIndexAbs - cursorRatio * newViewSize);
  clampViewStart(revealed.length, newViewSize);
  renderTradeChart();
}

function onCanvasMouseDown(evt) {
  if (TC.drawMode) return; // drawing takes priority over panning
  TC.dragging = true;
  TC.dragMoved = false;
  TC.dragStartX = evt.clientX;
  TC.dragStartViewStart = TC.viewStart;
  const canvas = document.getElementById("tc-canvas");
  if (canvas) canvas.style.cursor = "grabbing";
}

function onCanvasMouseMove(evt) {
  const rect = evt.target.getBoundingClientRect();
  const x = evt.clientX - rect.left;
  const y = evt.clientY - rect.top;

  if (TC.geom && TC.candles && TC.candles.length) {
    const revealed = TC.candles.slice(0, TC.visibleCount);
    const viewSize = getViewSize(revealed.length);
    clampViewStart(revealed.length, viewSize);
    const visible = revealed.slice(TC.viewStart, TC.viewStart + viewSize);
    const plotW = TC.geom.plotWidth || rect.width;
    const cw = plotW / (visible.length || 1);
    const idx = Math.floor(x / cw);

    if (x >= 0 && x <= plotW && y >= 0 && y <= rect.height) {
      TC.hoverPoint = { x, y };
    } else {
      TC.hoverPoint = null;
    }

    const ohlcEl = document.getElementById("tc-ohlc-bar");
    if (ohlcEl && visible[idx]) {
      const c = visible[idx];
      const diff = c.close - c.open;
      const pct = c.open ? ((diff / c.open) * 100).toFixed(2) : "0.00";
      const changeStr = diff >= 0 ? `+${fmtNum(diff, 5)} (+${pct}%)` : `${fmtNum(diff, 5)} (${pct}%)`;
      const color = diff >= 0 ? "var(--color-win)" : "var(--color-loss)";
      const volStr = c.volume ? ` \u00b7 Vol: <strong>${c.volume.toLocaleString()}</strong>` : "";
      let extra = "";
      const barAbsIdx = (TC.viewStart || 0) + idx;
      if (TC.indicators && TC.indicators.vwap && TC.vwap && TC.vwap[barAbsIdx] !== undefined) {
        extra += ` \u00b7 <span style="color:#a855f7">VWAP: <strong>${fmtNum(TC.vwap[barAbsIdx], 5)}</strong></span>`;
      }
      if (TC.indicators && TC.indicators.rsi && TC.rsi && TC.rsi[barAbsIdx] !== null && TC.rsi[barAbsIdx] !== undefined) {
        extra += ` \u00b7 <span style="color:#c084fc">RSI: <strong>${TC.rsi[barAbsIdx].toFixed(1)}</strong></span>`;
      }
      ohlcEl.innerHTML = `<span><strong>${c.timestamp.replace("T", " ").slice(0, 19)}</strong></span> \u00b7 ` +
        `O: <strong>${fmtNum(c.open, 5)}</strong> \u00b7 H: <strong>${fmtNum(c.high, 5)}</strong> \u00b7 ` +
        `L: <strong>${fmtNum(c.low, 5)}</strong> \u00b7 C: <strong>${fmtNum(c.close, 5)}</strong> \u00b7 ` +
        `<span style="color:${color}">\u0394 ${changeStr}</span>${volStr}${extra}`;
    }
  }

  if (TC.dragging && TC.geom) {
    const dx = evt.clientX - TC.dragStartX;
    if (Math.abs(dx) > 3) TC.dragMoved = true;
    const revealed = TC.candles.slice(0, TC.visibleCount);
    const viewSize = getViewSize(revealed.length);
    TC.viewStart = TC.dragStartViewStart + Math.round(-dx / TC.geom.cw);
    clampViewStart(revealed.length, viewSize);
    renderTradeChart();
    return;
  }

  if (!TC.drawMode && !TC.dragging) {
    renderTradeChart();
  }
}

function onCanvasMouseUp() {
  if (TC.dragging && TC.dragMoved) TC.suppressNextClick = true;
  TC.dragging = false;
  const canvas = document.getElementById("tc-canvas");
  if (canvas) canvas.style.cursor = "crosshair";
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

const ONE_CLICK_TOOLS = new Set(["TEXT_NOTE", "HORIZONTAL_RAY", "ARROW_UP", "ARROW_DOWN"]);

function setDrawMode(type) {
  TC.drawMode = (TC.drawMode === type) ? null : type;
  TC.pendingPoint = null;
  document.querySelectorAll("[data-draw]").forEach((b) => b.classList.toggle("btn-primary", b.dataset.draw === TC.drawMode));
  const hint = document.getElementById("tc-drawhint");
  if (!TC.drawMode) { hint.textContent = ""; return; }
  if (TC.drawMode === "ERASER") { hint.textContent = "Click an existing annotation to erase just that one."; return; }
  hint.textContent = ONE_CLICK_TOOLS.has(TC.drawMode)
    ? "Click on the chart to place it."
    : "Click two points on the chart to draw.";
}

// ------------------------------------------------------------- eraser (per-annotation hit test)

function pointToSegmentDistance(px, py, x1, y1, x2, y2) {
  const dx = x2 - x1, dy = y2 - y1;
  const lenSq = dx * dx + dy * dy;
  let t = lenSq === 0 ? 0 : ((px - x1) * dx + (py - y1) * dy) / lenSq;
  t = Math.max(0, Math.min(1, t));
  return Math.hypot(px - (x1 + t * dx), py - (y1 + t * dy));
}

function annotationHitDistance(a, px, py) {
  const g = TC.geom;
  if (a.annotation_type === "TREND_LINE") {
    return pointToSegmentDistance(px, py, g.timeToX(a.p1_time), g.priceToY(a.p1_price), g.timeToX(a.p2_time), g.priceToY(a.p2_price));
  }
  if (a.annotation_type === "HORIZONTAL_RAY") {
    const x1 = g.timeToX(a.p1_time);
    if (px < x1 - HIT_TOLERANCE_PX) return Infinity;
    return Math.abs(py - g.priceToY(a.p1_price));
  }
  if (a.annotation_type === "RECTANGLE_ZONE") {
    const x1 = g.timeToX(a.p1_time), x2 = g.timeToX(a.p2_time);
    const y1 = g.priceToY(a.p1_price), y2 = g.priceToY(a.p2_price);
    const inside = px >= Math.min(x1, x2) - HIT_TOLERANCE_PX && px <= Math.max(x1, x2) + HIT_TOLERANCE_PX
      && py >= Math.min(y1, y2) - HIT_TOLERANCE_PX && py <= Math.max(y1, y2) + HIT_TOLERANCE_PX;
    return inside ? 0 : Infinity;
  }
  // ARROW_UP, ARROW_DOWN, TEXT_NOTE: distance to the anchor point
  return Math.hypot(px - g.timeToX(a.p1_time), py - g.priceToY(a.p1_price));
}

function findAnnotationAt(px, py) {
  if (!TC.geom) return null;
  let best = null, bestDist = HIT_TOLERANCE_PX;
  for (const a of TC.annotations) {
    const dist = annotationHitDistance(a, px, py);
    if (dist < bestDist) { bestDist = dist; best = a; }
  }
  return best;
}

async function deleteAnnotationById(id) {
  try {
    await api(`/annotations/${id}`, { method: "DELETE" });
    TC.annotations = TC.annotations.filter((a) => a.id !== id);
    renderTradeChart();
    showTransientBanner("Annotation erased.", true);
  } catch (e) { showTransientBanner(e.message, false); }
}

async function onCanvasClick(evt) {
  if (TC.suppressNextClick) { TC.suppressNextClick = false; return; }
  if (!TC.drawMode || !TC.geom) return;
  const rect = evt.target.getBoundingClientRect();
  const x = evt.clientX - rect.left, y = evt.clientY - rect.top;

  if (TC.drawMode === "ERASER") {
    const hit = findAnnotationAt(x, y);
    if (hit) await deleteAnnotationById(hit.id);
    else showTransientBanner("No annotation there - click closer to a line or shape.", false);
    return;
  }

  const point = { time: TC.geom.timeAt(x), price: TC.geom.priceAt(y) };

  if (ONE_CLICK_TOOLS.has(TC.drawMode)) {
    if (TC.drawMode === "TEXT_NOTE") {
      const text = prompt("Note text:");
      if (!text) return;
      await postAnnotation({ annotation_type: "TEXT_NOTE", p1_time: point.time, p1_price: point.price, p2_time: point.time, p2_price: point.price, text });
      return;
    }
    await postAnnotation({ annotation_type: TC.drawMode, p1_time: point.time, p1_price: point.price, p2_time: point.time, p2_price: point.price });
    return;
  }

  // Two-click tools: TREND_LINE, RECTANGLE_ZONE
  if (!TC.pendingPoint) { TC.pendingPoint = point; return; }
  await postAnnotation({ annotation_type: TC.drawMode, p1_time: TC.pendingPoint.time, p1_price: TC.pendingPoint.price, p2_time: point.time, p2_price: point.price });
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

function getScreenshotFilename(pathStr) {
  if (!pathStr) return "";
  const normalized = pathStr.replace(/\\/g, "/");
  return normalized.split("/").pop() || "";
}

function getScreenshotUrl(filename) {
  const token = window.__TA_TOKEN__ || "";
  return `/api/screenshots/${encodeURIComponent(filename)}${token ? `?token=${encodeURIComponent(token)}` : ""}`;
}

function renderScreenshotGallery(screenshotPaths) {
  const galleryEl = document.getElementById("tj-screenshot-gallery");
  const countEl = document.getElementById("tj-screenshots");
  if (!galleryEl || !countEl) return;

  const validPaths = (screenshotPaths || []).filter(Boolean);
  if (!validPaths.length) {
    countEl.textContent = "No screenshots captured yet. Click '📸 Screenshot' above to capture a chart snapshot.";
    galleryEl.innerHTML = "";
    return;
  }

  countEl.textContent = `${validPaths.length} screenshot(s) saved for this trade:`;
  galleryEl.innerHTML = validPaths.map((p) => {
    const fn = getScreenshotFilename(p);
    const url = getScreenshotUrl(fn);
    return `
      <div class="screenshot-card" data-filename="${esc(fn)}">
        <div class="screenshot-thumb-wrap" onclick="openScreenshotLightbox('${esc(url)}', '${esc(fn)}')">
          <img class="screenshot-thumb" src="${esc(url)}" alt="Chart Screenshot" loading="lazy" />
          <div class="screenshot-overlay"><span class="screenshot-zoom-icon">🔍 View Full Size</span></div>
        </div>
        <div class="screenshot-meta">
          <span class="screenshot-name" title="${esc(fn)}">${esc(fn)}</span>
          <div class="screenshot-btns">
            <button type="button" class="btn-subtle" onclick="openScreenshotLightbox('${esc(url)}', '${esc(fn)}')" title="Preview full size">🔍</button>
            <a href="${esc(url)}" download="${esc(fn)}" class="btn-subtle" title="Download image" target="_blank" rel="noopener">📥</a>
            <button type="button" class="btn-danger-subtle" onclick="deleteScreenshot('${esc(fn)}')" title="Delete screenshot">🗑️</button>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

function openScreenshotLightbox(url, fn) {
  let modal = document.getElementById("screenshot-lightbox");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "screenshot-lightbox";
    modal.className = "screenshot-lightbox";
    modal.innerHTML = `
      <div class="screenshot-lightbox-backdrop"></div>
      <div class="screenshot-lightbox-content">
        <div class="screenshot-lightbox-header">
          <span id="sl-title" class="screenshot-lightbox-title"></span>
          <div class="screenshot-lightbox-actions">
            <a id="sl-download" href="#" download class="btn btn-sm" target="_blank" rel="noopener">📥 Download</a>
            <button type="button" class="btn btn-sm" id="sl-close">✕ Close</button>
          </div>
        </div>
        <div class="screenshot-lightbox-body">
          <img id="sl-img" src="" alt="Screenshot Full View" />
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    modal.querySelector(".screenshot-lightbox-backdrop").addEventListener("click", closeScreenshotLightbox);
    modal.querySelector("#sl-close").addEventListener("click", closeScreenshotLightbox);
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && modal.classList.contains("active")) {
        closeScreenshotLightbox();
      }
    });
  }

  document.getElementById("sl-title").textContent = fn;
  const imgEl = document.getElementById("sl-img");
  imgEl.src = url;
  const dlEl = document.getElementById("sl-download");
  dlEl.href = url;
  dlEl.download = fn;
  modal.classList.add("active");
}

function closeScreenshotLightbox() {
  const modal = document.getElementById("screenshot-lightbox");
  if (modal) {
    modal.classList.remove("active");
    const imgEl = document.getElementById("sl-img");
    if (imgEl) imgEl.src = "";
  }
}

async function deleteScreenshot(fn) {
  if (!confirm(`Delete screenshot "${fn}"?`)) return;
  try {
    const res = await api(`/trades/${TC.tradeId}/screenshots/${encodeURIComponent(fn)}`, { method: "DELETE" });
    renderScreenshotGallery(res.note ? res.note.screenshot_paths : []);
    showTransientBanner("Screenshot deleted.", true);
  } catch (e) {
    showTransientBanner("Could not delete screenshot: " + e.message, false);
  }
}

async function takeScreenshot() {
  const canvas = document.getElementById("tc-canvas");
  try {
    const dataUrl = canvas.toDataURL("image/png");
    const res = await apiPost(`/trades/${TC.tradeId}/screenshot`, { image_base64: dataUrl });
    renderScreenshotGallery(res.note ? res.note.screenshot_paths : []);
    showTransientBanner("Screenshot saved and added to gallery!", true);
  } catch (e) { showTransientBanner(e.message, false); }
}

function canvasToBlob(canvas) {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error("Could not encode chart image."))), "image/png");
  });
}

async function copyChartToClipboard() {
  const canvas = document.getElementById("tc-canvas");
  if (!navigator.clipboard || !window.ClipboardItem) {
    showTransientBanner("Clipboard image copy isn't supported in this environment.", false);
    return;
  }
  try {
    const blob = await canvasToBlob(canvas);
    await navigator.clipboard.write([new ClipboardItem({ [blob.type]: blob })]);
    showTransientBanner("✅ Chart image copied to clipboard!", true);
  } catch (e) {
    showTransientBanner("Could not copy chart image: " + e.message, false);
  }
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

    const stratEl = document.getElementById("tj-strategy");
    const emoEl = document.getElementById("tj-emotion");
    if (stratEl || emoEl) {
      const stratVal = stratEl ? stratEl.value : "";
      const emoVal = emoEl ? emoEl.value : "";

      try {
        await apiPost(`/trades/${TC.tradeId}/assign-strategy`, {
          strategy_id: stratVal ? parseInt(stratVal, 10) : null,
        });
      } catch (err) { /* ignore if unconfigured */ }

      try {
        await apiPost(`/trades/${TC.tradeId}/emotion`, {
          emotion_tag: emoVal || null,
        });
      } catch (err) { /* ignore if unconfigured */ }

      const t = state.trades.find((x) => String(x.id) === String(TC.tradeId));
      if (t) {
        t.strategy_id = stratVal ? parseInt(stratVal, 10) : null;
        t.emotion_tag = emoVal || null;
      }
    }

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

  const priceScaleW = 68;
  const pw = Math.max(100, w - priceScaleW);
  const showVol = Boolean(TC.indicators && TC.indicators.volume);
  const showRSI = Boolean(TC.indicators && TC.indicators.rsi);
  const volH = showVol ? Math.min(65, Math.floor(h * 0.18)) : 0;
  const rsiH = showRSI ? Math.min(75, Math.floor(h * 0.20)) : 0;
  const chartH = h - volH - rsiH;

  const highs = candles.map((c) => c.high), lows = candles.map((c) => c.low);
  let min = Math.min(...lows), max = Math.max(...highs);
  if (overlay && overlay.initial_sl) { min = Math.min(min, overlay.initial_sl); max = Math.max(max, overlay.initial_sl); }
  if (overlay && overlay.initial_tp) { min = Math.min(min, overlay.initial_tp); max = Math.max(max, overlay.initial_tp); }
  const startIdx = TC.viewStart || 0;
  if (TC.indicators && TC.indicators.bollinger && TC.bollinger && TC.bollinger.upper) {
    for (let i = 0; i < candles.length; i++) {
      const up = TC.bollinger.upper[startIdx + i];
      const lo = TC.bollinger.lower[startIdx + i];
      if (up !== undefined && up !== null) max = Math.max(max, up);
      if (lo !== undefined && lo !== null) min = Math.min(min, lo);
    }
  }
  const pad = (max - min) * 0.08 || 0.0001;
  min -= pad; max += pad;
  const range = max - min;
  const cw = pw / candles.length;

  const y = (price) => chartH - 12 - ((price - min) / range) * (chartH - 24);
  const priceAt = (py) => min + ((chartH - 12 - py) / (chartH - 24)) * range;
  const timestamps = candles.map((c) => new Date(c.timestamp).getTime());
  const xAt = (isoTime) => {
    const t = new Date(isoTime).getTime();
    let idx = timestamps.findIndex((ct) => ct >= t);
    if (idx === -1) idx = timestamps.length - 1;
    return Math.max(cw / 2, Math.min(pw - cw / 2, idx * cw + cw / 2));
  };
  const timeAt = (px) => {
    const idx = Math.max(0, Math.min(candles.length - 1, Math.floor(px / cw)));
    return candles[idx].timestamp;
  };
  TC.geom = { priceAt, timeAt, cw, timeToX: xAt, priceToY: y, plotWidth: pw };

  // Draw Horizontal Gridlines & Price Scale Ticks
  const gridCount = 5;
  ctx.strokeStyle = "rgba(255, 255, 255, 0.04)";
  ctx.lineWidth = 1;
  ctx.setLineDash([3, 4]);
  ctx.font = "10.5px Cascadia Code, Consolas, monospace";
  ctx.fillStyle = "#8b949e";
  for (let g = 0; g <= gridCount; g++) {
    const pVal = min + (range * g) / gridCount;
    const yy = y(pVal);
    if (yy >= 8 && yy <= chartH - 8) {
      ctx.beginPath();
      ctx.moveTo(0, yy);
      ctx.lineTo(pw, yy);
      ctx.stroke();
      ctx.fillText(fmtNum(pVal, 5), pw + 6, yy + 3.5);
    }
  }
  ctx.setLineDash([]);

  // Draw Vertical Right Price Scale Separator
  ctx.strokeStyle = "rgba(48, 54, 61, 0.65)";
  ctx.beginPath();
  ctx.moveTo(pw, 0);
  ctx.lineTo(pw, h);
  ctx.stroke();

  // Draw Risk:Reward Zone Box (Shaded Profit & Risk Zones)
  if (overlay && overlay.entry_price !== null && overlay.entry_price !== undefined) {
    const entryX = xAt(overlay.entry_time);
    let exitX = overlay.exit_time ? xAt(overlay.exit_time) : pw;
    if (exitX <= entryX) exitX = Math.min(pw, entryX + cw * 6);
    const boxW = Math.max(cw * 2, exitX - entryX);

    // Target Profit Zone (Green)
    if (overlay.initial_tp) {
      const tpY = y(overlay.initial_tp);
      const entY = y(overlay.entry_price);
      const topY = Math.min(tpY, entY);
      const zoneH = Math.max(2, Math.abs(tpY - entY));
      ctx.fillStyle = "rgba(38, 166, 154, 0.10)";
      ctx.fillRect(entryX, topY, boxW, zoneH);
      ctx.strokeStyle = "rgba(38, 166, 154, 0.35)";
      ctx.strokeRect(entryX, topY, boxW, zoneH);
    }

    // Stop Loss Zone (Red)
    if (overlay.initial_sl) {
      const slY = y(overlay.initial_sl);
      const entY = y(overlay.entry_price);
      const topY = Math.min(slY, entY);
      const zoneH = Math.max(2, Math.abs(slY - entY));
      ctx.fillStyle = "rgba(239, 83, 80, 0.10)";
      ctx.fillRect(entryX, topY, boxW, zoneH);
      ctx.strokeStyle = "rgba(239, 83, 80, 0.35)";
      ctx.strokeRect(entryX, topY, boxW, zoneH);
    }
  }

  // Draw Bollinger Bands (20, 2)
  if (TC.indicators && TC.indicators.bollinger && TC.bollinger && TC.bollinger.upper && TC.bollinger.upper.length) {
    ctx.fillStyle = "rgba(56, 189, 248, 0.06)";
    ctx.beginPath();
    let started = false;
    for (let i = 0; i < candles.length; i++) {
      const up = TC.bollinger.upper[startIdx + i];
      if (up === null || up === undefined) continue;
      const ex = i * cw + cw / 2;
      const ey = y(up);
      if (!started) { ctx.moveTo(ex, ey); started = true; }
      else { ctx.lineTo(ex, ey); }
    }
    for (let i = candles.length - 1; i >= 0; i--) {
      const lo = TC.bollinger.lower[startIdx + i];
      if (lo === null || lo === undefined) continue;
      const ex = i * cw + cw / 2;
      const ey = y(lo);
      ctx.lineTo(ex, ey);
    }
    ctx.closePath();
    ctx.fill();

    ctx.strokeStyle = "rgba(56, 189, 248, 0.65)";
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    started = false;
    for (let i = 0; i < candles.length; i++) {
      const up = TC.bollinger.upper[startIdx + i];
      if (up === null || up === undefined) continue;
      const ex = i * cw + cw / 2;
      const ey = y(up);
      if (!started) { ctx.moveTo(ex, ey); started = true; }
      else { ctx.lineTo(ex, ey); }
    }
    ctx.stroke();

    ctx.beginPath();
    started = false;
    for (let i = 0; i < candles.length; i++) {
      const lo = TC.bollinger.lower[startIdx + i];
      if (lo === null || lo === undefined) continue;
      const ex = i * cw + cw / 2;
      const ey = y(lo);
      if (!started) { ctx.moveTo(ex, ey); started = true; }
      else { ctx.lineTo(ex, ey); }
    }
    ctx.stroke();

    ctx.strokeStyle = "rgba(56, 189, 248, 0.4)";
    ctx.setLineDash([3, 3]);
    ctx.beginPath();
    started = false;
    for (let i = 0; i < candles.length; i++) {
      const mid = TC.bollinger.middle[startIdx + i];
      if (mid === null || mid === undefined) continue;
      const ex = i * cw + cw / 2;
      const ey = y(mid);
      if (!started) { ctx.moveTo(ex, ey); started = true; }
      else { ctx.lineTo(ex, ey); }
    }
    ctx.stroke();
    ctx.setLineDash([]);
  }

  // Draw Candlestick Bars
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

  // Draw EMA Indicators
  if (TC.indicators && TC.indicators.ema20 && TC.ema20 && TC.ema20.length) {
    ctx.strokeStyle = "#38bdf8";
    ctx.lineWidth = 1.8;
    ctx.beginPath();
    let started = false;
    for (let i = 0; i < candles.length; i++) {
      const val = TC.ema20[startIdx + i];
      if (val === null || val === undefined) continue;
      const ex = i * cw + cw / 2;
      const ey = y(val);
      if (!started) { ctx.moveTo(ex, ey); started = true; }
      else { ctx.lineTo(ex, ey); }
    }
    ctx.stroke();
  }

  if (TC.indicators && TC.indicators.ema50 && TC.ema50 && TC.ema50.length) {
    ctx.strokeStyle = "#f59e0b";
    ctx.lineWidth = 1.8;
    ctx.beginPath();
    let started = false;
    for (let i = 0; i < candles.length; i++) {
      const val = TC.ema50[startIdx + i];
      if (val === null || val === undefined) continue;
      const ex = i * cw + cw / 2;
      const ey = y(val);
      if (!started) { ctx.moveTo(ex, ey); started = true; }
      else { ctx.lineTo(ex, ey); }
    }
    ctx.stroke();
  }

  // Draw VWAP Indicator
  if (TC.indicators && TC.indicators.vwap && TC.vwap && TC.vwap.length) {
    ctx.strokeStyle = "#a855f7";
    ctx.lineWidth = 1.8;
    ctx.beginPath();
    let started = false;
    for (let i = 0; i < candles.length; i++) {
      const val = TC.vwap[startIdx + i];
      if (val === null || val === undefined) continue;
      const ex = i * cw + cw / 2;
      const ey = y(val);
      if (!started) { ctx.moveTo(ex, ey); started = true; }
      else { ctx.lineTo(ex, ey); }
    }
    ctx.stroke();
  }

  // Draw Volume Histogram Sub-Pane
  if (showVol) {
    const volBaseY = chartH;
    ctx.strokeStyle = "rgba(48, 54, 61, 0.75)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, volBaseY);
    ctx.lineTo(pw, volBaseY);
    ctx.stroke();

    ctx.fillStyle = "#8b949e";
    ctx.font = "bold 9.5px Segoe UI";
    ctx.fillText("VOLUME", 8, volBaseY + 14);

    let maxV = 1;
    for (const c of candles) {
      if (c.volume && c.volume > maxV) maxV = c.volume;
    }

    candles.forEach((c, i) => {
      const vol = c.volume || 0;
      const x = i * cw + cw / 2;
      const barH = Math.max(2, (vol / maxV) * (volH - 22));
      const barY = volBaseY + volH - barH - 4;
      const up = c.close >= c.open;
      ctx.fillStyle = up ? "rgba(38, 166, 154, 0.4)" : "rgba(239, 83, 80, 0.4)";
      ctx.fillRect(x - cw * 0.35, barY, cw * 0.7, barH);
      ctx.strokeStyle = up ? "rgba(38, 166, 154, 0.85)" : "rgba(239, 83, 80, 0.85)";
      ctx.lineWidth = 0.8;
      ctx.strokeRect(x - cw * 0.35, barY, cw * 0.7, barH);
    });
  }

  // Draw RSI Sub-Pane
  if (showRSI) {
    const rsiBaseY = chartH + volH;
    ctx.strokeStyle = "rgba(48, 54, 61, 0.75)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, rsiBaseY);
    ctx.lineTo(pw, rsiBaseY);
    ctx.stroke();

    ctx.fillStyle = "#c084fc";
    ctx.font = "bold 9.5px Segoe UI";
    ctx.fillText("RSI (14)", 8, rsiBaseY + 13);

    const rsiY = (val) => rsiBaseY + 12 + ((100 - val) / 100) * (rsiH - 20);

    ctx.fillStyle = "rgba(192, 132, 252, 0.05)";
    ctx.fillRect(0, rsiY(70), pw, rsiY(30) - rsiY(70));

    ctx.setLineDash([2, 3]);
    [70, 50, 30].forEach((level) => {
      const yy = rsiY(level);
      ctx.strokeStyle = level === 50 ? "rgba(255, 255, 255, 0.08)" : "rgba(192, 132, 252, 0.25)";
      ctx.beginPath();
      ctx.moveTo(0, yy);
      ctx.lineTo(pw, yy);
      ctx.stroke();

      if (level !== 50) {
        ctx.fillStyle = "rgba(192, 132, 252, 0.7)";
        ctx.font = "9px Cascadia Code, Consolas, monospace";
        ctx.fillText(String(level), pw + 6, yy + 3);
      }
    });
    ctx.setLineDash([]);

    if (TC.rsi && TC.rsi.length) {
      ctx.strokeStyle = "#c084fc";
      ctx.lineWidth = 1.8;
      ctx.beginPath();
      let started = false;
      for (let i = 0; i < candles.length; i++) {
        const val = TC.rsi[startIdx + i];
        if (val === null || val === undefined) continue;
        const rx = i * cw + cw / 2;
        const ry = rsiY(val);
        if (!started) { ctx.moveTo(rx, ry); started = true; }
        else { ctx.lineTo(rx, ry); }
      }
      ctx.stroke();
    }
  }

  // Draw Entry & SL/TP Levels
  function hline(price, color, label) {
    if (price === null || price === undefined) return;
    const yy = y(price);
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.2;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(0, yy);
    ctx.lineTo(pw, yy);
    ctx.stroke();
    ctx.setLineDash([]);

    ctx.fillStyle = color;
    ctx.fillRect(pw, yy - 8, priceScaleW, 16);
    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 9.5px Segoe UI, Cascadia Code, monospace";
    ctx.fillText(label, pw + 4, yy + 3.5);
  }

  if (overlay) {
    hline(overlay.entry_price, "#58a6ff", "Entry");
    hline(overlay.initial_sl, "#ef5350", "SL");
    hline(overlay.initial_tp, "#26a69a", "TP");

    // Entry Marker Badge
    if (overlay.entry_price !== null && overlay.entry_time) {
      const ex = xAt(overlay.entry_time);
      const ey = y(overlay.entry_price);
      const isBuy = (overlay.direction || "").toUpperCase() === "BUY";
      ctx.fillStyle = isBuy ? "#26a69a" : "#ef5350";
      ctx.font = "bold 10px Segoe UI";
      const badgeText = isBuy ? "▲ BUY" : "▼ SELL";
      const bw = ctx.measureText(badgeText).width + 8;
      const by = isBuy ? ey + 10 : ey - 22;
      ctx.fillRect(ex - bw / 2, by, bw, 15);
      ctx.fillStyle = "#ffffff";
      ctx.fillText(badgeText, ex - bw / 2 + 4, by + 11);
    }

    // Exit Marker Badge
    if (overlay.exit_price !== null && overlay.exit_time) {
      const xx = xAt(overlay.exit_time);
      const xy = y(overlay.exit_price);
      const isWin = (overlay.net_profit ?? 0) >= 0;
      ctx.fillStyle = isWin ? "#26a69a" : "#ef5350";
      ctx.font = "bold 10px Segoe UI";
      const rText = overlay.realized_r !== null ? ` ${fmtNum(overlay.realized_r, 2)}R` : "";
      const exitText = `✕ Exit${rText}`;
      const xw = ctx.measureText(exitText).width + 8;
      ctx.fillRect(xx - xw / 2, xy - 8, xw, 16);
      ctx.fillStyle = "#ffffff";
      ctx.fillText(exitText, xx - xw / 2 + 4, xy + 4);
    }
  }

  // Draw Annotations
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
      ctx.lineTo(pw, yy);
      ctx.stroke();
    } else if (a.annotation_type === "RECTANGLE_ZONE") {
      const x1 = xAt(a.p1_time), x2 = xAt(a.p2_time);
      const y1 = y(a.p1_price), y2 = y(a.p2_price);
      const rx = Math.min(x1, x2), ry = Math.min(y1, y2);
      const rw = Math.abs(x2 - x1) || cw, rh = Math.abs(y2 - y1) || 1;
      ctx.globalAlpha = 0.15;
      ctx.fillRect(rx, ry, rw, rh);
      ctx.globalAlpha = 1;
      ctx.strokeRect(rx, ry, rw, rh);
    } else if (a.annotation_type === "ARROW_UP" || a.annotation_type === "ARROW_DOWN") {
      const ax = xAt(a.p1_time), ay = y(a.p1_price);
      const dir = a.annotation_type === "ARROW_UP" ? -1 : 1;
      const size = 10;
      ctx.beginPath();
      ctx.moveTo(ax, ay);
      ctx.lineTo(ax - size * 0.6, ay - dir * size);
      ctx.lineTo(ax + size * 0.6, ay - dir * size);
      ctx.closePath();
      ctx.fill();
      if (a.text) ctx.fillText(a.text, ax + size, ay - dir * size);
    } else if (a.annotation_type === "TEXT_NOTE") {
      ctx.fillText(a.text || "\u{1F4CC}", xAt(a.p1_time), y(a.p1_price));
    }
    ctx.lineWidth = 1;
  });

  // Draw Legend Badges (Top-Left)
  let legX = 12;
  const lastBarIdx = candles.length - 1;
  ctx.font = "bold 11px Segoe UI";
  if (TC.indicators && TC.indicators.ema20 && TC.ema20 && candles[lastBarIdx]) {
    const val = TC.ema20[startIdx + lastBarIdx];
    if (val !== undefined && val !== null) {
      ctx.fillStyle = "#38bdf8";
      const txt = `EMA 20: ${fmtNum(val, 5)}`;
      ctx.fillText(txt, legX, 20);
      legX += ctx.measureText(txt).width + 16;
    }
  }
  if (TC.indicators && TC.indicators.ema50 && TC.ema50 && candles[lastBarIdx]) {
    const val = TC.ema50[startIdx + lastBarIdx];
    if (val !== undefined && val !== null) {
      ctx.fillStyle = "#f59e0b";
      const txt = `EMA 50: ${fmtNum(val, 5)}`;
      ctx.fillText(txt, legX, 20);
      legX += ctx.measureText(txt).width + 16;
    }
  }
  if (TC.indicators && TC.indicators.vwap && TC.vwap && candles[lastBarIdx]) {
    const val = TC.vwap[startIdx + lastBarIdx];
    if (val !== undefined && val !== null) {
      ctx.fillStyle = "#a855f7";
      const txt = `VWAP: ${fmtNum(val, 5)}`;
      ctx.fillText(txt, legX, 20);
      legX += ctx.measureText(txt).width + 16;
    }
  }
  if (TC.indicators && TC.indicators.bollinger && TC.bollinger && TC.bollinger.upper && candles[lastBarIdx]) {
    const up = TC.bollinger.upper[startIdx + lastBarIdx];
    const lo = TC.bollinger.lower[startIdx + lastBarIdx];
    if (up !== undefined && up !== null && lo !== undefined && lo !== null) {
      ctx.fillStyle = "#38bdf8";
      const txt = `BB: [${fmtNum(lo, 4)} - ${fmtNum(up, 4)}]`;
      ctx.fillText(txt, legX, 20);
      legX += ctx.measureText(txt).width + 16;
    }
  }
  if (TC.indicators && TC.indicators.rsi && TC.rsi && candles[lastBarIdx]) {
    const val = TC.rsi[startIdx + lastBarIdx];
    if (val !== undefined && val !== null) {
      ctx.fillStyle = "#c084fc";
      const txt = `RSI: ${val.toFixed(1)}`;
      ctx.fillText(txt, legX, 20);
      legX += ctx.measureText(txt).width + 16;
    }
  }

  // Draw Interactive Crosshair & Cursor Badges
  if (TC.hoverPoint && TC.hoverPoint.x >= 0 && TC.hoverPoint.x <= pw && TC.hoverPoint.y >= 0 && TC.hoverPoint.y <= h) {
    const hx = TC.hoverPoint.x;
    const hy = TC.hoverPoint.y;

    ctx.strokeStyle = "rgba(139, 148, 158, 0.55)";
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);

    // Vertical line
    ctx.beginPath();
    ctx.moveTo(hx, 0);
    ctx.lineTo(hx, h);
    ctx.stroke();

    // Horizontal line
    ctx.beginPath();
    ctx.moveTo(0, hy);
    ctx.lineTo(pw, hy);
    ctx.stroke();
    ctx.setLineDash([]);

    // Price Badge on Right Scale
    if (hy <= chartH) {
      const curP = priceAt(hy);
      const pStr = fmtNum(curP, 5);
      ctx.font = "bold 10px Cascadia Code, Consolas, monospace";
      ctx.fillStyle = "#1f6feb";
      ctx.fillRect(pw, hy - 9, priceScaleW, 18);
      ctx.fillStyle = "#ffffff";
      ctx.fillText(pStr, pw + 5, hy + 3.5);
    } else if (showRSI && hy >= chartH + volH && hy <= h) {
      const rsiBaseY = chartH + volH;
      const curRsi = 100 - ((hy - (rsiBaseY + 12)) / (rsiH - 20)) * 100;
      if (curRsi >= 0 && curRsi <= 100) {
        ctx.font = "bold 10px Cascadia Code, Consolas, monospace";
        ctx.fillStyle = "#8b5cf6";
        ctx.fillRect(pw, hy - 9, priceScaleW, 18);
        ctx.fillStyle = "#ffffff";
        ctx.fillText(`RSI ${curRsi.toFixed(1)}`, pw + 4, hy + 3.5);
      }
    }

    // Time Badge at Bottom X-Scale
    const curT = timeAt(hx);
    if (curT) {
      const tStr = curT.replace("T", " ").slice(5, 16);
      ctx.font = "10px Cascadia Code, Consolas, monospace";
      const tw = ctx.measureText(tStr).width;
      ctx.fillStyle = "#30363d";
      ctx.fillRect(hx - tw / 2 - 4, h - 18, tw + 8, 16);
      ctx.fillStyle = "#e6edf3";
      ctx.fillText(tStr, hx - tw / 2, h - 6);
    }
  }
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
  document.title = `${NAV.find((n) => n.id === route).label} · TradeAudit`;
  return renderRoute();
}

window.addEventListener("hashchange", syncFromHash);

async function init() {
  await refreshStatus();
  await syncFromHash();
  setInterval(refreshStatus, 15000);
}

init();
