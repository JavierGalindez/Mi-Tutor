/* =========================================================
   Mi Tutor — estudiante.js
   Flujo guiado: área → asignatura → necesidad → (tema) → tutor
   → perfil con cotizador → solicitud en Telegram.
   La solicitud se registra en SQLite desde el bot (Guía 03):
   esta página ya no guarda solicitudes falsas en localStorage.
   ========================================================= */

const ORDEN_PROGRESO = ["area", "asignatura", "necesidad", "tutores", "perfil"];
const ETAPA_PROGRESO = { area: "area", asignatura: "asignatura", necesidad: "necesidad",
  tema: "necesidad", tutores: "tutores", perfil: "perfil" };

const estado = { areaKey: null, asignatura: null, necesidad: null, tema: null, tutor: null, horas: 1 };
let historial = ["area"];

function render(etapa) {
  document.querySelectorAll(".etapa").forEach((s) => s.classList.remove("activa"));
  document.getElementById("et-" + etapa).classList.add("activa");
  ({ asignatura: pintarAsignaturas, necesidad: pintarNecesidades, tema: pintarTemas,
     tutores: pintarTutores, perfil: pintarPerfil })[etapa]?.();
  pintarProgreso(etapa);
  document.getElementById("btn-atras").style.visibility = historial.length > 1 ? "visible" : "hidden";
  const titulo = document.querySelector("#et-" + etapa + " h1");
  if (titulo) { titulo.setAttribute("tabindex", "-1"); titulo.focus({ preventScroll: true }); }
  window.scrollTo({ top: 0, behavior: "smooth" });
}
function irA(etapa) { historial.push(etapa); render(etapa); }
function atras() { if (historial.length > 1) { historial.pop(); render(historial[historial.length - 1]); } }

function pintarProgreso(etapa) {
  const actual = ORDEN_PROGRESO.indexOf(ETAPA_PROGRESO[etapa]);
  document.getElementById("progreso").style.visibility = actual < 0 ? "hidden" : "visible";
  document.querySelectorAll("#progreso li").forEach((li, i) => {
    li.className = i < actual ? "hecha" : i === actual ? "actual" : "";
    li.toggleAttribute("aria-current", i === actual);
  });
}

function boton(clase, html, alPulsar) {
  const b = document.createElement("button");
  b.type = "button"; b.className = clase; b.innerHTML = html;
  b.addEventListener("click", alPulsar);
  return b;
}

/* 1. Área */
function pintarAreas() {
  const cont = document.getElementById("lista-areas");
  Object.entries(MT_AREAS).forEach(([key, area]) => {
    const n = MT_TUTORES.filter((t) => t.area === key).length;
    cont.appendChild(boton("opcion " + key,
      `<span class="area-simbolo" aria-hidden="true">${area.simbolo}</span><strong>${area.label}</strong>
       <span>${area.asignaturas.length} asignaturas, ${n} tutores</span>`,
      () => { estado.areaKey = key; irA("asignatura"); }));
  });
}

/* 2. Asignatura */
function pintarAsignaturas() {
  const area = MT_AREAS[estado.areaKey];
  document.getElementById("t-asignatura").textContent = `${area.label}: elige la asignatura`;
  const cont = document.getElementById("lista-asignaturas");
  cont.innerHTML = "";
  area.asignaturas.forEach((nombre) => cont.appendChild(boton("chip", mtEscapar(nombre), () => {
    estado.asignatura = nombre; irA("necesidad");
  })));
}

/* 3. Necesidad */
function pintarNecesidades() {
  document.getElementById("necesidad-contexto").textContent = `Para ${estado.asignatura}, cuéntanos qué buscas.`;
  const cont = document.getElementById("lista-necesidades");
  cont.innerHTML = "";
  MT_NECESIDADES.forEach((n) => cont.appendChild(boton("opcion",
    `<strong>${n.label}</strong><span>${n.desc}</span>`,
    () => { estado.necesidad = n; estado.tema = null; irA(n.id === "refuerzo" ? "tema" : "tutores"); })));
}

/* 4. Tema (solo refuerzo) */
function pintarTemas() {
  document.getElementById("tema-contexto").textContent = `${estado.asignatura}: elige el tema o escríbelo.`;
  const cont = document.getElementById("lista-temas");
  cont.innerHTML = "";
  mtTemasDe(mtSlug(estado.asignatura)).forEach((tema) => cont.appendChild(boton("chip", mtEscapar(tema), () => {
    estado.tema = tema; irA("tutores");
  })));
  document.getElementById("tema-otro").value = "";
}
document.getElementById("form-tema").addEventListener("submit", (e) => {
  e.preventDefault();
  estado.tema = document.getElementById("tema-otro").value.trim();
  if (estado.tema) irA("tutores");
});

/* 5. Tutores */
function pintarTutores() {
  const tutores = mtTutoresPorAsignatura(estado.areaKey, estado.asignatura);
  const exactos = tutores.some((t) => t.asignaturas.includes(estado.asignatura));
  document.getElementById("tutores-contexto").textContent = exactos
    ? `${tutores.length === 1 ? "Este tutor domina" : "Estos tutores dominan"} ${estado.asignatura}.`
    : `Aún no hay un tutor dedicado a ${estado.asignatura}; estos tutores de ${MT_AREAS[estado.areaKey].label} pueden ayudarte.`;
  const cont = document.getElementById("lista-tutores");
  cont.innerHTML = "";
  tutores.forEach((t) => {
    const fila = document.createElement("article");
    fila.className = "tarjeta-tutor";
    fila.innerHTML = `
      <div class="iniciales" style="background:${MT_AREAS[t.area].color}" aria-hidden="true">${mtIniciales(t.nombre)}</div>
      <div><h3>${mtEscapar(t.nombre)}</h3>
        <p>${t.calificacion} de 5 en ${t.tutorias} tutorías. ${MT_MODALIDAD[t.modalidad]}. <strong>${mtFormatoCOP(mtPrecioConComision(t.precio))}</strong> la hora.</p></div>`;
    fila.appendChild(boton("boton boton-suave boton-sm", "Ver perfil y cotizar", () => { estado.tutor = t; estado.horas = 1; irA("perfil"); }));
    cont.appendChild(fila);
  });
}

/* 6. Perfil y cotizador */
/* Duración de un horario: «Lun 3–6pm» = 3 h (igual que en orquestador.py). */
function duracionFranja(etiqueta) {
  const m = etiqueta.trim().match(/^(\S+)\s+(\d{1,2})(am|pm|m)?\s*[–-]\s*(\d{1,2})(am|pm|m)$/i);
  if (!m) return null;
  const a24 = (h, suf) => { h = Number(h); if (suf === "m") return 12; if (suf === "pm" && h < 12) return h + 12; if (suf === "am" && h === 12) return 0; return h; };
  const s2 = m[5].toLowerCase();
  const fin = a24(m[4], s2);
  let inicio = a24(m[2], (m[3] || (s2 === "m" ? "am" : s2)).toLowerCase());
  if (!m[3] && inicio >= fin) inicio = a24(m[2], "am");
  return fin > inicio ? fin - inicio : null;
}
function maxHorasTutor(t) {
  return Math.max(...t.disponibilidad.map((e) => duracionFranja(e) || 1));
}

function pintarPerfil() {
  const t = estado.tutor;
  const ini = document.getElementById("perfil-iniciales");
  ini.textContent = mtIniciales(t.nombre);
  ini.style.background = MT_AREAS[t.area].color;
  document.getElementById("perfil-nombre").textContent = t.nombre;
  document.getElementById("perfil-sub").textContent = `${t.universidad}. ${t.calificacion} de 5 en ${t.tutorias} tutorías.`;
  document.getElementById("perfil-descripcion").textContent = t.descripcion;
  document.getElementById("perfil-materias").textContent = t.asignaturas.join(", ");
  document.getElementById("perfil-experiencia").textContent = t.experiencia;
  document.getElementById("perfil-modalidad").textContent = MT_MODALIDAD[t.modalidad];
  document.getElementById("perfil-horarios").textContent =
    t.disponibilidad.map((e) => `${e} (${duracionFranja(e) || "?"} h)`).join(", ");
  /* Solo se ofrecen las horas que caben en el horario más largo del tutor. */
  const limite = maxHorasTutor(t);
  if (estado.horas > limite) estado.horas = 1;
  document.querySelectorAll("#selector-horas button").forEach((b) => {
    b.hidden = Number(b.dataset.horas) > limite;
  });
  document.getElementById("perfil-tutorias").textContent = t.tutorias;
  document.getElementById("perfil-codigo").textContent = t.codigo;
  /* Deep link con el código del tutor: /start TUT-01 */
  document.getElementById("btn-telegram-tutor").href = mtEnlaceTelegram(t.codigo);
  actualizarCotizacion();
}

function actualizarCotizacion() {
  const t = estado.tutor;
  const c = mtCotizar(t.precio, estado.horas);
  document.getElementById("cot-subtotal").textContent = mtFormatoCOP(c.subtotal);
  document.getElementById("cot-comision").textContent = mtFormatoCOP(c.comision);
  document.getElementById("cot-total").textContent = mtFormatoCOP(c.total);
  document.querySelectorAll("#selector-horas button").forEach((b) =>
    b.setAttribute("aria-pressed", String(Number(b.dataset.horas) === estado.horas)));
  const tema = estado.tema ? ` Cuéntale a Tuti que quieres trabajar ${estado.tema}.` : "";
  document.getElementById("cot-nota").textContent =
    `En Telegram pulsa Solicitar tutoría, elige el horario y escribe ${estado.horas}. Cada horario dura ${maxHorasTutor(t)} h como máximo.${tema} Cotizar aquí no registra nada.`;
}
document.getElementById("selector-horas").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-horas]");
  if (!b) return;
  estado.horas = Number(b.dataset.horas);
  actualizarCotizacion();
});

/* Navegación */
document.getElementById("btn-atras").addEventListener("click", atras);
document.getElementById("nav-mis-solicitudes").addEventListener("click", () => irA("mis-solicitudes"));

/* Inicio: permite llegar directo con estudiante.html#mis-solicitudes */
pintarAreas();
if (location.hash === "#mis-solicitudes") { historial = ["area", "mis-solicitudes"]; render("mis-solicitudes"); }
else render("area");