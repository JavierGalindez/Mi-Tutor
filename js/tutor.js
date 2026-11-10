/* =========================================================
   Mi Tutor — tutor.js
   Postulación, evaluación simulada y panel del tutor.
   Prototipo: los datos viven solo en este navegador.
   ========================================================= */

const PASOS_EVALUACION = [
  { titulo: "Registro de información", desc: "Recibimos los datos de tu postulación." },
  { titulo: "Validación académica", desc: "Verificamos universidad, programa y semestre." },
  { titulo: "Evaluación de conocimientos", desc: "Revisamos tu dominio de las materias postuladas." },
  { titulo: "Revisión del perfil", desc: "Una persona del equipo revisa tu postulación completa." },
  { titulo: "Aprobado como tutor", desc: "Tu perfil queda listo para recibir solicitudes." },
];
const CLAVE = "mt_postulacion";

function mostrar(id) {
  document.querySelectorAll(".etapa").forEach((s) => s.classList.remove("activa"));
  document.getElementById(id).classList.add("activa");
  const h = document.querySelector("#" + id + " h1");
  h.setAttribute("tabindex", "-1"); h.focus({ preventScroll: true });
  window.scrollTo({ top: 0, behavior: "smooth" });
}

/* Materias agrupadas por área */
function pintarMaterias() {
  const cont = document.getElementById("materias");
  Object.entries(MT_AREAS).forEach(([key, area]) => {
    const grupo = document.createElement("div");
    grupo.className = "grupo-materias";
    grupo.innerHTML = `<h4>${area.label}</h4><div class="casillas">${area.asignaturas.map((n) =>
      `<label class="casilla"><input type="checkbox" value="${key}|${mtEscapar(n)}"><span>${mtEscapar(n)}</span></label>`).join("")}</div>`;
    cont.appendChild(grupo);
  });
}

document.getElementById("form-postulacion").addEventListener("submit", (e) => {
  e.preventDefault();
  const form = e.target;
  const materias = [...form.querySelectorAll("#materias input:checked")].map((el) => {
    const [area, nombre] = el.value.split("|"); return { area, nombre };
  });
  document.getElementById("error-materias").textContent = materias.length ? "" : "Elige al menos una materia que domines.";
  const invalido = [...form.querySelectorAll("[required]")].find((c) => !c.checkValidity());
  document.getElementById("error-form").textContent = invalido ? "Completa los campos obligatorios: " + invalido.labels[0].textContent + "." : "";
  if (invalido) { invalido.focus(); return; }
  if (!materias.length) return;
  const v = (id) => document.getElementById(id).value.trim();
  mtSet(CLAVE, {
    nombre: v("p-nombre"), correo: v("p-correo"), universidad: v("p-universidad"), programa: v("p-programa"),
    semestre: v("p-semestre"), nivel: v("p-nivel"), materias, disponibilidad: v("p-disponibilidad"),
    modalidad: v("p-modalidad"), experiencia: v("p-experiencia"), motivacion: v("p-motivacion"),
    paso: 0, aprobado: false, precio: 15000, creada: new Date().toISOString(),
  });
  irAEvaluacion();
});

function pintarEvaluacion() {
  const p = mtGet(CLAVE, null);
  const lista = document.getElementById("linea-tiempo");
  lista.innerHTML = "";
  PASOS_EVALUACION.forEach((paso, i) => {
    const li = document.createElement("li");
    const hecho = i < p.paso || (p.aprobado && i === p.paso);
    li.className = hecho ? "hecho" : i === p.paso ? "actual" : "";
    li.innerHTML = `<span class="punto">${hecho ? "✓" : i + 1}</span><div><h3>${paso.titulo}</h3><p>${paso.desc}</p></div>`;
    lista.appendChild(li);
  });
  document.getElementById("btn-avanzar").hidden = p.aprobado;
  document.getElementById("btn-ir-panel").hidden = !p.aprobado;
  document.getElementById("t-eval").textContent = p.aprobado ? "¡Postulación aprobada!" : "Tu postulación está en revisión";
}
function irAEvaluacion() { pintarEvaluacion(); mostrar("et-evaluacion"); }

document.getElementById("btn-avanzar").addEventListener("click", () => {
  const p = mtGet(CLAVE, null);
  p.paso = Math.min(p.paso + 1, PASOS_EVALUACION.length - 1);
  p.aprobado = p.paso === PASOS_EVALUACION.length - 1;
  mtSet(CLAVE, p);
  pintarEvaluacion();
});

function ayudaPrecio() {
  const precio = parseInt(document.getElementById("panel-precio").value, 10) || 0;
  document.getElementById("panel-precio-ayuda").textContent = precio
    ? `El estudiante verá ${mtFormatoCOP(mtPrecioConComision(precio))} por hora (tu tarifa más 10 %).` : "";
}
document.getElementById("panel-precio").addEventListener("input", ayudaPrecio);

function irAPanel() {
  const p = mtGet(CLAVE, null);
  if (!p || !p.aprobado) return;
  document.getElementById("nav-mi-panel").hidden = false;
  document.getElementById("panel-resumen").innerHTML =
    `<strong>${mtEscapar(p.nombre)}</strong>, ${mtEscapar(p.universidad)}.<br>Materias: ${mtEscapar(p.materias.map((m) => m.nombre).join(", "))}.`;
  document.getElementById("panel-precio").value = p.precio;
  document.getElementById("panel-modalidad").value = p.modalidad;
  document.getElementById("panel-disponibilidad").value = p.disponibilidad;
  ayudaPrecio();
  mostrar("et-panel");
}
document.getElementById("btn-ir-panel").addEventListener("click", irAPanel);
document.getElementById("nav-mi-panel").addEventListener("click", irAPanel);

document.getElementById("form-perfil").addEventListener("submit", (e) => {
  e.preventDefault();
  const p = mtGet(CLAVE, null);
  p.precio = parseInt(document.getElementById("panel-precio").value, 10) || 15000;
  p.modalidad = document.getElementById("panel-modalidad").value;
  p.disponibilidad = document.getElementById("panel-disponibilidad").value.trim();
  mtSet(CLAVE, p);
  const b = document.getElementById("btn-guardar");
  b.textContent = "Cambios guardados";
  setTimeout(() => (b.textContent = "Guardar cambios"), 1600);
});

document.getElementById("btn-postularme").addEventListener("click", () => mostrar("et-postulacion"));
document.getElementById("btn-reiniciar").addEventListener("click", () => {
  try { localStorage.removeItem(CLAVE); } catch (e) { /* sin almacenamiento */ }
  location.reload();
});

(function iniciar() {
  pintarMaterias();
  const p = mtGet(CLAVE, null);
  if (!p) mostrar("et-intro");
  else if (p.aprobado) irAPanel();
  else irAEvaluacion();
})();
