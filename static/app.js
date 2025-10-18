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
  } catch (e) {
    badge.textContent = "Caído";
    badge.className = "text-sm px-2 py-1 rounded bg-red-100 text-red-700";
  }
}

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
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ claim })
      });
      const data = await res.json();
      // data: { claim, valid, score } (stub) o tu estructura extendida si la cambiaste
      out.innerHTML = `
        <div class="mb-2">✔️ Resultado del texto</div>
        <div><b>Score:</b> ${data.score ?? "—"} | <b>Valid:</b> ${data.valid ?? "—"}</div>
        <div class="text-xs text-gray-600 mt-2">* En modo producción, este bloque mostrará evidencias y nivel (verde/amarillo/rojo).</div>
      `;
    } catch (err) {
      out.textContent = "Error verificando el texto.";
    }
  } else {
    const fileInput = document.getElementById("verify-file");
    const file = fileInput.files[0];
    if (!file) {
      out.textContent = "Selecciona un archivo .pptx o .docx";
      return;
    }
    out.textContent = "Procesando documento (puede tardar un poco)...";
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await fetch("/api/verify-ppt", { method: "POST", body: form });
      const data = await res.json();
      if (data.report_path) {
        // Si montaste outputs como estático en /outputs
        const link = data.report_path.startsWith("outputs/")
          ? `/${data.report_path}`
          : data.report_path;

        out.innerHTML = `
          <div class="mb-2">Informe generado ✅</div>
          <div>Resultados: Verde=${data.summary?.green ?? 0} | Amarillo=${data.summary?.yellow ?? 0} | Rojo=${data.summary?.red ?? 0}</div>
          <a class="underline" href="${link}" target="_blank">Abrir reporte PDF</a>
        `;
      } else {
        out.textContent = "No se pudo generar el informe.";
      }
    } catch (err) {
      out.textContent = "Error en el procesamiento del documento.";
    }
  }
}




async function validateClaim() {
  const input = document.getElementById("claim-input");
  const out = document.getElementById("validate-result");
  const claim = (input.value || "").trim();
  if (!claim) {
    out.textContent = "Introduce un claim para validar.";
    return;
  }
  out.textContent = "Validando...";
  try {
    const res = await fetch("/api/validate", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({claim})
    });
    const data = await res.json();
    out.textContent = `✔️ Resultado: valid=${data.valid} | score=${data.score} | claim="${data.claim}"`;
  } catch (e) {
    out.textContent = "Error validando el claim.";
  }
}

async function ingestDoc() {
  const input = document.getElementById("ingest-path");
  const out = document.getElementById("ingest-result");
  const path = (input.value || "").trim();
  if (!path) {
    out.textContent = "Introduce una ruta o referencia (placeholder).";
    return;
  }
  out.textContent = "Ingestando...";
  try {
    const res = await fetch("/api/ingest", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({path})
    });
    const data = await res.json();
    out.textContent = `📄 Ingestado: ${JSON.stringify(data)}`;
  } catch (e) {
    out.textContent = "Error en ingesta.";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  // Salud
  checkHealth?.();

  // Modo (radio buttons)
  const radios = document.querySelectorAll(".mode-radio");
  radios.forEach(r => r.addEventListener("change", (e) => setMode(e.target.value)));
  setMode("text"); // por defecto

  // Form submit único
  const verifyForm = document.getElementById("verify-form");
  if (verifyForm) verifyForm.addEventListener("submit", handleUnifiedSubmit);
});

async function uploadPPT(e){
  e.preventDefault();
  const file = document.getElementById("ppt-file").files[0];
  const out = document.getElementById("ppt-result");
  if(!file){ out.textContent="Selecciona un .pptx"; return; }
  out.textContent = "Procesando PPT... (puede tardar un poco)";
  const form = new FormData();
  form.append("file", file);
  try{
    const res = await fetch("/api/verify-ppt", { method:"POST", body: form });
    const data = await res.json();
    if(data.report_path){
      out.innerHTML = `
        <div>Informe generado ✅</div>
        <div>Resultados: Verde=${data.summary.green} | Amarillo=${data.summary.yellow} | Rojo=${data.summary.red}</div>
        <a class="underline" href="/${data.report_path}" target="_blank">Abrir reporte PDF</a>
      `;
    }else{
      out.textContent = "No se pudo generar el informe.";
    }
  }catch(err){
    out.textContent = "Error en el procesamiento.";
  }
}
document.addEventListener("DOMContentLoaded", ()=>{
  // ... tus otros listeners
  const pptForm = document.getElementById("ppt-form");
  if(pptForm){ pptForm.addEventListener("submit", uploadPPT); }
});
