// 1. Dial Inbound Call
async function simulateInboundCall() {
  const phone = document.getElementById("sim-phone-input").value.trim();
  if (!phone) {
    alert("Please provide a valid phone number!");
    return;
  }

  const generatedSessionId = "CALL-" + Math.random().toString(36).substring(2, 9).toUpperCase();
  document.getElementById("sim-session-display").value = generatedSessionId;

  try {
    const res = await fetch(`${API_BASE}/calls/inbound`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        call_session_id: generatedSessionId,
        customer_phone_number: phone
      })
    });

    const data = await res.json();

    document.getElementById("active-agent-badge").textContent = data.assigned_agent_code || "UNASSIGNED";
    
    const stickyIndicator = document.getElementById("sticky-flag-indicator");
    if (data.is_reconnected) {
      stickyIndicator.textContent = "MATCHED (Sticky Session Reconnected)";
      stickyIndicator.className = "text-xs font-bold text-amber-400";
      logTelecomEvent(`Sticky Reconnect: Session ${generatedSessionId} bound to ${data.assigned_agent_code}`, "warn");
    } else {
      stickyIndicator.textContent = "STANDARD (Fresh Routing)";
      stickyIndicator.className = "text-xs font-medium text-emerald-400";
      logTelecomEvent(`Inbound Call: Session ${generatedSessionId} routed to ${data.assigned_agent_code}`, "success");
    }

    fetchAgentPool();
    fetchTelemetryMetrics();
  } catch (err) {
    logTelecomEvent(`Dialing failed: ${err.message}`, "danger");
  }
}

// 2. Trigger Telecom Network Failure Drop
async function simulateNetworkFailureDrop() {
  const sessionId = document.getElementById("sim-session-display").value.trim();
  if (!sessionId) {
    alert("Please initiate an inbound call first!");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/calls/disconnect`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        call_session_id: sessionId,
        disconnect_reason: "NETWORK_FAILURE"
      })
    });

    const data = await res.json();
    logTelecomEvent(`Telecom Drop: Call ${sessionId} dropped due to NETWORK_FAILURE. Agent locked to ON_HOLD for 180s.`, "danger");
    
    fetchAgentPool();
    fetchTelemetryMetrics();
  } catch (err) {
    logTelecomEvent(`Drop simulation error: ${err.message}`, "danger");
  }
}

// 3. Normal Hangup / Complete Call
async function simulateNormalHangup() {
  const sessionId = document.getElementById("sim-session-display").value.trim();
  if (!sessionId) {
    alert("No active session to terminate!");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/calls/disconnect`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        call_session_id: sessionId,
        disconnect_reason: "NORMAL_CLEARING"
      })
    });

    const data = await res.json();
    logTelecomEvent(`Call Terminated: Session ${sessionId} cleanly hung up. Agent restored to AVAILABLE.`, "success");

    document.getElementById("sticky-flag-indicator").textContent = "IDLE";
    document.getElementById("sticky-flag-indicator").className = "text-xs font-medium text-slate-400";
    document.getElementById("active-agent-badge").textContent = "-";

    fetchAgentPool();
    fetchTelemetryMetrics();
  } catch (err) {
    logTelecomEvent(`Hangup error: ${err.message}`, "danger");
  }
}
