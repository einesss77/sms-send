const PASSWORD = "temples2025";

const el = (id) => document.getElementById(id);

const overlay = el("overlay");
const pwd = el("pwd");
const btnLogin = el("btnLogin");
const err = el("err");

const apiUrlInput = el("apiUrl");
const statusSelect = el("status");
const qInput = el("q");
const limitSelect = el("limit");
const btnRefresh = el("btnRefresh");
const tbody = el("tbody");
const subline = el("subline");

const LS_KEY = "sms_dashboard_authed";

function setSub(text) { subline.textContent = text; }

function isAuthed() {
    return localStorage.getItem(LS_KEY) === "1";
}

function setAuthed(ok) {
    localStorage.setItem(LS_KEY, ok ? "1" : "0");
}

function escapeHtml(s) {
    return String(s)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function fmtDate(d) {
    if (!d) return "-";
    try {
        const dt = new Date(d);
        if (Number.isNaN(dt.getTime())) return "-";
        return dt.toLocaleString();
    } catch {
        return "-";
    }
}

// --- NEW: config ---
let API_BASE = "";

async function loadConfig() {
    // API_BASE_URL vient du .env via FastAPI (/config)
    const res = await fetch("/config");
    if (!res.ok) throw new Error(`Config error ${res.status}`);

    const cfg = await res.json();
    if (!cfg.api_base_url) throw new Error("API_BASE_URL manquant dans l'environnement (Render).");

    API_BASE = String(cfg.api_base_url).trim().replace(/\/+$/, "");
    apiUrlInput.value = API_BASE; // affichage info (read-only conseillé côté HTML)
}

async function apiFetch(path, options = {}) {
    if (!API_BASE) await loadConfig();
    const url = `${API_BASE}${path}`;

    const res = await fetch(url, options);
    if (!res.ok) {
        const txt = await res.text().catch(() => "");
        throw new Error(`${res.status} ${res.statusText}${txt ? " - " + txt : ""}`);
    }
    return res.json();
}

async function loadSMS() {
    setSub("Chargement…");

    const status = statusSelect.value;
    const limit = limitSelect.value;
    const q = qInput.value.trim().toLowerCase();

    const params = new URLSearchParams();
    if (status) params.set("status", status);
    params.set("limit", limit);

    let data = await apiFetch(`/sms?${params.toString()}`);

    // Filtre client-side (numéro/message)
    if (q) {
        data = data.filter((x) => {
            const to = (x.to || "").toLowerCase();
            const msg = (x.message || "").toLowerCase();
            return to.includes(q) || msg.includes(q);
        });
    }

    if (!Array.isArray(data) || data.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="mono">Aucun SMS.</td></tr>`;
        setSub("0 SMS");
        return;
    }

    tbody.innerHTML = data.map((sms) => {
        const status = sms.status || "PENDING";
        const canRetry = status === "FAILED";
        const created = fmtDate(sms.created_at);
        const sent = fmtDate(sms.sent_at);
        const lastAttempt = fmtDate(sms.last_attempt_at);
        const reason = sms.fail_reason ? escapeHtml(sms.fail_reason) : "-";

        const dates = `
      <div><span class="mono">Créé:</span> ${created}</div>
      <div><span class="mono">Dernière tentative:</span> ${lastAttempt}</div>
      <div><span class="mono">Envoyé:</span> ${sent}</div>
      <div><span class="mono">Fail:</span> ${reason}</div>
    `;

        return `
      <tr class="${escapeHtml(status)}">
        <td data-label="Statut">
          <span class="status"><span class="dot"></span>${escapeHtml(status)}</span>
        </td>

        <td data-label="Numéro">
          <div>${escapeHtml(sms.to)}</div>
          <div class="mono">${escapeHtml(sms.id)}</div>
        </td>

        <td data-label="Message">${escapeHtml(sms.message)}</td>

        <td data-label="Tentatives">${sms.attempt_count ?? 0}</td>

        <td data-label="Dates">${dates}</td>

        <td data-label="Actions">
          <div class="actions">
            ${
            canRetry
                ? `<button class="btnSmall btnDanger" onclick="retrySMS('${sms.id}')">Renvoyer</button>`
                : `<span class="mono">—</span>`
        }
          </div>
        </td>
      </tr>
    `;
    }).join("");

    setSub(`${data.length} SMS affichés`);
}

async function retrySMS(id) {
    try {
        await apiFetch(`/sms/${encodeURIComponent(id)}/retry`, { method: "POST" });
        await loadSMS();
        alert("SMS remis en attente (PENDING).");
    } catch (e) {
        alert("Erreur retry: " + e.message);
    }
}

// Login
function tryLogin() {
    const ok = pwd.value === PASSWORD;
    err.style.display = ok ? "none" : "block";
    if (!ok) return;

    setAuthed(true);
    overlay.style.display = "none";
    boot();
}

pwd.addEventListener("keydown", (e) => {
    if (e.key === "Enter") tryLogin();
});
btnLogin.addEventListener("click", tryLogin);

// Inputs
btnRefresh.addEventListener("click", loadSMS);
statusSelect.addEventListener("change", loadSMS);
limitSelect.addEventListener("change", loadSMS);
qInput.addEventListener("input", () => {
    window.clearTimeout(window.__qT);
    window.__qT = window.setTimeout(loadSMS, 250);
});

async function boot() {
    try {
        // charge l'URL depuis /config (API_BASE_URL dans .env)
        await loadConfig();

        // Optionnel: rendre le champ non modifiable côté JS (ou mets readonly dans le HTML)
        apiUrlInput.setAttribute("readonly", "readonly");

        await loadSMS();
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="6" class="mono">Erreur: ${escapeHtml(e.message)}</td></tr>`;
        setSub("Erreur");
    }
}

// Auto
if (isAuthed()) {
    overlay.style.display = "none";
    boot();
} else {
    setSub("Accès protégé");
}
