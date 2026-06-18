/* ── OneAds Frontend ── */
const API = "http://localhost:8000";

const PLATFORMS = [
  {
    id: "google",
    name: "Google Drive + Ads",
    desc: "Conecte seu Drive (banco de dados) e Google Ads",
    icon: "🔵",
    iconClass: "icon-google",
    connectUrl: `${API}/auth/google/connect`,
    syncEndpoint: "/sync/google-ads",
    syncLabel: "Sincronizar Google Ads",
  },
  {
    id: "meta",
    name: "Meta Ads",
    desc: "Facebook Ads e Instagram Ads",
    icon: "📘",
    iconClass: "icon-meta",
    connectUrl: `${API}/auth/meta/connect`,
    syncEndpoint: "/sync/meta",
    syncLabel: "Sincronizar Meta Ads",
  },
  {
    id: "tiktok",
    name: "TikTok Ads",
    desc: "TikTok for Business",
    icon: "🎵",
    iconClass: "icon-tiktok",
    connectUrl: `${API}/auth/tiktok/connect`,
    syncEndpoint: "/sync/tiktok",
    syncLabel: "Sincronizar TikTok Ads",
  },
  {
    id: "hotmart",
    name: "Hotmart",
    desc: "Vendas de produtos digitais",
    icon: "🔥",
    iconClass: "icon-hotmart",
    connectUrl: `${API}/auth/hotmart/connect`,
    syncEndpoint: "/sync/hotmart",
    syncLabel: "Sincronizar Vendas",
  },
];

let status = {};

/* ────── Init ────── */
async function init() {
  checkConnectedParam();
  await fetchStatus();
  renderPlatforms();
  renderSyncPanel();
  await fetchDriveFiles();
}

function checkConnectedParam() {
  const params = new URLSearchParams(window.location.search);
  const connected = params.get("connected");
  if (connected) {
    toast(`✅ ${connected.charAt(0).toUpperCase() + connected.slice(1)} conectado com sucesso!`, "ok");
    window.history.replaceState({}, "", "/");
  }
}

/* ────── Status ────── */
async function fetchStatus() {
  try {
    const res = await fetch(`${API}/auth/status`);
    status = await res.json();
  } catch (e) {
    toast("Não foi possível conectar à API. Verifique se o backend está rodando.", "err");
  }
}

/* ────── Render Platforms ────── */
function renderPlatforms() {
  const grid = document.getElementById("platforms-grid");
  grid.innerHTML = "";

  PLATFORMS.forEach((p) => {
    const info = status[p.id] || { connected: false };
    const isConnected = info.connected;

    const card = document.createElement("div");
    card.className = `platform-card${isConnected ? " connected" : ""}`;
    card.innerHTML = `
      <div class="platform-icon ${p.iconClass}">${p.icon}</div>
      <div class="platform-name">${p.name}</div>
      <div class="platform-desc">${p.desc}</div>
      <div class="platform-account">${info.account_name ? "👤 " + info.account_name : ""}</div>
      <span class="status-badge ${isConnected ? "badge-connected" : "badge-disconnected"}">
        ${isConnected ? "✓ Conectado" : "Não conectado"}
      </span>
      <div style="margin-top:14px">
        ${isConnected
          ? `<button class="btn btn-danger" onclick="disconnect('${p.id}')">Desconectar</button>
             <button class="btn btn-sync" onclick="syncPlatform('${p.id}', '${p.syncEndpoint}', this)">
               🔄 ${p.syncLabel}
             </button>`
          : `<a href="${p.connectUrl}" class="btn btn-primary">🔗 Conectar</a>`
        }
      </div>
    `;
    grid.appendChild(card);
  });
}

/* ────── Disconnect ────── */
async function disconnect(platformId) {
  if (!confirm(`Desconectar ${platformId}?`)) return;
  showLoading("Desconectando...");
  try {
    await fetch(`${API}/auth/${platformId}/disconnect`, { method: "DELETE" });
    await fetchStatus();
    renderPlatforms();
    renderSyncPanel();
    toast(`${platformId} desconectado.`, "ok");
  } catch (e) {
    toast("Erro ao desconectar.", "err");
  } finally {
    hideLoading();
  }
}

/* ────── Sync Panel ────── */
function renderSyncPanel() {
  const panel = document.getElementById("sync-actions");
  panel.innerHTML = "";

  const connected = PLATFORMS.filter((p) => status[p.id]?.connected && p.id !== "google");

  if (!status.google?.connected) {
    panel.innerHTML = `<p style="color:var(--text2)">⚠️ Conecte o <strong>Google Drive</strong> primeiro — ele é o banco de dados.</p>`;
    return;
  }

  if (connected.length === 0) {
    panel.innerHTML = `<p style="color:var(--text2)">Conecte pelo menos uma plataforma de ads para sincronizar.</p>`;
    return;
  }

  connected.forEach((p) => {
    const btn = document.createElement("button");
    btn.className = "btn btn-primary";
    btn.textContent = `🔄 ${p.syncLabel}`;
    btn.onclick = () => syncPlatform(p.id, p.syncEndpoint, btn);
    panel.appendChild(btn);
  });

  const allBtn = document.createElement("button");
  allBtn.className = "btn btn-success";
  allBtn.textContent = "⚡ Sincronizar Tudo";
  allBtn.style.width = "100%";
  allBtn.style.marginTop = "12px";
  allBtn.onclick = () => syncAll();
  panel.appendChild(allBtn);
}

/* ────── Sync ────── */
async function syncPlatform(platformId, endpoint, btn) {
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span> Sincronizando...`;
  }
  addLog(`[${platformId}] Iniciando sincronização...`, "info");
  try {
    const res = await fetch(`${API}${endpoint}`, { method: "POST" });
    const data = await res.json();
    if (data.success) {
      addLog(`[${platformId}] ✅ ${data.rows_synced} linhas sincronizadas.`, "ok");
      if (data.drive_file_url) {
        addLog(`[${platformId}] 📄 Arquivo: ${data.drive_file_url}`, "info");
      }
      toast(`${platformId}: ${data.rows_synced} linhas no Drive!`, "ok");
      await fetchDriveFiles();
    } else {
      addLog(`[${platformId}] ❌ ${data.detail || "Erro"}`, "err");
      toast(`Erro ao sincronizar ${platformId}`, "err");
    }
  } catch (e) {
    addLog(`[${platformId}] ❌ ${e.message}`, "err");
    toast(`Falha na sincronização de ${platformId}`, "err");
  } finally {
    if (btn) {
      btn.disabled = false;
      const p = PLATFORMS.find((x) => x.id === platformId);
      btn.innerHTML = `🔄 ${p?.syncLabel || "Sincronizar"}`;
    }
  }
}

async function syncAll() {
  const connected = PLATFORMS.filter((p) => status[p.id]?.connected && p.id !== "google");
  for (const p of connected) {
    await syncPlatform(p.id, p.syncEndpoint, null);
  }
}

function addLog(msg, type = "info") {
  const log = document.getElementById("sync-log");
  log.classList.add("visible");
  const line = document.createElement("div");
  line.className = `log-line log-${type}`;
  line.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
  log.appendChild(line);
  log.scrollTop = log.scrollHeight;
}

/* ────── Drive Files ────── */
async function fetchDriveFiles() {
  if (!status.google?.connected) return;
  try {
    const res = await fetch(`${API}/sync/history`);
    const data = await res.json();
    renderDriveFiles(data.files || []);
  } catch (e) {
    // silently ignore
  }
}

function renderDriveFiles(files) {
  const container = document.getElementById("drive-files");
  if (!files.length) {
    container.innerHTML = `<p style="color:var(--text2)">Nenhuma planilha sincronizada ainda. Faça a primeira sincronização!</p>`;
    return;
  }
  container.innerHTML = "";
  files.forEach((f) => {
    const card = document.createElement("a");
    card.className = "file-card";
    card.href = f.webViewLink || "#";
    card.target = "_blank";
    card.innerHTML = `
      <div class="file-icon">📊</div>
      <div>
        <div class="file-name">${f.name}</div>
        <div class="file-date">${f.modifiedTime ? new Date(f.modifiedTime).toLocaleDateString("pt-BR") : ""}</div>
      </div>
    `;
    container.appendChild(card);
  });
}

/* ────── Toast ────── */
function toast(msg, type = "ok") {
  const container = document.getElementById("toast-container");
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.innerHTML = `<span>${type === "ok" ? "✅" : "❌"}</span><span>${msg}</span>`;
  container.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

/* ────── Loading ────── */
function showLoading(msg = "Aguarde...") {
  document.getElementById("loading-text").textContent = msg;
  document.getElementById("loading-overlay").classList.add("active");
}
function hideLoading() {
  document.getElementById("loading-overlay").classList.remove("active");
}

document.addEventListener("DOMContentLoaded", init);
