/* =========================================================
   Mi Tutor — app.js
   Datos compartidos y utilidades de las tres páginas.
   Los tutores, códigos y precios DEBEN coincidir con tutores.py.
   ========================================================= */

/* ADAPTAR A SU MVP: usuario del bot (sin @), igual a USUARIO_BOT. */
const MT_BOT = "MiTutorKevin_bot";
/* Comisión de Mi Tutor, igual a comision_porcentaje en tutores.py */
const MT_COMISION = 10;

/* Deep link de Telegram. https://t.me funciona en PC y celular,
   con o sin la app instalada (tg:// fallaba en navegadores de PC). */
function mtEnlaceTelegram(referencia) {
  return "https://t.me/" + MT_BOT + (referencia ? "?start=" + encodeURIComponent(referencia) : "");
}

function mtSlug(texto) {
  return texto.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
}
function mtFormatoCOP(valor) {
  return "$" + Math.round(valor).toLocaleString("es-CO");
}
function mtIniciales(nombre) {
  return nombre.split(" ").filter(Boolean).slice(0, 2).map((p) => p[0].toUpperCase()).join("");
}
/* Precio por hora con comisión, en enteros (igual que Python). */
function mtPrecioConComision(precioTutor) {
  return precioTutor + Math.floor((precioTutor * MT_COMISION) / 100);
}
function mtCotizar(precioTutor, horas) {
  const subtotal = precioTutor * horas;
  const total = mtPrecioConComision(precioTutor) * horas;
  return { subtotal, comision: total - subtotal, total };
}
function mtGet(clave, porDefecto) {
  try { const raw = localStorage.getItem(clave); return raw ? JSON.parse(raw) : porDefecto; }
  catch (e) { return porDefecto; }
}
function mtSet(clave, valor) {
  try { localStorage.setItem(clave, JSON.stringify(valor)); } catch (e) { /* modo privado */ }
}
function mtEscapar(texto) {
  return String(texto).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

/* ---------- Áreas (códigos iguales a AREAS en tutores.py) ---------- */
const MT_AREAS = {
  matematicas: {
    codigo: "TUT-MAT", label: "Matemáticas", simbolo: "∑", color: "var(--math)",
    asignaturas: ["Matemáticas Básicas", "Cálculo I", "Cálculo II", "Cálculo III", "Álgebra",
      "Álgebra Lineal", "Geometría", "Ecuaciones Diferenciales", "Estadística", "Probabilidad"],
  },
  fisica: {
    codigo: "TUT-FIS", label: "Física", simbolo: "F", color: "var(--physics)",
    asignaturas: ["Física I", "Física II", "Física III", "Mecánica",
      "Electricidad y Magnetismo", "Circuitos", "Termodinámica"],
  },
  quimica: {
    codigo: "TUT-QUI", label: "Química", simbolo: "H₂O", color: "var(--chem)",
    asignaturas: ["Química General", "Química I", "Química II", "Química Orgánica",
      "Química Inorgánica", "Estequiometría", "Termodinámica Química"],
  },
};

const MT_NECESIDADES = [
  { id: "tutoria", label: "Tutoría", desc: "Acompañamiento continuo en la asignatura." },
  { id: "parcial", label: "Preparación para parcial", desc: "Repaso intensivo antes de tu evaluación." },
  { id: "taller", label: "Ayuda con taller", desc: "Resolver dudas de un taller o guía puntual." },
  { id: "refuerzo", label: "Refuerzo de un tema", desc: "Profundizar en un tema que no te quedó claro." },
];

const MT_TEMAS = {
  "calculo-i": ["Límites", "Derivadas", "Aplicaciones de derivadas", "Funciones", "Continuidad"],
  "calculo-ii": ["Integrales", "Aplicaciones de integrales", "Series", "Técnicas de integración"],
  "calculo-iii": ["Integrales múltiples", "Campos vectoriales", "Coordenadas polares"],
  "algebra": ["Ecuaciones lineales", "Factorización", "Sistemas de ecuaciones", "Polinomios"],
  "algebra-lineal": ["Matrices", "Determinantes", "Espacios vectoriales", "Transformaciones lineales"],
  "estadistica": ["Medidas de tendencia central", "Distribuciones", "Regresión lineal"],
  "fisica-i": ["Cinemática", "Leyes de Newton", "Trabajo y energía", "Movimiento circular"],
  "fisica-ii": ["Ondas", "Fluidos", "Óptica geométrica"],
  "electricidad-y-magnetismo": ["Campo eléctrico", "Ley de Coulomb", "Circuitos RC", "Inducción magnética"],
  "termodinamica": ["Leyes de la termodinámica", "Ciclos térmicos", "Entropía"],
  "quimica-general": ["Estructura atómica", "Tabla periódica", "Enlaces químicos", "Reacciones químicas"],
  "quimica-organica": ["Nomenclatura", "Hidrocarburos", "Grupos funcionales", "Reacciones orgánicas"],
  "estequiometria": ["Balanceo de ecuaciones", "Reactivo límite", "Rendimiento de reacción"],
};
const MT_TEMAS_DEFAULT = ["Conceptos básicos", "Ejercicios prácticos", "Aplicaciones", "Repaso general"];
function mtTemasDe(slug) { return MT_TEMAS[slug] || MT_TEMAS_DEFAULT; }

const MT_MODALIDAD = { virtual: "Virtual", presencial: "Presencial", ambas: "Virtual o presencial" };

/* ---------- Tutores (mismos códigos y precios que tutores.py) ---------- */
const MT_TUTORES = [
  { codigo: "TUT-01", nombre: "Laura Gómez", area: "matematicas",
    asignaturas: ["Matemáticas Básicas", "Cálculo I", "Cálculo II", "Álgebra"],
    calificacion: 4.9, tutorias: 32, precio: 18000, modalidad: "ambas",
    disponibilidad: ["Lun 3–6pm", "Mié 4–7pm", "Sáb 10am–1pm"], universidad: "Universidad Nacional",
    experiencia: "Monitora de Cálculo I y II durante 2 años. Ha acompañado a más de 30 estudiantes.",
    descripcion: "Explico paso a paso y con ejemplos gráficos. Nada de fórmulas sin entender de dónde salen." },
  { codigo: "TUT-02", nombre: "Andrés Ríos", area: "matematicas",
    asignaturas: ["Álgebra Lineal", "Geometría", "Ecuaciones Diferenciales"],
    calificacion: 4.7, tutorias: 21, precio: 17000, modalidad: "ambas",
    disponibilidad: ["Mar 2–5pm", "Jue 5–8pm"], universidad: "Universidad de los Andes",
    experiencia: "Tutor particular desde hace año y medio, enfocado en álgebra lineal y ecuaciones diferenciales.",
    descripcion: "Convierto los ejercicios abstractos en problemas visuales; así se entienden mucho mejor." },
  { codigo: "TUT-03", nombre: "Camila Torres", area: "matematicas",
    asignaturas: ["Estadística", "Probabilidad", "Cálculo III"],
    calificacion: 4.8, tutorias: 40, precio: 20000, modalidad: "presencial",
    disponibilidad: ["Lun 9am–12m", "Vie 3–6pm"], universidad: "Universidad Javeriana",
    experiencia: "Auxiliar docente de Estadística I. Le encanta preparar simulacros de parcial.",
    descripcion: "Trabajamos con datos reales para que la estadística deje de sentirse abstracta." },
  { codigo: "TUT-04", nombre: "Julián Peña", area: "fisica",
    asignaturas: ["Física I", "Física II", "Mecánica"],
    calificacion: 4.6, tutorias: 18, precio: 16000, modalidad: "virtual",
    disponibilidad: ["Mié 6–9pm", "Sáb 2–5pm"], universidad: "Universidad Nacional",
    experiencia: "Un año como tutor de Física I. Usa simulaciones interactivas en sus sesiones.",
    descripcion: "La física se aprende resolviendo, no memorizando. Practicamos muchos ejercicios juntos." },
  { codigo: "TUT-05", nombre: "Sofía Martínez", area: "fisica",
    asignaturas: ["Electricidad y Magnetismo", "Circuitos", "Física III"],
    calificacion: 4.9, tutorias: 27, precio: 19000, modalidad: "ambas",
    disponibilidad: ["Lun 4–7pm", "Jue 4–7pm"], universidad: "Universidad de los Andes",
    experiencia: "Ganadora de olimpiadas de física en el colegio, ahora tutora de electromagnetismo.",
    descripcion: "Explico los circuitos con analogías cotidianas antes de entrar a las fórmulas." },
  { codigo: "TUT-06", nombre: "Diego Herrera", area: "fisica",
    asignaturas: ["Termodinámica", "Física I"],
    calificacion: 4.5, tutorias: 12, precio: 15000, modalidad: "virtual",
    disponibilidad: ["Mar 5–8pm"], universidad: "Universidad Distrital",
    experiencia: "Estudiante de Ingeniería Mecánica, tutor desde hace 8 meses.",
    descripcion: "Me enfoco en que entiendas el concepto físico antes de manipular la fórmula." },
  { codigo: "TUT-07", nombre: "Valentina Cruz", area: "quimica",
    asignaturas: ["Química General", "Química I", "Estequiometría"],
    calificacion: 4.8, tutorias: 25, precio: 17000, modalidad: "ambas",
    disponibilidad: ["Lun 2–5pm", "Vie 10am–1pm"], universidad: "Universidad Javeriana",
    experiencia: "Monitora de laboratorio de Química General por 3 semestres.",
    descripcion: "Uso ejemplos de la vida diaria para que la química deje de ser abstracta." },
  { codigo: "TUT-08", nombre: "Mateo Salazar", area: "quimica",
    asignaturas: ["Química Orgánica", "Química Inorgánica", "Química II"],
    calificacion: 4.7, tutorias: 19, precio: 18000, modalidad: "presencial",
    disponibilidad: ["Mié 3–6pm", "Sáb 9am–12m"], universidad: "Universidad Nacional",
    experiencia: "Tutor de química orgánica desde hace un año, enfocado en nomenclatura y mecanismos.",
    descripcion: "Dibujamos cada molécula juntos hasta que la estructura tenga sentido para ti." },
];

function mtTutoresPorAsignatura(areaKey, asignatura) {
  const exactos = MT_TUTORES.filter((t) => t.area === areaKey && t.asignaturas.includes(asignatura));
  return exactos.length ? exactos : MT_TUTORES.filter((t) => t.area === areaKey);
}
function mtTutorPorCodigo(codigo) { return MT_TUTORES.find((t) => t.codigo === codigo); }

/* ---------- Fila de tutor reutilizable (index) ---------- */
function mtFilaTutor(t) {
  const area = MT_AREAS[t.area];
  const fila = document.createElement("article");
  fila.className = "fila-tutor";
  fila.dataset.area = t.area;
  fila.innerHTML = `
    <div class="iniciales" style="background:${area.color}" aria-hidden="true">${mtIniciales(t.nombre)}</div>
    <div>
      <h3>${mtEscapar(t.nombre)}</h3>
      <p class="materias">${mtEscapar(t.asignaturas.join(", "))}</p>
      <div class="meta"><span class="codigo">${t.codigo}</span><span>${t.calificacion} de 5 en ${t.tutorias} tutorías</span><span>${MT_MODALIDAD[t.modalidad]}</span></div>
    </div>
    <div class="precio"><strong>${mtFormatoCOP(mtPrecioConComision(t.precio))}</strong><span>por hora, comisión incluida</span></div>
    <a class="boton boton-sm" href="${mtEnlaceTelegram(t.codigo)}" target="_blank" rel="noopener">Elegir en Telegram</a>`;
  return fila;
}

/* ---------- Comportamiento común ---------- */
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-anio]").forEach((el) => { el.textContent = new Date().getFullYear(); });
  /* Todo elemento con data-telegram="REFERENCIA" apunta al bot. */
  document.querySelectorAll("[data-telegram]").forEach((el) => {
    el.href = mtEnlaceTelegram(el.dataset.telegram);
    el.target = "_blank";
    el.rel = "noopener";
  });
});
