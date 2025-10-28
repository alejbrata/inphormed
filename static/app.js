// ===================== Utilidades =====================
function toHref(p) { return p ? (p.startsWith("/") ? p : `/${p}`) : null; }

// ===================== Health =====================
async function checkHealth() {
  const badge = document.getElementById("health-badge");
  try {
    const res = await fetch("/health");
    const data = await res.json();
    if (data.status === "ok") {
      badge.textContent = "OK";
      badge.className = "text-sm px-2 py-1 rounded bg-green-100 text-green-700";
    } else {
      badge.textContent = "Degradado";
      badge.className = "text-sm px-2 py-1 rounded bg-yellow-100 text-yellow-700";
    }
  } catch {
    badge.textContent = "Caído";
    badge.className = "text-sm px-2 py-1 rounded bg-red-100 text-red-700";
  }
}

// ===================== Navegación =====================
function showView(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.scrollIntoView({ behavior: "smooth", block: "start" });
  el.classList.add("ring", "ring-2", "ring-sky-300");
  setTimeout(() => el.classList.remove("ring", "ring-2", "ring-sky-300"), 600);
}

// ===================== Chat (HS) =====================
const CHAT_TOPIC = "hidradenitis supurativa";
let chatMessages = [
  { role: "assistant", content: "Hola, soy tu asistente clínico en hidradenitis supurativa. ¿En qué te ayudo hoy?" }
];

function renderChat() {
  const box = document.getElementById("chat-messages");
  if (!box) return;
  box.innerHTML = "";
  chatMessages.forEach(m => {
    const wrap = document.createElement("div");
    wrap.className = (m.role === "assistant")
      ? "bg-white border rounded-xl p-3 max-w-[85%]"
      : "bg-black text-white rounded-xl p-3 ml-auto max-w-[85%]";
    wrap.textContent = m.content;
    box.appendChild(wrap);
  });
  box.scrollTop = box.scrollHeight;
}

async function sendChat(e) {
  e.preventDefault();
  const input = document.getElementById("chat-input");
  const text = (input.value || "").trim();
  if (!text) return;

  chatMessages.push({ role: "user", content: text });
  input.value = "";
  renderChat();

  chatMessages.push({ role: "assistant", content: "…" });
  renderChat();

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({
        topic: CHAT_TOPIC,
        messages: chatMessages.filter(m => m.content !== "…")
      })
    });
    const data = await res.json();
    if (chatMessages.at(-1)?.content === "…") chatMessages.pop();
    chatMessages.push({ role: "assistant", content: data.reply || "(sin respuesta)" });
    renderChat();
  } catch {
    if (chatMessages.at(-1)?.content === "…") chatMessages.pop();
    chatMessages.push({ role: "assistant", content: "Error al obtener respuesta." });
    renderChat();
  }
}

// ===================== Verificación (texto o archivo) =====================
function setMode(mode) {
  const textWrap = document.getElementById("text-area-wrapper");
  const fileWrap = document.getElementById("file-area-wrapper");
  if (mode === "text") {
    textWrap.classList.remove("hidden");
    fileWrap.classList.add("hidden");
  } else {
    fileWrap.classList.remove("hidden");
    textWrap.classList.add("hidden");
  }
}

async function handleUnifiedSubmit(e) {
  e.preventDefault();
  const out = document.getElementById("verify-result");
  const mode = [...document.querySelectorAll('.mode-radio')].find(r => r.checked)?.value || "text";
  out.textContent = "";

  if (mode === "text") {
    const claim = (document.getElementById("claim-input").value || "").trim();
    if (!claim) {
      out.textContent = "Introduce un texto para verificar.";
      return;
    }
    out.textContent = "Verificando texto...";
    try {
      const res = await fetch("/api/validate", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ claim })
      });
      if (!res.ok) {
        const t = await res.text();
        out.textContent = `Error del servidor (${res.status}): ${t}`;
        return;
      }
      const data = await res.json();
      out.innerHTML = `
        <div class="mb-2">✔️ Resultado del texto</div>
        <div><b>Score:</b> ${data.score ?? "—"} | <b>Valid:</b> ${data.valid ?? "—"}</div>
        <div class="text-xs text-gray-600 mt-2">* En producción, aquí mostraremos evidencias y color (verde/amarillo/rojo).</div>
      `;
    } catch {
      out.textContent = "Error verificando el texto.";
    }

  } else { // modo archivo
    const fileInput = document.getElementById("verify-file");
    const file = fileInput?.files?.[0];
    if (!file) {
      out.textContent = "Selecciona un archivo .pptx o .docx";
      return;
    }
    out.textContent = "Procesando documento (puede tardar un poco)...";
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await fetch("/api/verify-ppt", { method: "POST", body: form });
      if (!res.ok) {
        const t = await res.text();
        out.textContent = `Error del servidor (${res.status}): ${t}`;
        return;
      }
      const data = await res.json();

      const linkReport = toHref(data.report_path);
      const linkAnno   = toHref(data.summary?.annotated_doc);
      const linkSnip   = toHref(data.summary?.snippets_html);

      const greens  = data.summary?.green  ?? 0;
      const yellows = data.summary?.yellow ?? 0;
      const reds    = data.summary?.red    ?? 0;

      let html = `
        <div class="mb-2">Informe generado ✅</div>
        <div class="mb-2">Resultados:
          <span class="px-2 py-0.5 rounded bg-green-100 text-green-800">Verde=${greens}</span>
          <span class="px-2 py-0.5 rounded bg-yellow-100 text-yellow-800 ml-1">Amarillo=${yellows}</span>
          <span class="px-2 py-0.5 rounded bg-red-100 text-red-800 ml-1">Rojo=${reds}</span>
        </div>
        <ul class="list-disc ml-5 space-y-1">
      `;
      if (linkReport) html += `<li><a class="underline" href="${linkReport}" target="_blank" rel="noopener">Abrir reporte PDF</a></li>`;
      if (linkAnno)   html += `<li><a class="underline" href="${linkAnno}" target="_blank" rel="noopener">Descargar documento anotado</a></li>`;
      if (linkSnip)   html += `<li><a class="underline" href="${linkSnip}" target="_blank" rel="noopener">Ver snippets con texto exacto</a></li>`;
      html += `</ul>`;

      out.innerHTML = html;
    } catch {
      out.textContent = "Error en el procesamiento del documento.";
    }
  }
}

// ===================== Personalización (layout + DnD + agente) =====================
const LAYOUT_KEY = "inphormed_layout_v1";
let layout = {
  version: 1,
  widgets: [
    { id: "chat", order: 0, span: 2, visible: true },
    { id: "validate", order: 1, span: 2, visible: true },
    { id: "create", order: 2, span: 2, visible: true },
  ],
};

async function loadLayout() {
  try {
    const res = await fetch("/api/ui-layout");
    if (res.ok) layout = await res.json();
  } catch {}
  const ls = localStorage.getItem(LAYOUT_KEY);
  if (ls) { try { layout = JSON.parse(ls); } catch {} }
  applyLayout();
}

function saveLayout() {
  localStorage.setItem(LAYOUT_KEY, JSON.stringify(layout));
  fetch("/api/ui-layout", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ layout }),
  }).catch(()=>{});
}

function applyLayout() {
  const container = document.querySelector("main");
  const byId = Object.fromEntries(layout.widgets.map(w => [w.id, w]));
  // visibilidad
  document.querySelectorAll(".widget").forEach(sec => {
    const wid = sec.dataset.widgetId;
    const w = byId[wid];
    if (!w) return;
    sec.classList.toggle("hidden", w.visible === false);
  });
  // orden
  const orderedIds = [...layout.widgets].sort((a,b)=>a.order-b.order).map(w=>w.id);
  orderedIds.forEach(wid => {
    const el = document.querySelector(`.widget[data-widget-id="${wid}"]`);
    if (el) container.appendChild(el);
  });
}

let customizing = false;
function setCustomizeMode(on) {
  customizing = !!on;
  // Sin panel: solo asas y borde
  document.querySelectorAll(".drag-handle").forEach(h => h.classList.toggle("hidden", !on));
  document.querySelectorAll(".widget").forEach(w => {
    w.setAttribute("draggable", on ? "true" : "false");
    w.classList.toggle("ring", on);
    w.classList.toggle("ring-1", on);
    w.classList.toggle("ring-gray-300", on);
  });
}

function enableDnD() {
  let dragEl = null;
  document.querySelectorAll(".widget").forEach(el => {
    el.addEventListener("dragstart", (e) => {
      if (!customizing) { e.preventDefault(); return; }
      dragEl = el;
      e.dataTransfer.effectAllowed = "move";
      el.classList.add("opacity-60");
    });
    el.addEventListener("dragend", () => {
      if (dragEl) dragEl.classList.remove("opacity-60");
      dragEl = null;
    });
    el.addEventListener("dragover", (e) => {
      if (!customizing) return;
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
    });
    el.addEventListener("drop", (e) => {
      if (!customizing || !dragEl || dragEl === el) return;
      e.preventDefault();
      const container = el.parentElement;
      const rect = el.getBoundingClientRect();
      const before = (e.clientY - rect.top) < rect.height / 2;
      if (before) container.insertBefore(dragEl, el);
      else container.insertBefore(dragEl, el.nextSibling);
      const orderIds = [...container.querySelectorAll(".widget")].map(x => x.dataset.widgetId);
      layout.widgets.forEach(w => w.order = orderIds.indexOf(w.id));
      saveLayout();
    });
  });
}

// ===================== Agente de UI (voz + texto) — silencioso =====================
function bindUIAgent() {
  const form = document.getElementById("ui-agent-form");
  const input = document.getElementById("ui-agent-input");
  const micBtn = document.getElementById("ui-mic-btn");
  if (!form) return;

  // Enviar comando (sin mostrar mensajes)
  async function sendUICommand(command) {
    if (!command) return;
    try {
      const res = await fetch("/api/ui-agent/command", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ command, layout })
      });
      const data = await res.json();
      if (data.layout) {
        layout = data.layout;
        applyLayout();
        saveLayout();
      }
    } catch (e) {
      // silencio total; para depurar: console.error(e);
    }
  }

  // Texto → Aplicar
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const cmd = (input.value || "").trim();
    sendUICommand(cmd);
    input.value = "";
  });

  // -------- Dictado por voz (Web Speech API) --------
  let recognizing = false;
  let recognition = null;
  let supported = false;

  function setupSpeechRecognition() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) return null;
    const r = new SR();
    r.lang = "es-ES";
    r.continuous = false;       // 1 frase por pulsación
    r.interimResults = true;    // mostramos resultados parciales
    r.maxAlternatives = 1;

    let finalTranscript = "";

    r.addEventListener("start", () => {
      finalTranscript = "";
      recognizing = true;
      if (micBtn) micBtn.classList.add("bg-red-600","text-white");
    });

    r.addEventListener("result", (ev) => {
      let interim = "";
      for (let i = ev.resultIndex; i < ev.results.length; ++i) {
        const t = ev.results[i][0].transcript;
        if (ev.results[i].isFinal) finalTranscript += t;
        else interim += t;
      }
      // opcional: enseñar en el input lo que va entendiendo
      input.value = (finalTranscript || interim || "").trim();
    });

    r.addEventListener("end", () => {
      recognizing = false;
      if (micBtn) micBtn.classList.remove("bg-red-600","text-white");
      const text = (finalTranscript || input.value || "").trim();
      if (text) {
        sendUICommand(text);
        // opcional: mantener el texto último en el input para que el usuario lo vea
      }
    });

    r.addEventListener("error", (e) => {
      recognizing = false;
      if (micBtn) micBtn.classList.remove("bg-red-600","text-white");
      // errores típicos: "no-speech", "audio-capture", "not-allowed"
      // No mostramos nada al usuario (silencioso). Para depurar: console.warn(e.error);
    });

    return r;
  }

  function toggleMic() {
    if (!recognition) recognition = setupSpeechRecognition();
    if (!recognition) return; // no soportado
    try {
      if (!recognizing) recognition.start();
      else recognition.stop();
    } catch {
      // algunos navegadores lanzan si se llama start() dos veces
    }
  }

  // Inicializa/inhabilita el botón según soporte
  (function initMicButton() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    supported = !!SR;
    if (micBtn) {
      if (!supported) {
        micBtn.title = "Dictado no soportado por este navegador";
        micBtn.classList.add("opacity-50", "cursor-not-allowed");
        micBtn.disabled = true;
      } else {
        micBtn.addEventListener("click", toggleMic);
        micBtn.title = "Hablar comando";
      }
    }
  })();
}

// ===================== INIT =====================
document.addEventListener("DOMContentLoaded", () => {
  checkHealth();

  // Sidebar → scroll a cada sección
  document.querySelectorAll(".nav-btn").forEach(btn => {
    btn.addEventListener("click", () => showView(`view-${btn.dataset.view}`));
  });

  // Chat
  renderChat();
  const chatForm = document.getElementById("chat-form");
  if (chatForm) chatForm.addEventListener("submit", sendChat);

  // Verificación
  const radios = document.querySelectorAll(".mode-radio");
  radios.forEach(r => r.addEventListener("change", (e) => setMode(e.target.value)));
  setMode("text");
  const verifyForm = document.getElementById("verify-form");
  if (verifyForm) verifyForm.addEventListener("submit", handleUnifiedSubmit);

  // Personalización
  const toggle = document.getElementById("customize-toggle");
  if (toggle) toggle.addEventListener("click", () => setCustomizeMode(!customizing));
  loadLayout().then(() => {
    enableDnD();
    bindUIAgent();   // incluye voz mejorada y ejecución silenciosa
  });
});
