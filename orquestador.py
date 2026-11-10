# ============================================================
# orquestador.py — Asistente "Tuti" de Mi Tutor en Telegram
# ------------------------------------------------------------
# Equivale al pizza.py de las guías, adaptado a Mi Tutor.
#
# Landing (index.html / estudiante.html)
#     ↓ deep link https://t.me/MiTutor777_bot?start=TUT-01
# Telegram → orquestador.py → tutores.py (catálogo)
#                           → SQLite (solicitudes persistentes)
#                           → Groq (principal) / Gemini (emergente)
#
# Bloques (mismo orden de las guías):
#   A. Herramientas, configuración y catálogo
#   B. Base de datos y migración (Semana 03 → Semana 04)
#   C. Validar cantidad y guardar la solicitud
#   D. Consultar, mostrar y cambiar estados
#   E. Asistentes de IA y mensajes del bot
#   F. Cancelación, cotización y atención del cliente
#   G. Conexión con Telegram
#   H. Verificar el proyecto e iniciar
#
# Convención de comentarios:
#   NUEVO SEMANA 03 / NUEVO SEMANA 04  → funciones añadidas
#   ACTUALIZADO SEMANA 04              → comportamiento ampliado
#   ADAPTAR A SU MVP                   → contenido propio de Mi Tutor
#
# IMPORTANTE: el bot SOLO responde mientras este programa esté
# ejecutándose. Ejecute una sola instancia (ver Iniciar.bat).
# ============================================================


# ========================================================
# A. HERRAMIENTAS Y CONFIGURACIÓN DEL PROYECTO
# ========================================================
import os
import sys

# Permitir emojis en la consola de Windows sin errores.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# NUEVO SEMANA 03: herramientas incluidas en Python (no usan pip).
import re
import json
import time
import sqlite3
import unicodedata
from pathlib import Path
from datetime import datetime

# Carpeta de este archivo; la base y las librerías viven aquí.
BASE = Path(__file__).resolve().parent
LIBS = BASE / "libs"
sys.path.insert(0, str(LIBS))

# INICIO NUEVO SEMANA 04: CONFIGURACIÓN PARA OTRO MVP
# ADAPTAR A SU MVP: nombre del negocio, usuario del bot y base.
NOMBRE_NEGOCIO = "Mi Tutor"
USUARIO_BOT = "MiTutor777_bot"          # sin @
DB = BASE / "mitutor.db"
# ADAPTAR A SU MVP: prefijo visible del consecutivo (SOL-0001).
PREFIJO = "SOL"
# ADAPTAR A SU MVP: la "cantidad" de Mi Tutor son HORAS de tutoría.
CANTIDAD_MAXIMA = 10
UNIDAD = "horas"
# FIN NUEVO SEMANA 04: CONFIGURACIÓN PARA OTRO MVP

# Archivo temporal con el que el bot avisa a iniciar.py que está listo.
ARCHIVO_LISTO = BASE / ".bot_listo.json"

# CONSERVAMOS la base de conocimiento de Semana 02.
from tutores import (  # noqa: E402
    PLATAFORMA, NECESIDADES, AREAS, TEMAS, TUTORES, PREGUNTAS_FRECUENTES
)

COMISION = PLATAFORMA["comision_porcentaje"]
NOMBRE_AREA = {a["clave"]: a["nombre"] for a in AREAS}
AREAS_POR_CODIGO = {a["codigo"].upper(): a for a in AREAS}

# NUEVO SEMANA 03: índice del catálogo por código.
# En Mi Tutor el "producto" es una hora de tutoría con un tutor.
# precio = valor por hora del tutor + comisión de Mi Tutor (entero).
# Así total = cantidad × precio_unitario se cumple siempre en SQLite.
PRODUCTOS = {}
for _t in TUTORES:
    PRODUCTOS[_t["codigo"].upper()] = {
        "codigo": _t["codigo"].upper(),
        "nombre": f"Tutoría con {_t['nombre']}",
        "tutor": _t["nombre"],
        "area": NOMBRE_AREA[_t["area"]],
        "area_clave": _t["area"],
        "precio_tutor": _t["precio"],
        "precio": _t["precio"] + _t["precio"] * COMISION // 100,
        "descripcion": (
            f"{', '.join(_t['asignaturas'])}. "
            f"{PLATAFORMA['modalidades'][_t['modalidad']]}. "
            f"Horarios: {', '.join(_t['disponibilidad'])}."
        ),
    }

# Memorias temporales (se reinician al cerrar el bot).
# Las solicitudes confirmadas viven en SQLite y NO se pierden.
sesiones = {}                 # chat_id -> {"codigo", "area", "etapa"}
memoria_usuarios = {}         # chat_id -> {"id", "modelo"} de Gemini
memoria_conversaciones = {}   # chat_id -> historial compartido por proveedores


# --------------------------------------------------------
# A.1. NUEVO SEMANA 04: PREPARAR LIBRERÍAS AUTOMÁTICAMENTE
# --------------------------------------------------------
def preparar_librerias():
    # libs se entrega vacía; solo se completa si hace falta.
    import subprocess
    import importlib
    from importlib import metadata

    LIBS.mkdir(exist_ok=True)
    requeridas = {"python-dotenv": "1.2.4",
                  "python-telegram-bot": "22.8", "google-genai": "2.30.1"}
    instaladas = {d.metadata["Name"].lower(): d.version
                  for d in metadata.distributions(path=[str(LIBS)])}
    if all(instaladas.get(n) == v for n, v in requeridas.items()):
        return
    print("📦 Preparando librerías automáticamente. Espere...")
    pip = subprocess.run([sys.executable, "-m", "pip", "--version"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    with open(BASE / "instalacion_librerias.log", "a", encoding="utf-8") as registro:
        if pip.returncode:
            subprocess.run([sys.executable, "-m", "ensurepip", "--upgrade"],
                           check=True, stdout=registro, stderr=registro)
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade",
                        "--target", str(LIBS), "--disable-pip-version-check",
                        *[n + "==" + v for n, v in requeridas.items()]],
                       check=True, stdout=registro, stderr=registro)
    importlib.invalidate_caches()
    print("✅ Librerías listas. No necesita escribir comandos de instalación.")


# ========================================================
# B. INICIO ACTUALIZADO SEMANA 04: BASE Y MIGRACIÓN
# ========================================================
# Se conservan la tabla "pedidos" y sus columnas de las guías.
# En Mi Tutor cada fila es una SOLICITUD de tutoría.
ESTADOS = ("PENDIENTE", "APROBADO", "NO APROBADO", "CANCELADO")


def conectar():
    con = sqlite3.connect(DB, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def crear_tabla(con, nombre):
    # nombre recibe solo un nombre interno, nunca datos del usuario.
    con.execute(f"""CREATE TABLE {nombre} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        consecutivo TEXT UNIQUE,
        cliente TEXT NOT NULL,
        chat_id INTEGER NOT NULL,
        codigo_producto TEXT NOT NULL,
        nombre_producto TEXT NOT NULL,
        cantidad INTEGER NOT NULL CHECK(cantidad > 0),
        precio_unitario INTEGER NOT NULL CHECK(precio_unitario > 0),
        total INTEGER NOT NULL,
        fecha TEXT NOT NULL,
        hora TEXT NOT NULL,
        estado TEXT NOT NULL DEFAULT 'PENDIENTE'
            CHECK(estado IN ('PENDIENTE','APROBADO',
                             'NO APROBADO','CANCELADO')),
        telegram_update_id INTEGER NOT NULL UNIQUE,
        motivo TEXT NOT NULL DEFAULT '',
        actualizado_en TEXT NOT NULL DEFAULT '',
        actualizado_por TEXT NOT NULL DEFAULT '',
        CHECK(total = cantidad * precio_unitario)
    )""")


def iniciar_db(silencioso=False):
    con = conectar()
    try:
        # Evitar que dos programas migren simultáneamente.
        con.execute("BEGIN IMMEDIATE")
        existe = con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='pedidos'"
        ).fetchone()
        if not existe:
            crear_tabla(con, "pedidos")
            if not silencioso:
                print("✅ Base de datos creada:", DB)
        else:
            columnas = [f[1] for f in con.execute("PRAGMA table_info(pedidos)")]
            base = ["id", "consecutivo", "cliente", "chat_id",
                    "codigo_producto", "nombre_producto", "cantidad",
                    "precio_unitario", "total", "fecha", "hora",
                    "estado", "telegram_update_id"]
            if not set(base).issubset(columnas):
                raise ValueError("La base no corresponde a Semana 03.")
            version = con.execute("PRAGMA user_version").fetchone()[0]
            if version > 4:
                raise ValueError("La base pertenece a una semana posterior.")
            if version < 4:
                # Semana 03 solo admitía PENDIENTE en su CHECK.
                # Añadir columnas no cambia esa restricción:
                # se recrea la tabla dentro de UNA transacción.
                conteo = con.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]
                secuencia = con.execute(
                    "SELECT seq FROM sqlite_sequence WHERE name='pedidos'"
                ).fetchone()
                crear_tabla(con, "pedidos_semana04")
                campos = base + ["motivo", "actualizado_en", "actualizado_por"]
                seleccion = [c if c in columnas else "''" for c in campos]
                con.execute(
                    "INSERT INTO pedidos_semana04 (" + ",".join(campos) +
                    ") SELECT " + ",".join(seleccion) + " FROM pedidos"
                )
                nuevo = con.execute(
                    "SELECT COUNT(*) FROM pedidos_semana04"
                ).fetchone()[0]
                if conteo != nuevo:
                    raise ValueError("No coincidió el conteo de solicitudes.")
                con.execute("DROP TABLE pedidos")
                con.execute("ALTER TABLE pedidos_semana04 RENAME TO pedidos")
                # Conservar la secuencia para no reutilizar consecutivos.
                if secuencia:
                    con.execute(
                        "UPDATE sqlite_sequence SET seq=MAX(seq, ?) "
                        "WHERE name='pedidos'", (secuencia[0],)
                    )
                print(f"✅ Migración Semana 04: {conteo} solicitudes conservadas")
            elif not {"motivo", "actualizado_en", "actualizado_por"}.issubset(columnas):
                raise ValueError("Faltan columnas de Semana 04.")
        # NUEVO SEMANA 04: historial de cada decisión sin borrar la solicitud.
        con.execute("""CREATE TABLE IF NOT EXISTS historial_estados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id INTEGER NOT NULL REFERENCES pedidos(id),
            estado_anterior TEXT NOT NULL,
            estado_nuevo TEXT NOT NULL,
            actor TEXT NOT NULL,
            motivo TEXT NOT NULL,
            fecha_hora TEXT NOT NULL
        )""")
        con.execute("PRAGMA user_version = 4")
        con.commit()
        if not silencioso:
            print("✅ SQLite Semana 04 verificado:", DB)
    except Exception:
        con.rollback()  # Si falla, no queda una migración parcial.
        raise
    finally:
        con.close()


def contar_pedidos():
    con = conectar()
    try:
        return con.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]
    finally:
        con.close()
# FIN ACTUALIZADO SEMANA 04: BASE Y MIGRACIÓN


# ========================================================
# C. NUEVO SEMANA 03: VALIDAR Y GUARDAR LA SOLICITUD
# ========================================================
# Python calcula el total con el catálogo oficial.
# La IA no fija precios ni escribe registros en SQLite.
def validar_cantidad(texto):
    # Solo enteros positivos: rechaza cero, decimales y texto.
    if not re.fullmatch(r"[0-9]{1,3}", texto.strip()):
        raise ValueError(f"Escribe un número entero de 1 a {CANTIDAD_MAXIMA}.")
    cantidad = int(texto)
    if not 1 <= cantidad <= CANTIDAD_MAXIMA:
        raise ValueError(f"Las {UNIDAD} deben estar entre 1 y {CANTIDAD_MAXIMA}.")
    return cantidad


def guardar_pedido(cliente, chat_id, codigo, cantidad, update_id, franja=""):
    if codigo not in PRODUCTOS:
        raise ValueError("Tutor desconocido.")
    if type(cantidad) is not int or not 1 <= cantidad <= CANTIDAD_MAXIMA:
        raise ValueError("Cantidad inválida.")
    producto = PRODUCTOS[codigo]
    precio = producto["precio"]          # Pesos enteros, con comisión.
    total = cantidad * precio
    ahora = datetime.now()
    con = conectar()
    try:
        con.execute("BEGIN IMMEDIATE")
        existente = con.execute(
            "SELECT * FROM pedidos WHERE telegram_update_id = ?", (update_id,)
        ).fetchone()
        if existente:
            con.commit()
            return dict(existente)       # Un reintento no duplica.
        cursor = con.execute("""
            INSERT INTO pedidos (
                cliente, chat_id, codigo_producto, nombre_producto,
                cantidad, precio_unitario, total, fecha, hora,
                telegram_update_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            # El horario se guarda junto al nombre: la tabla no cambia.
            cliente, chat_id, codigo,
            producto["nombre"] + (f" ({franja})" if franja else ""), cantidad, precio,
            total, ahora.strftime("%Y-%m-%d"), ahora.strftime("%H:%M:%S"),
            update_id,
        ))
        # SQLite asigna el id; no usamos COUNT(*) + 1.
        numero = cursor.lastrowid
        consecutivo = f"{PREFIJO}-{numero:04d}"
        con.execute("UPDATE pedidos SET consecutivo = ? WHERE id = ?",
                    (consecutivo, numero))
        pedido = dict(con.execute(
            "SELECT * FROM pedidos WHERE id = ?", (numero,)
        ).fetchone())
        con.commit()                     # Inserción y consecutivo juntos.
        return pedido
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


# ========================================================
# D. CONSULTAR, MOSTRAR Y DECIDIR
# ========================================================
# --------------------------------------------------------
# D.1. ACTUALIZADO SEMANA 04: consultar con fechas y estado
# --------------------------------------------------------
def consultar(tipo="todos", consecutivo=None, chat_id=None,
              desde="", hasta="", estado=""):
    if tipo == "pendientes":
        estado = "PENDIENTE"
    elif tipo not in ("todos", "pedido"):
        raise ValueError("Consulta desconocida.")
    if estado and estado not in ESTADOS:
        raise ValueError("Estado desconocido.")
    for fecha in (desde, hasta):
        if fecha:
            if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", fecha):
                raise ValueError("Use una fecha válida AAAA-MM-DD.")
            datetime.strptime(fecha, "%Y-%m-%d")
    if desde and hasta and desde > hasta:
        raise ValueError("«Desde» no puede ser posterior a «Hasta».")
    condiciones, parametros = [], []
    for campo, operador, valor in (
        ("consecutivo", "=", consecutivo if tipo == "pedido" else None),
        ("chat_id", "=", chat_id), ("fecha", ">=", desde or None),
        ("fecha", "<=", hasta or None), ("estado", "=", estado or None),
    ):
        if valor is not None:
            condiciones.append(campo + " " + operador + " ?")
            parametros.append(valor)
    sql = "SELECT * FROM pedidos"
    if condiciones:
        sql += " WHERE " + " AND ".join(condiciones)
    sql += " ORDER BY id"
    con = conectar()
    try:
        return [dict(f) for f in con.execute(sql, parametros)]
    finally:
        con.close()


def historial(pedido_id):
    con = conectar()
    try:
        return [dict(f) for f in con.execute(
            "SELECT * FROM historial_estados WHERE pedido_id=? ORDER BY id",
            (pedido_id,))]
    finally:
        con.close()


def pesos(valor):
    return "$" + f"{int(valor):,}".replace(",", ".")


def mostrar(pedidos):
    if not pedidos:
        print("No hay solicitudes para esta consulta.")
    for p in pedidos:
        print(f"\n{p['consecutivo']} | {p['estado']}")
        print(f"Estudiante: {p['cliente']}")
        print(f"{p['codigo_producto']} | {p['nombre_producto']}")
        print(f"Horas: {p['cantidad']}")
        print("Valor hora:", pesos(p["precio_unitario"]))
        print("Total:", pesos(p["total"]))
        print(f"Fecha: {p['fecha']} | Hora: {p['hora']}")


# --------------------------------------------------------
# D.2. INICIO NUEVO SEMANA 04: DECIDIR SIN BORRAR LA SOLICITUD
# --------------------------------------------------------
def cambiar_estado(consecutivo, nuevo, actor, motivo="", chat_id=None):
    if nuevo not in ("APROBADO", "NO APROBADO", "CANCELADO"):
        raise ValueError("Decisión no permitida.")
    motivo = motivo.strip()
    if nuevo == "NO APROBADO" and not motivo:
        raise ValueError("Debe indicar el motivo de no aprobación.")
    if len(motivo) > 500:
        raise ValueError("El motivo admite hasta 500 caracteres.")
    if chat_id is not None and nuevo != "CANCELADO":
        raise ValueError("El estudiante solo puede cancelar.")
    con = conectar()
    try:
        # Bloquear escritura y comprobar el estado ACTUAL.
        con.execute("BEGIN IMMEDIATE")
        sql = "SELECT * FROM pedidos WHERE consecutivo=?"
        datos = [consecutivo]
        if chat_id is not None:
            sql += " AND chat_id=?"
            datos.append(chat_id)
        fila = con.execute(sql, datos).fetchone()
        if not fila:
            raise ValueError("No hay una solicitud tuya con ese consecutivo."
                             if chat_id is not None else "Solicitud no encontrada.")
        if fila["estado"] != "PENDIENTE":
            raise ValueError("La solicitud ya está " + fila["estado"] +
                             ". Solo se pueden cambiar solicitudes PENDIENTES.")
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        con.execute(
            "UPDATE pedidos SET estado=?, motivo=?, actualizado_en=?, "
            "actualizado_por=? WHERE id=? AND estado='PENDIENTE'",
            (nuevo, motivo, ahora, actor, fila["id"])
        )
        con.execute(
            "INSERT INTO historial_estados (pedido_id, estado_anterior, "
            "estado_nuevo, actor, motivo, fecha_hora) VALUES (?,?,?,?,?,?)",
            (fila["id"], "PENDIENTE", nuevo, actor, motivo, ahora)
        )
        pedido = dict(con.execute(
            "SELECT * FROM pedidos WHERE id=?", (fila["id"],)
        ).fetchone())
        con.commit()                     # Estado e historial juntos.
        return pedido
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
# FIN NUEVO SEMANA 04: DECIDIR SIN BORRAR LA SOLICITUD


# ========================================================
# E. ACTUALIZADO SEMANA 04: ASISTENTES DE IA Y MENSAJES
# ========================================================
# Groq es el proveedor principal; Gemini Interactions es el
# emergente. Las solicitudes, cotizaciones, cancelaciones y
# consultas NO dependen de una respuesta de IA.

# --------------------------------------------------------
# E.1. Base de conocimiento que reciben los asistentes
# --------------------------------------------------------
def construir_conocimiento():
    p = PLATAFORMA
    t = [f"=== QUÉ ES {p['nombre'].upper()} ===\n{p['que_es']}"]
    t.append(f"=== SER TUTOR ===\n{p['ser_tutor']}")
    t.append(
        f"=== PRECIOS ===\nPrecio del tutor por hora + comisión de Mi Tutor del "
        f"{COMISION} %. Total = horas × (precio_hora + {COMISION} %)."
    )
    t.append("=== TIPOS DE AYUDA ===\n" + "\n".join(
        f"- {n['nombre']}: {n['descripcion']}" for n in NECESIDADES))
    t.append("=== ÁREAS Y ASIGNATURAS ===\n" + "\n".join(
        f"{a['emoji']} {a['nombre']} ({a['codigo']}): {', '.join(a['asignaturas'])}"
        for a in AREAS))
    t.append("=== TEMAS DE EJEMPLO ===\n" + "\n".join(
        f"- {asig}: {', '.join(temas)}" for asig, temas in TEMAS.items()))
    tutores = "=== TUTORES (únicos que existen) ===\n"
    for tu in TUTORES:
        prod = PRODUCTOS[tu["codigo"].upper()]
        tutores += (
            f"\n[{tu['codigo']}] {tu['nombre']} — {NOMBRE_AREA[tu['area']]}\n"
            f"  Asignaturas: {', '.join(tu['asignaturas'])}\n"
            f"  Precio: {pesos(tu['precio'])} por hora; con comisión "
            f"{pesos(prod['precio'])} por hora\n"
            f"  Modalidad: {p['modalidades'][tu['modalidad']]}\n"
            f"  Horarios: {', '.join(f['etiqueta'] + ' (' + str(f['horas']) + ' h)' for f in FRANJAS[tu['codigo'].upper()])}\n"
            f"  Calificación: {tu['calificacion']} · {tu['tutorias']} tutorías · "
            f"{tu['universidad']}\n"
            f"  Experiencia: {tu['experiencia']}\n  Estilo: {tu['descripcion']}\n"
        )
    t.append(tutores)
    t.append("=== PREGUNTAS FRECUENTES ===\n" + "\n".join(
        f"P: {f['pregunta']}\nR: {f['respuesta']}" for f in PREGUNTAS_FRECUENTES))
    return "\n\n".join(t)


# CONOCIMIENTO se construye después de leer los horarios (bloque F.3c).

# ADAPTAR A SU MVP: personalidad y reglas del asistente.
INSTRUCCIONES = f"""
Eres "Tuti", el asistente de {NOMBRE_NEGOCIO} en Telegram. Hablas con estudiantes
universitarios colombianos que buscan tutorías de Matemáticas, Física o Química.

OBJETIVO: entender qué necesita el estudiante y conectarlo con el tutor adecuado.
Camino natural (no un formulario): área y asignatura → tema o tipo de ayuda →
modalidad y horario → recomendar 1 o 2 tutores con su código (TUT-01...), precio
y horario → indicar cómo registrar la solicitud. No repitas preguntas ya respondidas.

ESTILO: chat corto (2 a 5 líneas), cálido, tuteando, una sola pregunta por mensaje,
máximo 2 emojis. NO uses Markdown (nada de asteriscos, almohadillas ni tablas).
Responde siempre en español y en menos de 120 palabras.

REGLAS:
- Usa solo los tutores, precios y horarios de la BASE DE CONOCIMIENTO. Nunca inventes
  tutores, precios, horarios, descuentos ni medios de pago.
- Mi Tutor SÍ registra solicitudes desde este chat. El estudiante puede escribir
  natural, por ejemplo "quiero 2 horas con Laura", o usar los botones (elegir tutor
  y "Solicitar tutoría"). El programa le mostrará un resumen y le pedirá confirmar.
  Para conocer el valor sin registrar nada: "¿cuánto valen 3 horas?" o "Cotizar".
- Cada horario tiene una duración (por ejemplo "Lun 3–6pm" = 3 horas). Al solicitar,
  el programa pide el horario y luego las horas, que no pueden superar esa duración.
  Nunca ofrezcas más horas de las que caben en un horario.
- Cuando recomiendes un tutor, termina invitando a pedirlo con una frase natural,
  por ejemplo: "Si quieres, escríbeme cuántas horas necesitas con ella".
- El programa pide las horas, calcula el total y guarda la solicitud. Solo el
  programa confirma el registro y su consecutivo SOL-0000. Nunca afirmes que una
  solicitud ya se registró, se aprobó o cambió de estado.
- Seguimiento: botón "Mis solicitudes". Cancelar una pendiente: botón "Cancelar
  solicitud", escribir el consecutivo y confirmar con Sí o No.
- No procesas pagos. Puedes explicar un concepto en 2-3 líneas, pero no resuelvas
  tareas completas: invita a tomar la tutoría.
- Si piden una materia que no existe, dilo con amabilidad y ofrece las áreas.
""".strip()


def describir_contexto(sesion):
    if not sesion:
        return "El estudiante aún no ha elegido tutor."
    if sesion.get("codigo"):
        p = PRODUCTOS[sesion["codigo"]]
        return (f"Tutor activo: {p['codigo']} {p['tutor']} ({p['area']}). "
                f"Valor por hora con comisión: {pesos(p['precio'])}. "
                "Enfócate en este tutor hasta que pida otro.")
    if sesion.get("area"):
        area = AREAS_POR_CODIGO[sesion["area"]]
        return (f"El estudiante llegó buscando el área {area['nombre']}. "
                "Ayúdale a elegir un tutor de esa área.")
    return "El estudiante aún no ha elegido tutor."


# --------------------------------------------------------
# E.2. Groq (principal)
# --------------------------------------------------------
def consultar_groq(configuracion, mensajes):
    from urllib.request import Request, urlopen
    cuerpo = {"model": configuracion["modelo_groq"], "messages": mensajes,
              "temperature": 0.3, "max_completion_tokens": 1024}
    if configuracion["modelo_groq"].startswith("openai/gpt-oss"):
        cuerpo["reasoning_effort"] = "low"
    solicitud = Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(cuerpo).encode("utf8"),
        headers={"Authorization": "Bearer " + configuracion["clave_groq"],
                 "Content-Type": "application/json", "User-Agent": "MVP-Aula/1.0"},
    )
    # Un intento acotado; si falla, pasar al proveedor emergente.
    with urlopen(solicitud, timeout=8) as respuesta:
        datos = json.load(respuesta)
    texto = datos["choices"][0]["message"]["content"]
    if not texto or not texto.strip():
        raise ValueError("Groq no devolvió texto.")
    return texto.strip()


# --------------------------------------------------------
# E.3. Responder con memoria compartida entre proveedores
# --------------------------------------------------------
def responder_ia(configuracion, chat_id, texto):
    inicio = time.monotonic()
    nombre = configuracion.get("nombres", {}).get(chat_id, "Estudiante")
    instrucciones = (
        INSTRUCCIONES + "\n\n=== BASE DE CONOCIMIENTO ===\n" + CONOCIMIENTO +
        "\n\n=== CONTEXTO ===\n" + describir_contexto(sesiones.get(chat_id)) +
        f"\nNombre del estudiante: {nombre}"
    )
    historia = memoria_conversaciones.get(chat_id, [])
    mensajes = [{"role": "system", "content": instrucciones}]
    mensajes += historia[-12:]
    mensajes.append({"role": "user", "content": texto[:4000]})
    respuesta, proveedor = None, ""

    if configuracion.get("clave_groq"):
        try:
            respuesta = consultar_groq(configuracion, mensajes)
            proveedor = "Groq"
        except Exception as error:
            # No imprimir claves ni cuerpos de respuestas HTTP.
            print("⚠️ Groq no respondió:", type(error).__name__, getattr(error, "code", ""))
            print("🛟 Pasando a Gemini emergente")

    if respuesta is None and configuracion.get("gemini") is not None:
        cliente = configuracion["gemini"]
        for modelo in dict.fromkeys((configuracion["modelo_gemini"],
                                     configuracion["reserva_gemini"])):
            if not modelo:
                continue
            try:
                argumentos = {"model": modelo, "input": instrucciones +
                              "\nConversación reciente: " + str(mensajes[1:])}
                anterior = memoria_usuarios.get(chat_id)
                if anterior and anterior["modelo"] == modelo:
                    argumentos["previous_interaction_id"] = anterior["id"]
                resultado = cliente.interactions.create(**argumentos)
                if not resultado.output_text:
                    raise ValueError("Gemini no devolvió texto.")
                respuesta = resultado.output_text.strip()
                if resultado.id:
                    memoria_usuarios[chat_id] = {"id": resultado.id, "modelo": modelo}
                proveedor = "Gemini: " + modelo
                break
            except Exception as error:
                print("⚠️ Gemini:", modelo, type(error).__name__)

    if respuesta is None:
        return ("⚠️ Los asistentes de IA no respondieron en este momento. "
                "Puedes seguir con los botones: Cotizar, Solicitar tutoría "
                "o Mis solicitudes.")
    memoria_conversaciones[chat_id] = (
        historia + [{"role": "user", "content": texto[:4000]},
                    {"role": "assistant", "content": respuesta[:4000]}]
    )[-12:]
    print("✅ Respuesta IA:", proveedor, "|",
          round(time.monotonic() - inicio, 2), "segundos")
    return respuesta


# --------------------------------------------------------
# E.4. Utilidades de texto y mensajes con datos de SQLite
# --------------------------------------------------------
def normalizar(texto):
    texto = unicodedata.normalize("NFD", texto.lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    # Quitar emojis y signos del inicio de los botones.
    texto = re.sub(r"^[^a-z0-9/]+", "", texto)
    return texto.strip().rstrip(".!?")


def mensaje_pedido(p):
    # ADAPTAR A SU MVP: tono del detalle. Datos tomados de SQLite.
    texto = (
        f"📋 Solicitud {p['consecutivo']}\n"
        f"👩‍🏫 {p['nombre_producto']} ({p['codigo_producto']})\n"
        f"Horas: {p['cantidad']}\n"
        f"Valor por hora (incluye {COMISION} % de comisión): "
        f"{pesos(p['precio_unitario'])}\n"
        f"Total: {pesos(p['total'])}\n"
        f"📌 Estado: {p['estado']}"
    )
    if p.get("motivo"):
        texto += "\nMotivo: " + p["motivo"]
    if p.get("actualizado_en"):
        texto += "\nÚltima decisión: " + p["actualizado_en"]
    if p["estado"] == "PENDIENTE":
        texto += ("\n\nPuedes cancelar esta solicitud mientras el administrador "
                  "no la haya aprobado. Pulsa Cancelar solicitud y escribe "
                  + p["consecutivo"] + ".")
    texto += "\nPara ver todas tus solicitudes: Mis solicitudes"
    return texto


def bienvenida_general(nombre):
    # ADAPTAR A SU MVP: no consulta IA; responde al instante.
    return (
        f"👋 ¡Hola, {nombre}! Soy Tuti, el asistente de {NOMBRE_NEGOCIO}.\n\n"
        "Te conecto con estudiantes que ya dominan Matemáticas, Física o "
        "Química para que te expliquen.\n\n"
        "Elige un área con los botones de abajo, o cuéntame qué necesitas."
    )


def bienvenida_area(nombre, area):
    tutores = [p for p in PRODUCTOS.values() if p["area_clave"] == area["clave"]]
    return (
        f"👋 ¡Hola, {nombre}! Llegaste buscando ayuda en {area['emoji']} "
        f"{area['nombre']}.\n\nTenemos {len(tutores)} tutores en esta área, desde "
        f"{pesos(min(p['precio'] for p in tutores))} la hora (comisión incluida).\n\n"
        "Elige un tutor con los botones o cuéntame qué asignatura estás viendo."
    )


def bienvenida_tutor(nombre, p):
    return (
        f"👋 ¡Hola, {nombre}! Elegiste {p['nombre']} ({p['area']}).\n\n"
        f"📚 {p['descripcion']}\n"
        f"💰 {pesos(p['precio'])} por hora (incluye {COMISION} % de comisión).\n\n"
        "Pregúntame lo que quieras sobre la tutoría, o pulsa Cotizar o "
        "Solicitar tutoría."
    )


# ========================================================
# F. ATENDER SEGUIMIENTO, COTIZACIÓN, SOLICITUD Y CANCELACIÓN
# ========================================================
# --------------------------------------------------------
# F.1. ACTUALIZADO SEMANA 04: cancelar con botón y Sí/No
# --------------------------------------------------------
confirmaciones_cancelacion = {}
solicitudes_cancelacion = set()
PATRON_CONSECUTIVO = re.compile(PREFIJO + r"-[0-9]{4}")


def impedimento_cancelacion(pedido):
    if pedido["estado"] == "APROBADO":
        return ("⚠️ El administrador ya aprobó tu solicitud y no se puede "
                "cancelar. ¡Lo sentimos!")
    return ("⚠️ Esta solicitud está " + pedido["estado"] +
            ". Solo puedes cancelar solicitudes PENDIENTES.")


def gestionar_cancelacion(chat_id, comando, partes):
    # Botón → consecutivo → Sí/No. No se borra el registro de SQLite.
    texto = " ".join(partes).strip()
    limpio = normalizar(texto)
    iniciar = limpio in ("cancelar solicitud", "cancelar pedido") or \
        comando == "/cancelar_pedido"
    activo = chat_id in solicitudes_cancelacion or chat_id in confirmaciones_cancelacion
    codigo = None
    if iniciar:
        solicitudes_cancelacion.add(chat_id)
        confirmaciones_cancelacion.pop(chat_id, None)
        codigo = partes[1].upper() if comando == "/cancelar_pedido" and len(partes) == 2 else None
        if codigo is None:
            return (f"📋 Escribe el consecutivo de tu solicitud: {PREFIJO}- seguido "
                    f"de cuatro cifras, por ejemplo {PREFIJO}-0001.")
    elif activo and comando in ("/start", "/mis_pedidos", "/pedido"):
        solicitudes_cancelacion.discard(chat_id)
        confirmaciones_cancelacion.pop(chat_id, None)
        return None
    elif activo and (limpio in ("no", "no gracias") or comando == "/cancelar"):
        solicitudes_cancelacion.discard(chat_id)
        codigo = confirmaciones_cancelacion.pop(chat_id, None)
        if codigo:
            propios = consultar("pedido", codigo, chat_id)
            if propios and propios[0]["estado"] != "PENDIENTE":
                return "No cancelé tu solicitud. Su estado actual es " + propios[0]["estado"] + "."
        return "✅ No cancelé nada. Si tu solicitud estaba PENDIENTE, sigue activa."
    elif chat_id in confirmaciones_cancelacion:
        codigo = confirmaciones_cancelacion[chat_id]
        confirmar = limpio in ("si", "si por favor") or (
            comando == "/confirmar_cancelacion" and
            (len(partes) == 1 or (len(partes) == 2 and partes[1].upper() == codigo))
        )
        if not confirmar:
            return "¿Estás seguro de cancelar " + codigo + "? Pulsa Sí o No."
        try:
            # cambiar_estado verifica dueño y PENDIENTE en la transacción.
            cambiar_estado(codigo, "CANCELADO", "CLIENTE:" + str(chat_id),
                           "Cancelada por el estudiante", chat_id)
            return ("✅ Solicitud " + codigo + " cancelada correctamente.\n"
                    "Estado: CANCELADO. Ya no está activa; se conserva su historial.")
        except ValueError as error:
            propios = consultar("pedido", codigo, chat_id)
            if propios and propios[0]["estado"] != "PENDIENTE":
                return impedimento_cancelacion(propios[0])
            return "⚠️ " + str(error)
        finally:
            solicitudes_cancelacion.discard(chat_id)
            confirmaciones_cancelacion.pop(chat_id, None)
    elif chat_id in solicitudes_cancelacion:
        codigo = texto.upper()
    elif comando == "/confirmar_cancelacion":
        return "Pulsa Cancelar solicitud, escribe su consecutivo y confirma con Sí o No."
    else:
        return None

    if not PATRON_CONSECUTIVO.fullmatch(codigo):
        return (f"⚠️ Usa {PREFIJO}- y cuatro cifras, por ejemplo {PREFIJO}-0001. "
                "Escribe solo ese consecutivo.")
    propios = consultar("pedido", codigo, chat_id)
    if not propios:
        return ("⚠️ No encontré una solicitud tuya con ese consecutivo. "
                "Revisa Mis solicitudes y vuelve a escribirlo.")
    pedido = propios[0]
    if pedido["estado"] != "PENDIENTE":
        solicitudes_cancelacion.discard(chat_id)
        confirmaciones_cancelacion.pop(chat_id, None)
        return impedimento_cancelacion(pedido)
    solicitudes_cancelacion.discard(chat_id)
    confirmaciones_cancelacion[chat_id] = codigo
    return (f"📋 {codigo} | {pedido['nombre_producto']} | {pesos(pedido['total'])}\n"
            "Estado: PENDIENTE.\n\n¿Estás seguro de cancelar esta solicitud? "
            "Pulsa Sí o No.")


# --------------------------------------------------------
# F.2. NUEVO SEMANA 04: teclado con solo rutas implementadas
# --------------------------------------------------------
def botones_cliente(chat_id):
    if chat_id in confirmaciones_cancelacion:
        return [["Sí", "No"]]
    if chat_id in solicitudes_cancelacion:
        return [["No", "Mis solicitudes"]]
    sesion = sesiones.get(chat_id) or {}
    seguimiento = ["Mis solicitudes", "Cancelar solicitud"]
    if sesion.get("etapa") == "confirmar":
        return [["Sí, registrar", "No"], ["Cambiar horas", "Cambiar horario"]]
    if sesion.get("etapa") == "franja":
        etiquetas = [f["etiqueta"] for f in FRANJAS[sesion["codigo"]]]
        return [etiquetas[i:i + 2] for i in range(0, len(etiquetas), 2)] + [["/cancelar"]]
    if sesion.get("etapa") in ("cantidad", "cantidad_cotizacion"):
        if sesion.get("franja") is not None:
            limite = FRANJAS[sesion["codigo"]][sesion["franja"]]["horas"]
        else:
            limite = max_horas(sesion["codigo"])
        return [[str(n) for n in range(1, min(limite, 4) + 1)], ["/cancelar"]]
    if sesion.get("codigo"):
        return [["Cotizar", "Solicitar tutoría"], seguimiento, ["Ver otros tutores"]]
    if sesion.get("area"):
        area = AREAS_POR_CODIGO[sesion["area"]]
        tutores = [f"{p['codigo']} — {p['tutor']}" for p in PRODUCTOS.values()
                   if p["area_clave"] == area["clave"]]
        filas = [tutores[i:i + 2] for i in range(0, len(tutores), 2)]
        return filas + [seguimiento, ["Cambiar de área"]]
    return [[f"{a['emoji']} {a['nombre']}" for a in AREAS], seguimiento]


# --------------------------------------------------------
# F.3. NUEVO SEMANA 04: cotizar sin registrar
# --------------------------------------------------------
def texto_cotizacion(codigo, cantidad):
    p = PRODUCTOS[codigo]
    if cantidad > max_horas(codigo):
        return (f"⚠️ El horario más largo de {p['tutor']} es de {max_horas(codigo)} "
                f"{UNIDAD}, así que puedes cotizar de 1 a {max_horas(codigo)}. "
                f"Horarios: {', '.join(f['etiqueta'] for f in FRANJAS[codigo])}.")
    subtotal = cantidad * p["precio_tutor"]
    total = cantidad * p["precio"]
    return (
        f"💰 Cotización — {p['nombre']}\n"
        f"Horas: {cantidad}\n"
        f"Valor del tutor: {pesos(subtotal)}\n"
        f"Comisión {NOMBRE_NEGOCIO} ({COMISION} %): {pesos(total - subtotal)}\n"
        f"Total: {pesos(total)}\n\n"
        "Esta cotización todavía no registra ninguna solicitud. "
        "Si quieres tomarla, pulsa Solicitar tutoría."
    )


# --------------------------------------------------------
# F.3b. NUEVO C3S2: ENTENDER LENGUAJE NATURAL (sin IA)
# --------------------------------------------------------
# Python reconoce tutor, materia, horas e intención en frases como
# «quiero 2 horas con Laura». Nunca registra sin una confirmación
# explícita (Sí / No), así una pregunta no se convierte en solicitud.
NUMEROS = {"un": 1, "una": 1, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4,
           "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10}
SALUDOS = {"hola", "holi", "ola", "buenas", "buen dia", "buenos dias",
           "buenas tardes", "buenas noches", "hey", "hola tuti", "hola buenas"}
GRACIAS = {"gracias", "muchas gracias", "ok gracias", "listo gracias",
           "mil gracias", "gracias tuti", "perfecto gracias"}
CONFIRMACIONES = {"dale", "confirmo", "confirmar", "ok", "okay", "listo", "de una",
                  "claro", "registrala", "registrar", "hazlo", "por favor"}
NEGACIONES = {"no", "no gracias", "mejor no", "todavia no", "aun no", "no por ahora",
              "ahora no", "despues"}

# Nombres de pila de los tutores (los apellidos pueden ser palabras comunes,
# como «peña», por eso solo cuentan con el nombre completo).
NOMBRES_TUTORES = {}
for _t in TUTORES:
    _partes = normalizar(_t["nombre"]).split()
    NOMBRES_TUTORES[_t["codigo"].upper()] = (_partes[0], " ".join(_partes))

# Palabras que delatan el área cuando no se nombra una asignatura exacta.
PISTAS_AREA = {
    "TUT-MAT": ("matematica", "calculo", "algebra", "estadistica", "probabilidad",
                "geometria", "derivada", "integral", "limite", "matriz", "matrices",
                "ecuacion", "funcion", "vector"),
    "TUT-FIS": ("fisica", "mecanica", "circuito", "electric", "magnet", "newton",
                "cinematica", "dinamica", "fuerza", "energia", "onda", "optica",
                "termodinamica"),
    "TUT-QUI": ("quimica", "estequiometr", "organica", "inorganica", "molecula",
                "reaccion", "enlace", "mol ", "atomo", "tabla periodica"),
}
ASIGNATURAS = sorted(
    ((normalizar(asig), asig, a["codigo"]) for a in AREAS for asig in a["asignaturas"]),
    key=lambda x: -len(x[0]))  # Las más largas primero: «termodinamica quimica».


def extraer_horas(limpio):
    """Horas mencionadas (int), None si no hay; ValueError si son inválidas."""
    if re.search(r"\d\s*[.,]\s*\d", limpio):
        raise ValueError(f"Las {UNIDAD} deben ser un número entero de 1 a {CANTIDAD_MAXIMA}.")
    numero = (re.search(r"(?<!\d)(\d{1,3})\s*(?:horas?|hrs?|h)\b", limpio)
              or re.fullmatch(r"(\d{1,3})", limpio))
    if numero:
        valor = int(numero[1])
    else:
        palabras = "|".join(NUMEROS)
        escrito = (re.search(r"\b(" + palabras + r")\s+horas?\b", limpio)
                   or re.fullmatch(r"(" + palabras + r")", limpio))
        if not escrito:
            return None
        valor = NUMEROS[escrito[1]]
    if not 1 <= valor <= CANTIDAD_MAXIMA:
        raise ValueError(f"Las {UNIDAD} deben estar entre 1 y {CANTIDAD_MAXIMA}.")
    return valor


# --------------------------------------------------------
# F.3c. NUEVO C3S2: HORARIOS (FRANJAS) DE CADA TUTOR
# --------------------------------------------------------
# «Lun 3–6pm» dura 3 horas: no se pueden pedir más horas que las
# que caben en el horario elegido.
DIAS = {"lun": "lunes", "mar": "martes", "mie": "miercoles", "jue": "jueves",
        "vie": "viernes", "sab": "sabado", "dom": "domingo"}


def _hora24(numero, sufijo):
    h = int(numero)
    if sufijo == "m":                    # «12m» = mediodía
        return 12
    if sufijo == "pm" and h < 12:
        return h + 12
    if sufijo == "am" and h == 12:
        return 0
    return h


def duracion_franja(etiqueta):
    m = re.match(r"^(\S+)\s+(\d{1,2})(am|pm|m)?\s*[–-]\s*(\d{1,2})(am|pm|m)$",
                 etiqueta.strip(), re.I)
    if not m:
        return None
    _, h1, s1, h2, s2 = m.groups()
    fin = _hora24(h2, s2.lower())
    inicio = _hora24(h1, (s1 or ("am" if s2.lower() == "m" else s2)).lower())
    if not s1 and inicio >= fin:         # «11–1pm» empieza en la mañana
        inicio = _hora24(h1, "am")
    return fin - inicio if fin > inicio else None


FRANJAS = {}
for _t in TUTORES:
    FRANJAS[_t["codigo"].upper()] = [
        {"etiqueta": e, "horas": min(duracion_franja(e) or CANTIDAD_MAXIMA, CANTIDAD_MAXIMA)}
        for e in _t["disponibilidad"]]


# Base de conocimiento de la IA, ya con la duración de cada horario.
CONOCIMIENTO = construir_conocimiento()


def max_horas(codigo):
    return max(f["horas"] for f in FRANJAS[codigo])


def detectar_franja(codigo, limpio, abreviado=False):
    """Índice del horario mencionado («el sábado», «Lun 3–6pm») o None."""
    franjas = FRANJAS[codigo]
    for i, f in enumerate(franjas):
        if limpio.startswith(normalizar(f["etiqueta"])):
            return i
    palabras = list(DIAS.values()) + (list(DIAS) if abreviado else [])
    dichos = {d[:3] for d in re.findall(r"\b(" + "|".join(palabras) + r")\b", limpio)}
    candidatos = [i for i, f in enumerate(franjas) if normalizar(f["etiqueta"])[:3] in dichos]
    return candidatos[0] if len(candidatos) == 1 else None


def limpiar_solicitud(sesion):
    for clave in ("horas", "franja"):
        sesion.pop(clave, None)


def avanzar_solicitud(sesion):
    """Pide lo que falte (horario y horas) y deja la solicitud lista para confirmar."""
    codigo = sesion["codigo"]
    p = PRODUCTOS[codigo]
    franjas = FRANJAS[codigo]
    if sesion.get("franja") is None and len(franjas) == 1:
        sesion["franja"] = 0
    if sesion.get("franja") is None:
        sesion["etapa"] = "franja"
        lineas = [f"🗓️ ¿En qué horario quieres la tutoría con {p['tutor']}?"]
        lineas += [f"• {f['etiqueta']} (hasta {f['horas']} h)" for f in franjas]
        lineas.append("Toca un horario o escribe el día.")
        return "\n".join(lineas)
    f = franjas[sesion["franja"]]
    horas = sesion.get("horas")
    if horas and horas > f["horas"]:
        sesion.pop("horas")
        sesion["etapa"] = "cantidad"
        return (f"⚠️ En el horario {f['etiqueta']} {p['tutor']} solo tiene {f['horas']} "
                f"{UNIDAD} disponibles. ¿Cuántas quieres? (1 a {f['horas']})")
    if not horas:
        sesion["etapa"] = "cantidad"
        return (f"¿Cuántas {UNIDAD} quieres en el horario {f['etiqueta']}? "
                f"Elige un botón o escribe un número de 1 a {f['horas']}.")
    sesion["etapa"] = "confirmar"
    return resumen_confirmacion(codigo, horas, f["etiqueta"])


def detectar_tutor(limpio):
    codigo = re.search(r"\btut-?([0-9]{2})\b", limpio)
    if codigo and f"TUT-{codigo[1]}" in PRODUCTOS:
        return f"TUT-{codigo[1]}"
    palabras = set(re.findall(r"[a-z]+", limpio))
    encontrados = [c for c, (pila, completo) in NOMBRES_TUTORES.items()
                   if completo in limpio or pila in palabras]
    return encontrados[0] if len(encontrados) == 1 else None


def detectar_area(limpio):
    for normal, asignatura, area in ASIGNATURAS:
        if re.search(r"\b" + re.escape(normal) + r"\b", limpio):
            return area, asignatura
    for area, pistas in PISTAS_AREA.items():
        if any(p in limpio + " " for p in pistas):
            return area, None
    return None


def pregunta_precio(limpio):
    return any(p in limpio for p in ("cotiz", "cuanto", "cuesta", "precio", "valor",
                                     "costo", "tarifa", "cobra"))


def quiere_solicitar(limpio):
    if limpio in INTENCIONES:
        return True
    if pregunta_precio(limpio) or limpio.startswith(("como ", "que ", "cual", "cuando")):
        return False
    verbos = r"(quiero|quisiera|necesito|me gustaria|deseo|voy a|me ayudas a|puedo|podria)"
    objetos = (r"(solicitar|agendar|reservar|separar|apartar|tomar|pedir|contratar|"
               r"programar|tutoria|tutorias|clase|clases|asesoria|horas?)")
    return bool(re.search(r"\b" + verbos + r"\b.*\b" + objetos + r"\b", limpio)
                or re.search(r"\b(agendame|reservame|apartame|separame|anotame|inscribeme|"
                             r"programame|solicitame)\b", limpio)
                or re.match(r"^(agendar|agenda|reservar|reserva|solicitar|solicito)\b", limpio))


def recomendar(codigo_area, asignatura):
    area = AREAS_POR_CODIGO[codigo_area]
    tutores = [t for t in TUTORES if t["area"] == area["clave"]]
    exactos = [t for t in tutores if asignatura in t["asignaturas"]] if asignatura else []
    lista = exactos or tutores
    tema = asignatura or area["nombre"]
    lineas = [f"{area['emoji']} Para {tema} te puedo conectar con:"]
    for t in lista:
        p = PRODUCTOS[t["codigo"].upper()]
        lineas.append(f"\n{p['codigo']} — {t['nombre']} ({t['calificacion']} ⭐)\n"
                      f"{pesos(p['precio'])}/h · {PLATAFORMA['modalidades'][t['modalidad']]}\n"
                      f"Horarios: {', '.join(t['disponibilidad'])}")
    lineas.append("\n¿Con quién quieres la tutoría? Toca su botón o escribe su nombre.")
    return "\n".join(lineas)


def es_afirmativo(limpio):
    # «sí», «sii», «claro que sí», «dale», «confirmo», «me interesa»… en un mensaje
    # corto y sin «no». Una pregunta larga nunca cuenta como confirmación.
    if re.search(r"\bno\b", limpio) or len(limpio.split()) > 5:
        return False
    return bool(limpio in CONFIRMACIONES or re.match(
        r"^(si+|sip|claro|dale|ok|okay|listo|de una|hagale|hagamosle|perfecto|correcto|"
        r"confirmo|confirmar|confirmado|por supuesto|me interesa|registrala|registrar|"
        r"hazlo|vale|me sirve|esta bien|de acuerdo)\b", limpio))


def resumen_confirmacion(codigo, horas, franja):
    p = PRODUCTOS[codigo]
    return (f"📝 Revisa tu solicitud:\n"
            f"👩‍🏫 {p['nombre']} ({codigo})\n"
            f"🗓️ Horario: {franja}\n"
            f"Horas: {horas}\n"
            f"Total: {pesos(horas * p['precio'])} (incluye {COMISION} % de comisión)\n\n"
            "¿La registro? Pulsa «Sí, registrar» o «No».")


def orientar_compra(sesion, texto):
    limpio = normalizar(texto).lstrip("¿¡")
    if limpio in ("si", "si por favor", "si quiero", "claro", "dale"):
        return avanzar_solicitud(sesion)
    if limpio in NEGACIONES:
        return ("De acuerdo, no registraré nada. Puedes seguir preguntando; "
                "cuando quieras, pulsa Solicitar tutoría.")
    if not pregunta_precio(limpio):
        return None                  # Otras preguntas van a la IA.
    try:
        horas = extraer_horas(limpio)
    except ValueError as error:
        return str(error)
    if horas:
        return texto_cotizacion(sesion["codigo"], horas)
    p = PRODUCTOS[sesion["codigo"]]
    return (f"💰 {p['nombre']}: {pesos(p['precio'])} por hora con comisión.\n"
            "Dime cuántas horas quieres (por ejemplo «2 horas») y te doy el total.")


# --------------------------------------------------------
# F.4. Botones con texto → comandos implementados
# --------------------------------------------------------
TEXTO_A_COMANDO = {
    "mis solicitudes": "/mis_pedidos",
    "cotizar": "/cotizar",
    "solicitar tutoria": "/comprar",
    "ver otros tutores": "/otros_tutores",
    "cambiar de area": "/areas",
}
ALIAS = {
    "/solicitar": "/comprar", "/mis_solicitudes": "/mis_pedidos",
    "/solicitud": "/pedido", "/cancelar_solicitud": "/cancelar_pedido",
    "/reiniciar": "/start",
}
INTENCIONES = {"quiero comprar", "quiero pedir", "comprar", "solicitar",
               "quiero solicitar", "quiero una tutoria", "quiero la tutoria",
               "agendar", "quiero agendar"}


def seleccionar_tutor(chat_id, codigo, nombre, reiniciar=True):
    # reiniciar=False conserva la conversación (el tutor se nombró en el chat).
    if reiniciar:
        memoria_usuarios.pop(chat_id, None)
        memoria_conversaciones.pop(chat_id, None)
    p = PRODUCTOS[codigo]
    area = next(a["codigo"] for a in AREAS if a["clave"] == p["area_clave"])
    sesiones[chat_id] = {"codigo": codigo, "area": area, "etapa": "consulta"}
    return bienvenida_tutor(nombre, p)


def seleccionar_area(chat_id, codigo_area, nombre):
    memoria_usuarios.pop(chat_id, None)
    memoria_conversaciones.pop(chat_id, None)
    sesiones[chat_id] = {"codigo": None, "area": codigo_area, "etapa": "consulta"}
    return bienvenida_area(nombre, AREAS_POR_CODIGO[codigo_area])


# --------------------------------------------------------
# F.5. ELEGIR LA ACCIÓN DEL ESTUDIANTE
# --------------------------------------------------------
def procesar(mensaje, update_id, configuracion=None):
    configuracion = configuracion or {}
    chat_id = mensaje["chat"]["id"]
    if mensaje["chat"].get("type", "private") != "private":
        return f"Abre el chat privado con @{USUARIO_BOT}."
    nombre = mensaje.get("from", {}).get("first_name") or "estudiante"
    configuracion.setdefault("nombres", {})[chat_id] = nombre

    texto = mensaje.get("text", "").strip()
    partes = texto.split()
    comando = partes[0].split("@")[0].lower() if partes and partes[0].startswith("/") else ""
    comando = ALIAS.get(comando, comando)
    limpio = normalizar(texto)
    if not comando and limpio in TEXTO_A_COMANDO:
        comando = TEXTO_A_COMANDO[limpio]
        partes = [comando]

    # El seguimiento se permite incluso después de reiniciar.
    seguimiento = comando == "/mis_pedidos" or (
        comando == "/start" and [p.lower() for p in partes[1:]] == ["mis_pedidos"])

    # INICIO NUEVO SEMANA 04: cancelación antes de otras rutas.
    respuesta_cancelacion = gestionar_cancelacion(
        chat_id, comando, [comando] + partes[1:] if comando else partes)
    if respuesta_cancelacion is not None:
        return respuesta_cancelacion
    # FIN NUEVO SEMANA 04

    if seguimiento:
        propios = consultar(chat_id=chat_id)
        if not propios:
            return ("📋 Aún no tienes solicitudes. Elige un tutor desde la página "
                    "o con los botones y pulsa Solicitar tutoría para registrar "
                    "la primera.")
        lineas = ["📋 Tus últimas solicitudes:"]
        for p in propios[-10:]:
            lineas.append(f"{p['consecutivo']} | {p['estado']} | {pesos(p['total'])}")
        lineas.append("\nDetalle: /pedido " + propios[-1]["consecutivo"])
        return "\n".join(lineas)

    if comando == "/pedido":
        if len(partes) != 2:
            return f"Escribe /pedido seguido del consecutivo, por ejemplo /pedido {PREFIJO}-0001."
        propios = consultar("pedido", partes[1].upper(), chat_id)
        if not propios:
            return "No hay una solicitud tuya con ese consecutivo."
        return mensaje_pedido(propios[0])

    # Un reintento de Telegram devuelve la misma solicitud guardada.
    con = conectar()
    try:
        previo = con.execute("SELECT * FROM pedidos WHERE telegram_update_id = ?",
                             (update_id,)).fetchone()
    finally:
        con.close()
    if previo:
        return mensaje_pedido(dict(previo))

    # Deep links de la página: /start TUT-01, /start TUT-MAT, /start inicio.
    if comando == "/start":
        print("🔎 Deep link recibido:", texto)
        referencia = partes[1].upper() if len(partes) == 2 else ""
        if referencia in PRODUCTOS:
            return seleccionar_tutor(chat_id, referencia, nombre)
        if referencia in AREAS_POR_CODIGO:
            return seleccionar_area(chat_id, referencia, nombre)
        sesiones.pop(chat_id, None)
        memoria_usuarios.pop(chat_id, None)
        memoria_conversaciones.pop(chat_id, None)
        if referencia not in ("", "INICIO", "TUTOR"):
            print("⚠️ Referencia desconocida:", referencia)
        return bienvenida_general(nombre)

    if comando == "/ayuda":
        return ("Escríbeme normal, como en un chat 🙂\n\n"
                "Cotizar: calcula el valor sin registrar nada.\n"
                "Solicitar tutoría: registra tu solicitud con consecutivo.\n"
                "Mis solicitudes: estado de tus solicitudes.\n"
                "Cancelar solicitud: anula una solicitud PENDIENTE.\n"
                "/tutores: lista completa · /start: empezar de nuevo")

    if comando == "/tutores":
        lineas = ["👩‍🏫 Tutores de Mi Tutor (valor por hora con comisión):"]
        for a in AREAS:
            lineas.append(f"\n{a['emoji']} {a['nombre']}")
            for p in PRODUCTOS.values():
                if p["area_clave"] == a["clave"]:
                    lineas.append(f"{p['codigo']} — {p['tutor']}: {pesos(p['precio'])}")
        return "\n".join(lineas)

    # Botones del teclado: área o tutor.
    for a in AREAS:
        if limpio == normalizar(a["nombre"]):
            return seleccionar_area(chat_id, a["codigo"], nombre)
    elegido = re.match(r"^(TUT-[0-9]{2})\b", texto.upper())
    if elegido and elegido[1] in PRODUCTOS:
        return seleccionar_tutor(chat_id, elegido[1], nombre)

    sesion = sesiones.get(chat_id)

    if comando == "/areas":
        sesiones.pop(chat_id, None)
        return "Elige un área con los botones de abajo."
    if comando == "/otros_tutores":
        if sesion and sesion.get("area"):
            sesion["codigo"] = None
            sesion["etapa"] = "consulta"
            return "Estos son los tutores del área. Elige uno con los botones."
        sesiones.pop(chat_id, None)
        return "Elige un área para ver sus tutores."

    if comando == "/cancelar":
        if sesion:
            sesion["etapa"] = "consulta"
            limpiar_solicitud(sesion)
        return "Listo, no registré nada. Puedes seguir consultando o elegir otra opción."

    # INICIO NUEVO C3S2: confirmar la solicitud (horario + horas).
    if sesion and sesion.get("etapa") == "confirmar":
        if es_afirmativo(limpio):
            franja = FRANJAS[sesion["codigo"]][sesion["franja"]]["etiqueta"]
            pedido = guardar_pedido(nombre, chat_id, sesion["codigo"], sesion["horas"],
                                    update_id, franja)
            limpiar_solicitud(sesion)
            sesion["etapa"] = "consulta"     # Solo tras confirmar en SQLite.
            sesion["recien_registrada"] = pedido["consecutivo"]
            mostrar([pedido])
            return "✅ ¡Solicitud registrada!\n\n" + mensaje_pedido(pedido)
        if limpio in NEGACIONES:
            sesion["etapa"] = "consulta"
            limpiar_solicitud(sesion)
            return ("De acuerdo, no registré nada. Si quieres, cambia el horario o las "
                    "horas, o pregúntame lo que necesites.")
        if limpio == "cambiar horas":
            sesion.pop("horas", None)
            return avanzar_solicitud(sesion)
        if limpio == "cambiar horario":
            limpiar_solicitud(sesion)
            return avanzar_solicitud(sesion)
        try:
            nuevas = extraer_horas(limpio)
        except ValueError as error:
            return str(error)
        otra_franja = detectar_franja(sesion["codigo"], limpio)
        if nuevas or otra_franja is not None:
            if otra_franja is not None:
                sesion["franja"] = otra_franja
            if nuevas:
                sesion["horas"] = nuevas
            return avanzar_solicitud(sesion)
        # Cambió de tema: se abandona la confirmación sin registrar nada.
        sesion["etapa"] = "consulta"
        limpiar_solicitud(sesion)

    # Elegir el horario (franja) del tutor.
    if sesion and sesion.get("etapa") == "franja":
        indice = detectar_franja(sesion["codigo"], limpio, abreviado=True)
        try:
            horas_dichas = None if indice is not None and limpio.startswith(
                normalizar(FRANJAS[sesion["codigo"]][indice]["etiqueta"])) else extraer_horas(limpio)
        except ValueError as error:
            return str(error)
        if horas_dichas:
            sesion["horas"] = horas_dichas
        if indice is not None:
            sesion["franja"] = indice
            return avanzar_solicitud(sesion)
        if horas_dichas:
            return avanzar_solicitud(sesion)     # Vuelve a mostrar los horarios.
        if not (comando or detectar_tutor(limpio) or detectar_area(limpio)
                or len(limpio.split()) >= 4):
            return ("Elige uno de los horarios con los botones o escribe el día, "
                    "por ejemplo «el sábado». Para salir, pulsa /cancelar.")
        sesion["etapa"] = "consulta"             # Cambió de tema: se atiende.
        limpiar_solicitud(sesion)
    # FIN NUEVO C3S2

    sin_tutor = not sesion or not sesion.get("codigo")
    if comando in ("/comprar", "/cotizar") and sin_tutor:
        return ("Primero elige un tutor: cuéntame qué materia necesitas, toca un área "
                "o abre el perfil del tutor en la página de Mi Tutor.")

    # Cotizar reutiliza el cálculo del catálogo y nunca guarda.
    if comando == "/cotizar":
        sesion["etapa"] = "cantidad_cotizacion"
        return (f"💰 ¿Cuántas {UNIDAD} quieres cotizar? Elige un botón o escribe un "
                f"número de 1 a {max_horas(sesion['codigo'])}. Esta consulta no registra nada.")

    # Botón Solicitar tutoría: pide horario y horas, y confirma.
    if comando == "/comprar" or (limpio in INTENCIONES and not sin_tutor):
        limpiar_solicitud(sesion)
        return avanzar_solicitud(sesion)

    if sesion and sesion.get("etapa") in ("cantidad", "cantidad_cotizacion"):
        try:
            cantidad = extraer_horas(limpio)
        except ValueError as error:
            return str(error) + " Para salir, pulsa /cancelar."
        cambia_tema = detectar_tutor(limpio) or detectar_area(limpio)
        if cantidad is None and len(limpio.split()) < 3 and not cambia_tema:
            return ("Escribe un número entero de horas, por ejemplo «2». "
                    "Para salir, pulsa /cancelar.")
        if cantidad is not None:
            if sesion["etapa"] == "cantidad_cotizacion":
                sesion["etapa"] = "consulta"
                return texto_cotizacion(sesion["codigo"], cantidad)
            sesion["horas"] = cantidad
            otra_franja = detectar_franja(sesion["codigo"], limpio)
            if otra_franja is not None:
                sesion["franja"] = otra_franja
            return avanzar_solicitud(sesion)     # Valida el límite y pide confirmar.
        sesion["etapa"] = "consulta"             # Escribió una pregunta: se atiende.
        limpiar_solicitud(sesion)

    if not texto:
        return "Escríbeme tu pregunta o usa los botones de abajo."

    # INICIO NUEVO C3S2: conversación natural sin depender de botones.
    if not comando:
        if limpio in SALUDOS:
            if sesion and sesion.get("codigo"):
                p = PRODUCTOS[sesion["codigo"]]
                return (f"¡Hola, {nombre}! Seguimos con {p['nombre']}. "
                        "¿Quieres cotizar, solicitar o tienes alguna pregunta?")
            return bienvenida_general(nombre)
        if limpio in GRACIAS:
            return ("¡Con gusto! 🙌 Si necesitas algo más, aquí estoy. Para revisar "
                    "tus solicitudes, toca Mis solicitudes.")

        # Un «sí» justo después de registrar no inicia otra solicitud.
        recien = sesion.pop("recien_registrada", None) if sesion else None
        if recien and es_afirmativo(limpio):
            return (f"✅ Tu solicitud {recien} ya quedó registrada. Puedes verla en "
                    "Mis solicitudes. ¿Necesitas algo más?")
        if limpio in ("cambiar horas", "cambiar horario") and sesion and sesion.get("codigo"):
            limpiar_solicitud(sesion)
            return avanzar_solicitud(sesion)

        quiere = quiere_solicitar(limpio)
        precio = pregunta_precio(limpio)
        tutor = detectar_tutor(limpio)
        try:
            horas = extraer_horas(limpio)        # «2», «2 horas», «dos horas»
        except ValueError as error:
            return str(error)
        # Horas que el estudiante dijo antes de elegir tutor.
        deseadas = sesion.get("horas_deseadas") if sesion else None

        if tutor and (sin_tutor or tutor != sesion["codigo"]):
            seleccionar_tutor(chat_id, tutor, nombre, reiniciar=False)
            sesion, sin_tutor = sesiones[chat_id], False
            horas = horas or deseadas
            if (horas or quiere) and not precio:
                limpiar_solicitud(sesion)
                sesion["horas"] = horas
                sesion["franja"] = detectar_franja(tutor, limpio)
                return avanzar_solicitud(sesion)
            if len(limpio.split()) <= 3 and not (quiere or precio):
                return bienvenida_tutor(nombre, PRODUCTOS[tutor])

        if sin_tutor:
            if horas and not precio:
                # Aún no hay tutor: se recuerdan las horas para no volver a pedirlas.
                sesion = sesiones.setdefault(chat_id, {"codigo": None, "area": None,
                                                       "etapa": "consulta"})
                sesion["horas_deseadas"] = horas
                quiere = True
            area = detectar_area(limpio)
            if area:
                codigo_area, asignatura = area
                sesion = sesiones[chat_id] = {"codigo": None, "area": codigo_area,
                                              "etapa": "consulta"}
                if horas or deseadas:
                    sesion["horas_deseadas"] = horas or deseadas
                if quiere or precio or asignatura or len(limpio.split()) <= 4:
                    return recomendar(codigo_area, asignatura)
            elif quiere:
                if sesion and sesion.get("area"):
                    return recomendar(sesion["area"], None)
                return ("¡Claro! ¿De qué materia necesitas la tutoría? Por ejemplo: "
                        "Cálculo I, Física II o Química General.")
        else:
            # Pide otra materia que su tutor actual no enseña: se recomienda de nuevo.
            area = None if tutor else detectar_area(limpio)
            actual = PRODUCTOS[sesion["codigo"]]
            if area and (AREAS_POR_CODIGO[area[0]]["clave"] != actual["area_clave"] or (
                    area[1] and area[1] not in next(
                        t["asignaturas"] for t in TUTORES if t["codigo"].upper() == actual["codigo"]))):
                sesiones[chat_id] = {"codigo": None, "area": area[0], "etapa": "consulta"}
                return recomendar(*area)
            # Ya hay tutor: unas horas escritas («2 horas», «2») o un «sí» bastan
            # para preparar la solicitud. Nada se guarda sin la confirmación.
            horas = horas or (deseadas if quiere or es_afirmativo(limpio) else None)
            franja = detectar_franja(sesion["codigo"], limpio)
            solo_dia = (franja is not None and "?" not in texto
                        and len(limpio.split()) <= 4)       # «el sábado», no una pregunta
            if (horas or quiere or es_afirmativo(limpio) or solo_dia) and not precio:
                sesion.pop("horas_deseadas", None)
                limpiar_solicitud(sesion)
                sesion["horas"] = horas
                sesion["franja"] = franja
                return avanzar_solicitud(sesion)
            orientacion = orientar_compra(sesion, texto)
            if orientacion:
                return orientacion
    # FIN NUEVO C3S2

    return responder_ia(configuracion, chat_id, texto)


# ========================================================
# G. CONEXIÓN CON TELEGRAM
# ========================================================
# Las librerías externas se cargan solo al iniciar el bot:
# consultas.py e iniciar.py importan este archivo sin Internet.
def configurar_ia():
    from google import genai
    clave_groq = (os.getenv("GROQ_API_KEY") or "").strip()
    clave_gemini = (os.getenv("GEMINI_API_KEY") or "").strip()
    gemini = None
    if clave_gemini:
        try:
            gemini = genai.Client(api_key=clave_gemini,
                                  http_options={"timeout": 8000})
        except Exception:
            gemini = genai.Client(api_key=clave_gemini)
    return {
        "clave_groq": clave_groq,
        "modelo_groq": (os.getenv("GROQ_MODEL") or "openai/gpt-oss-20b").strip(),
        "gemini": gemini,
        "modelo_gemini": (os.getenv("GEMINI_MODEL") or os.getenv("GEMINI_MODELO")
                          or "gemini-3.5-flash-lite").strip(),
        "reserva_gemini": (os.getenv("GEMINI_MODELO_RESPALDO")
                           or "gemini-3.6-flash").strip(),
        "nombres": {},
    }


def ejecutar_bot():
    try:
        import asyncio
        from dotenv import load_dotenv
        from telegram import ReplyKeyboardMarkup
        from telegram.constants import ChatAction
        from telegram.error import Conflict, InvalidToken, NetworkError
        from telegram.ext import Application, MessageHandler, filters
    except ImportError as error:
        print("❌ Falta una librería de comunicación:", error.name)
        print("📌 Cierre y vuelva a abrir: las librerías se instalan solas.")
        return
    print("✅ python-dotenv, python-telegram-bot y google-genai: disponibles")

    load_dotenv(BASE / ".env")
    token = (os.getenv("TELEGRAM_TOKEN") or "").strip()
    if not token or not (os.getenv("GEMINI_API_KEY") or os.getenv("GROQ_API_KEY")):
        print("❌ Revise .env: TELEGRAM_TOKEN y al menos GROQ_API_KEY o GEMINI_API_KEY.")
        return
    configuracion = configurar_ia()

    async def mantener_escribiendo(chat, detener):
        while not detener.is_set():
            try:
                await chat.send_action(ChatAction.TYPING)
            except Exception:
                pass
            try:
                await asyncio.wait_for(detener.wait(), timeout=4)
            except asyncio.TimeoutError:
                pass

    # Una misma entrada atiende comandos, botones y conversación.
    async def atender(update, context):
        mensaje = update.effective_message
        if mensaje is None or mensaje.text is None:
            return
        print(f"\n👤 {mensaje.chat.first_name or mensaje.chat.id}: {mensaje.text}")
        detener = asyncio.Event()
        escribiendo = asyncio.create_task(mantener_escribiendo(mensaje.chat, detener))
        try:
            # En un hilo: la IA o SQLite no bloquean el bucle de Telegram.
            respuesta = await asyncio.to_thread(
                procesar, mensaje.to_dict(), update.update_id, configuracion)
        except (sqlite3.Error, ValueError) as error:
            print("❌ No fue posible procesar la operación:", type(error).__name__)
            respuesta = ("⚠️ No pude confirmar esta operación. Revisa Mis "
                         "solicitudes antes de intentarlo de nuevo.")
        finally:
            detener.set()
            await escribiendo
        teclado = ReplyKeyboardMarkup(botones_cliente(mensaje.chat.id),
                                      resize_keyboard=True)
        for i in range(0, len(respuesta), 4000):
            await mensaje.reply_text(respuesta[i:i + 4000], reply_markup=teclado)

    # Confirmar conexión real e identidad del bot.
    async def listo(app):
        yo = await app.bot.get_me()
        if yo.username.lower() != USUARIO_BOT.lower():
            print(f"⚠️ Este token es de @{yo.username}, pero la página apunta a "
                  f"@{USUARIO_BOT}. Corrija USUARIO_BOT o el token.")
        # Ajustes opcionales: si Telegram los rechaza, el bot sigue funcionando.
        try:
            info = await app.bot.get_webhook_info()
            if info.url:
                await app.bot.delete_webhook()
        except Exception as error:
            print("⚠️ No se pudo revisar el webhook:", error)
        try:
            await app.bot.set_my_commands([
                ("start", "Empezar"), ("mis_pedidos", "Mis solicitudes"),
                ("tutores", "Ver tutores"), ("ayuda", "Ayuda"),
            ])
        except Exception as error:
            print("⚠️ Telegram no permitió actualizar el menú de comandos:", error)
            if "frozen" in str(error).lower():
                print("   La cuenta del bot o de su dueño está CONGELADA (frozen) por Telegram.")
                print("   Si el bot tampoco responde mensajes, revise @SpamBot o cree otro bot.")
        ARCHIVO_LISTO.write_text(json.dumps({
            "pid": os.getpid(), "usuario": yo.username,
            "momento": datetime.now().isoformat(timespec="seconds")}),
            encoding="utf-8")
        print("✅ Telegram conectado: @" + yo.username)
        print("📡 Esperando mensajes. Para detener: Ctrl+C")

    async def informar_error(update, context):
        error = context.error
        if isinstance(error, Conflict):
            print("❌ CONFLICTO: hay otra copia de este bot ejecutándose "
                  "(otra consola, otro PC o Colab). Deje solo una.")
        elif isinstance(error, NetworkError):
            print("🌐 Problema de red (se reintenta solo):", type(error).__name__)
        elif "frozen" in str(error).lower():
            print("❌ Telegram bloqueó la respuesta: la cuenta del bot está CONGELADA "
                  "(Frozen_method_invalid). Revise @SpamBot o cree un bot nuevo en @BotFather.")
        else:
            print("❌ Telegram:", type(error).__name__, error)
        print("📌 Las solicitudes guardadas permanecen en SQLite.")

    print(f"\n🎓 {NOMBRE_NEGOCIO.upper()} — ASISTENTE TUTI (Semana 04)")
    print("✅ Credenciales cargadas")
    print("🧠 Groq principal:", configuracion["modelo_groq"] if configuracion["clave_groq"]
          else "sin GROQ_API_KEY (se usa Gemini)")
    print("🛟 Gemini emergente:", configuracion["modelo_gemini"], "→",
          configuracion["reserva_gemini"])

    app = Application.builder().token(token).post_init(listo).build()
    app.add_handler(MessageHandler(filters.TEXT, atender))
    app.add_error_handler(informar_error)
    try:
        # No descartar mensajes pendientes al reiniciar el bot.
        app.run_polling(drop_pending_updates=False)
    except InvalidToken:
        print("❌ TELEGRAM_TOKEN no es válido. Pida uno en @BotFather y péguelo en .env")
    finally:
        ARCHIVO_LISTO.unlink(missing_ok=True)


# ========================================================
# H. VERIFICAR EL PROYECTO E INICIAR EL BOT
# ========================================================
def verificar_catalogo():
    if not PRODUCTOS:
        raise ValueError("El catálogo de tutores está vacío.")
    for codigo, p in PRODUCTOS.items():
        if not p.get("nombre") or type(p.get("precio")) is not int or p["precio"] <= 0:
            raise ValueError("Revise nombre y precio: " + codigo)


def main():
    try:
        preparar_librerias()
    except Exception as error:
        print("❌ No se pudieron preparar las librerías:", type(error).__name__)
        print("📌 Revise Internet y el archivo instalacion_librerias.log")
        return
    try:
        verificar_catalogo()
        print("✅ Carpeta del proyecto:", BASE)
        print("✅ SQLite disponible:", sqlite3.sqlite_version)
        print("📚 Tutores cargados:", len(PRODUCTOS))
        iniciar_db()
        print("📋 Solicitudes almacenadas:", contar_pedidos())
    except (sqlite3.Error, ValueError) as error:
        print("❌ No se pudo preparar el proyecto:", error)
        print("📌 Revise catálogo, permisos y diseño de la tabla.")
        return
    ejecutar_bot()


# Si consultas.py o iniciar.py importan funciones, NO se inicia el bot.
if __name__ == "__main__":
    main()