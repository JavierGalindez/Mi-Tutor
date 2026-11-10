# ============================================================
# tutores.py - Base de conocimiento de Mi Tutor
# ------------------------------------------------------------
# Es la "memoria oficial" del negocio. orquestador.py convierte
# esta información en texto y se la entrega a Gemini para que
# responda SOLO con datos reales (sin inventar tutores ni precios).
#
# Los datos son los mismos que muestra la página web (js/app.js).
# Si cambias un tutor o un precio en la web, cámbialo también aquí.
# ============================================================

# ------------------------------------------------------------
# 1. Información general de la plataforma
# ------------------------------------------------------------
PLATAFORMA = {
    "nombre": "Mi Tutor",
    "eslogan": "Aprende con estudiantes que ya dominan lo que necesitas.",
    "que_es": (
        "Plataforma de tutorías de Ciencias Básicas (Matemáticas, Física y "
        "Química) de estudiante a estudiante, a precios accesibles. El "
        "estudiante que ya cursó y domina la materia le enseña directamente "
        "a otro estudiante."
    ),
    "comision_porcentaje": 10,  # Mi Tutor cobra 10 % sobre el valor del tutor
    "como_solicitar": [
        "Entrar a la página web de Mi Tutor y elegir un área o un tutor (botón 'Necesito un tutor' o el catálogo).",
        "El botón abre el chat de Telegram con Tuti, con el tutor o el área ya cargados.",
        "Preguntarle a Tuti lo que necesite; para ver el valor sin registrar nada, pulsar 'Cotizar'.",
        "Pulsar 'Solicitar tutoría' o escribir, por ejemplo, 'quiero 2 horas con Laura'.",
        "Indicar las horas (de 1 a 10) y confirmar; el sistema entrega un consecutivo SOL-0000.",
        "Mi Tutor revisa la solicitud con el tutor; el estado se consulta en 'Mis solicitudes'.",
    ],
    "ser_tutor": (
        "Cualquier estudiante que domine una materia puede postularse como "
        "tutor desde la página (botón 'Soy tutor'). Toda postulación pasa por "
        "un proceso de validación antes de aparecer en la plataforma. El tutor "
        "define su precio por hora, sus horarios y su modalidad."
    ),
    "modalidades": {
        "virtual": "Virtual",
        "presencial": "Presencial",
        "ambas": "Virtual o presencial",
    },
}

# ------------------------------------------------------------
# 2. Tipos de ayuda que puede pedir un estudiante
# ------------------------------------------------------------
NECESIDADES = [
    {"id": "tutoria",  "nombre": "Tutoría",                         "descripcion": "Acompañamiento continuo en la asignatura."},
    {"id": "parcial",  "nombre": "Preparación para parcial",        "descripcion": "Repaso intensivo antes de una evaluación."},
    {"id": "taller",   "nombre": "Ayuda con taller",                "descripcion": "Resolver dudas de un taller o guía puntual."},
    {"id": "refuerzo", "nombre": "Refuerzo de un tema específico",  "descripcion": "Profundizar en un tema que no quedó claro."},
]

# ------------------------------------------------------------
# 3. Áreas (los códigos coinciden con los botones de index.html)
# ------------------------------------------------------------
AREAS = [
    {
        "codigo": "TUT-MAT",
        "clave": "matematicas",
        "nombre": "Matemáticas",
        "emoji": "📐",
        "asignaturas": [
            "Matemáticas Básicas", "Cálculo I", "Cálculo II", "Cálculo III",
            "Álgebra", "Álgebra Lineal", "Geometría", "Ecuaciones Diferenciales",
            "Estadística", "Probabilidad",
        ],
    },
    {
        "codigo": "TUT-FIS",
        "clave": "fisica",
        "nombre": "Física",
        "emoji": "⚡",
        "asignaturas": [
            "Física I", "Física II", "Física III", "Mecánica",
            "Electricidad y Magnetismo", "Circuitos", "Termodinámica",
        ],
    },
    {
        "codigo": "TUT-QUI",
        "clave": "quimica",
        "nombre": "Química",
        "emoji": "🧪",
        "asignaturas": [
            "Química General", "Química I", "Química II", "Química Orgánica",
            "Química Inorgánica", "Estequiometría", "Termodinámica Química",
        ],
    },
]

# Temas de ejemplo por asignatura (sirven para orientar al estudiante)
TEMAS = {
    "Cálculo I": ["Límites", "Derivadas", "Aplicaciones de derivadas", "Funciones", "Continuidad"],
    "Cálculo II": ["Integrales", "Aplicaciones de integrales", "Series", "Técnicas de integración"],
    "Cálculo III": ["Integrales múltiples", "Campos vectoriales", "Coordenadas polares"],
    "Álgebra": ["Ecuaciones lineales", "Factorización", "Sistemas de ecuaciones", "Polinomios"],
    "Álgebra Lineal": ["Matrices", "Determinantes", "Espacios vectoriales", "Transformaciones lineales"],
    "Estadística": ["Medidas de tendencia central", "Distribuciones", "Regresión lineal"],
    "Física I": ["Cinemática", "Leyes de Newton", "Trabajo y energía", "Movimiento circular"],
    "Física II": ["Ondas", "Fluidos", "Óptica geométrica"],
    "Electricidad y Magnetismo": ["Campo eléctrico", "Ley de Coulomb", "Circuitos RC", "Inducción magnética"],
    "Termodinámica": ["Leyes de la termodinámica", "Ciclos térmicos", "Entropía"],
    "Química General": ["Estructura atómica", "Tabla periódica", "Enlaces químicos", "Reacciones químicas"],
    "Química Orgánica": ["Nomenclatura", "Hidrocarburos", "Grupos funcionales", "Reacciones orgánicas"],
    "Estequiometría": ["Balanceo de ecuaciones", "Reactivo límite", "Rendimiento de reacción"],
}

# ------------------------------------------------------------
# 4. Tutores (mismos datos que js/app.js)
#    precio = valor por HORA en pesos colombianos (COP)
# ------------------------------------------------------------
TUTORES = [
    {
        "codigo": "TUT-01", "nombre": "Laura Gómez", "area": "matematicas",
        "asignaturas": ["Matemáticas Básicas", "Cálculo I", "Cálculo II", "Álgebra"],
        "calificacion": 4.9, "tutorias": 32, "precio": 18000, "modalidad": "ambas",
        "disponibilidad": ["Lun 3–6pm", "Mié 4–7pm", "Sáb 10am–1pm"],
        "universidad": "Universidad Nacional",
        "experiencia": "Monitora de Cálculo I y II durante 2 años. Ha acompañado a más de 30 estudiantes.",
        "descripcion": "Explica paso a paso y con ejemplos gráficos. Nada de fórmulas sin entender de dónde salen.",
    },
    {
        "codigo": "TUT-02", "nombre": "Andrés Ríos", "area": "matematicas",
        "asignaturas": ["Álgebra Lineal", "Geometría", "Ecuaciones Diferenciales"],
        "calificacion": 4.7, "tutorias": 21, "precio": 17000, "modalidad": "ambas",
        "disponibilidad": ["Mar 2–5pm", "Jue 5–8pm"],
        "universidad": "Universidad de los Andes",
        "experiencia": "Tutor particular desde hace 1,5 años, enfocado en álgebra lineal y ecuaciones diferenciales.",
        "descripcion": "Convierte los ejercicios abstractos en problemas visuales.",
    },
    {
        "codigo": "TUT-03", "nombre": "Camila Torres", "area": "matematicas",
        "asignaturas": ["Estadística", "Probabilidad", "Cálculo III"],
        "calificacion": 4.8, "tutorias": 40, "precio": 20000, "modalidad": "presencial",
        "disponibilidad": ["Lun 9am–12m", "Vie 3–6pm"],
        "universidad": "Universidad Javeriana",
        "experiencia": "Auxiliar docente de Estadística I. Le encanta preparar simulacros de parcial.",
        "descripcion": "Trabaja con datos reales para que la estadística deje de sentirse abstracta.",
    },
    {
        "codigo": "TUT-04", "nombre": "Julián Peña", "area": "fisica",
        "asignaturas": ["Física I", "Física II", "Mecánica"],
        "calificacion": 4.6, "tutorias": 18, "precio": 16000, "modalidad": "virtual",
        "disponibilidad": ["Mié 6–9pm", "Sáb 2–5pm"],
        "universidad": "Universidad Nacional",
        "experiencia": "1 año como tutor de Física I. Usa simulaciones interactivas en sus sesiones.",
        "descripcion": "La física se aprende resolviendo, no memorizando. Practica muchos ejercicios con el estudiante.",
    },
    {
        "codigo": "TUT-05", "nombre": "Sofía Martínez", "area": "fisica",
        "asignaturas": ["Electricidad y Magnetismo", "Circuitos", "Física III"],
        "calificacion": 4.9, "tutorias": 27, "precio": 19000, "modalidad": "ambas",
        "disponibilidad": ["Lun 4–7pm", "Jue 4–7pm"],
        "universidad": "Universidad de los Andes",
        "experiencia": "Ganadora de olimpiadas de física en el colegio, ahora tutora de electromagnetismo.",
        "descripcion": "Explica los circuitos con analogías cotidianas antes de entrar a las fórmulas.",
    },
    {
        "codigo": "TUT-06", "nombre": "Diego Herrera", "area": "fisica",
        "asignaturas": ["Termodinámica", "Física I"],
        "calificacion": 4.5, "tutorias": 12, "precio": 15000, "modalidad": "virtual",
        "disponibilidad": ["Mar 5–8pm"],
        "universidad": "Universidad Distrital",
        "experiencia": "Estudiante de Ingeniería Mecánica, tutor desde hace 8 meses.",
        "descripcion": "Se enfoca en que entiendas el concepto físico antes de manipular la fórmula.",
    },
    {
        "codigo": "TUT-07", "nombre": "Valentina Cruz", "area": "quimica",
        "asignaturas": ["Química General", "Química I", "Estequiometría"],
        "calificacion": 4.8, "tutorias": 25, "precio": 17000, "modalidad": "ambas",
        "disponibilidad": ["Lun 2–5pm", "Vie 10am–1pm"],
        "universidad": "Universidad Javeriana",
        "experiencia": "Monitora de laboratorio de Química General por 3 semestres.",
        "descripcion": "Usa ejemplos de la vida diaria para que la química deje de ser abstracta.",
    },
    {
        "codigo": "TUT-08", "nombre": "Mateo Salazar", "area": "quimica",
        "asignaturas": ["Química Orgánica", "Química Inorgánica", "Química II"],
        "calificacion": 4.7, "tutorias": 19, "precio": 18000, "modalidad": "presencial",
        "disponibilidad": ["Mié 3–6pm", "Sáb 9am–12m"],
        "universidad": "Universidad Nacional",
        "experiencia": "Tutor de química orgánica desde hace un año, enfocado en nomenclatura y mecanismos.",
        "descripcion": "Dibuja cada molécula con el estudiante hasta que la estructura tenga sentido.",
    },
]

# ------------------------------------------------------------
# 5. Preguntas frecuentes (respuestas oficiales)
#    Agrega aquí todo lo que quieras que el bot sepa responder.
# ------------------------------------------------------------
PREGUNTAS_FRECUENTES = [
    {
        "pregunta": "¿Cuánto cuesta una tutoría?",
        "respuesta": "Cada tutor define su precio por hora (entre $15.000 y $20.000 COP). "
                     "Al valor del tutor se le suma una comisión del 10 % de Mi Tutor. "
                     "Ejemplo: 1 hora con un tutor de $18.000 = $18.000 + $1.800 = $19.800.",
    },
    {
        "pregunta": "¿Cuántas horas puedo pedir?",
        "respuesta": "Horas enteras, hasta lo que dure el horario elegido del tutor (por ejemplo, Lun 3–6pm permite hasta 3 horas). El total es horas × (precio por hora del tutor + 10 % de comisión). No se manejan fracciones de hora.",
    },
    {
        "pregunta": "¿Las tutorías son virtuales o presenciales?",
        "respuesta": "Depende del tutor: algunos solo virtual, otros solo presencial y otros ambas. "
                     "La modalidad aparece en el perfil de cada tutor.",
    },
    {
        "pregunta": "¿Quiénes son los tutores?",
        "respuesta": "Estudiantes universitarios que ya cursaron y dominan la materia. "
                     "Su postulación es validada antes de aparecer en la plataforma.",
    },
    {
        "pregunta": "¿Qué materias hay?",
        "respuesta": "Por ahora solo Ciencias Básicas: Matemáticas, Física y Química.",
    },
]