const API_BASE = "http://127.0.0.1:8000/api/v1";

// Logger function for Telecom activity stream
function logTelecomEvent(message, type = "info") {
  const container = document.getElementById("telecom-logs");
  if (!container) return;

  const time = new Date().toLocaleTimeString();
  let badgeColor = "text-slate-300";

  if (type === "success") badgeColor = "text-emerald-400";
  if (type === "warn") badgeColor = "text-amber-400";
  if (type === "danger") badgeColor = "text-rose-400";

  const item = document.createElement("div");
  item.className = `flex items-start space-x-2 text-xs py-1 border-b border-slate-900/60 ${badgeColor}`;
  item.innerHTML = `
    <span class="text-slate-500 font-telecom-mono">[${time}]</span>
    <span>${message}</span>
  `;
  container.prepend(item);
}

function clearConsoleLogs() {
  const container = document.getElementById("telecom-logs");
  if (container) container.innerHTML = "";
}

// 1. Fetch Contact Center Live Metrics
async function fetchTelemetryMetrics() {
  try {
    const res = await fetch(`${API_BASE}/telemetry/metrics`);
    if (!res.ok) return;
    const data = await res.json();

    document.getElementById("metric-total-calls").textContent = data.total_calls ?? 0;
    document.getElementById("metric-dropped-calls").textContent = data.total_dropped ?? 0;
    document.getElementById("metric-sticky-reconnects").textContent = data.total_reconnected ?? 0;
    document.getElementById("metric-drop-rate").textContent = `${data.drop_rate_percentage ?? 0}%`;
    document.getElementById("metric-avg-time").textContent = `${data.avg_reconnection_time_seconds ?? 0}s`;
  } catch (err) {
    console.error("Failed to load telemetry:", err);
  }
}

// 2. Fetch Active Agent Pool
async function fetchAgentPool() {
  try {
    const res = await fetch(`${API_BASE}/agents/`);
    if (!res.ok) return;
    const agents = await res.json();

    const grid = document.getElementById("agent-matrix-grid");
    if (!grid) return;
    grid.innerHTML = "";

    agents.forEach(agent => {
      let statusClass = "bg-emerald-950/80 text-emerald-400 border-emerald-800";
      let pulseEffect = "";

      if (agent.status === "ON_HOLD") {
        statusClass = "bg-amber-950/80 text-amber-400 border-amber-700 font-semibold";
        pulseEffect = "pulse-sticky border-amber-500/80";
      } else if (agent.status === "BUSY") {
        statusClass = "bg-rose-950/80 text-rose-400 border-rose-800";
      }

      const card = document.createElement("div");
      card.className = `bg-slate-900/90 border border-slate-800 p-3.5 rounded-xl flex flex-col justify-between transition-all ${pulseEffect}`;
      card.innerHTML = `
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <div class="w-2 h-2 rounded-full ${agent.status === 'AVAILABLE' ? 'bg-emerald-500' : (agent.status === 'ON_HOLD' ? 'bg-amber-500' : 'bg-rose-500')}"></div>
            <span class="text-sm font-bold text-slate-100 font-telecom-mono">${agent.agent_code}</span>
          </div>
          <span class="text-[10px] uppercase font-telecom-mono tracking-wider px-2 py-0.5 rounded border ${statusClass}">
            ${agent.status}
          </span>
        </div>
        <div class="mt-3">
          <p class="text-xs font-medium text-slate-300 truncate">${agent.full_name || 'Agent'}</p>
          <p class="text-[11px] text-slate-500 truncate mt-0.5">${agent.email || ''}</p>
        </div>
      `;
      grid.appendChild(card);
    });
  } catch (err) {
    console.error("Failed to load agents:", err);
  }
}

// Global Poll Timer (2-second interval for real-time contact center updates)
document.addEventListener("DOMContentLoaded", () => {
  fetchTelemetryMetrics();
  fetchAgentPool();

  setInterval(() => {
    fetchTelemetryMetrics();
    fetchAgentPool();
  }, 2000);
});
