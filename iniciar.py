# ============================================================
# iniciar.py — Inicio conjunto de Mi Tutor (Guía 04, paso 7)
# ------------------------------------------------------------
# Inicia orquestador.py (bot) y consultas.py (panel local),
# verifica cada condición y abre la página y el panel.
# Ctrl+C en esta ventana detiene ambos programas.
# Para diagnóstico individual: py orquestador.py / py consultas.py
# ============================================================
import json
import os
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
os.chdir(BASE)

import orquestador as o  # noqa: E402  (no inicia el bot al importarse)

URL_ADMIN = "http://127.0.0.1:8000"


def titulo(numero, texto):
    print(f"\n{numero}. {texto}")


def ok(texto):
    print("   ✅", texto)


def falla(texto):
    print("   ❌", texto)


def obtener_identidad(token):
    url = f"https://api.telegram.org/bot{token}/getMe"
    with urllib.request.urlopen(url, timeout=15) as r:
        datos = json.load(r)
    return datos["result"]["username"] if datos.get("ok") else None


def panel_responde():
    try:
        with urllib.request.urlopen(URL_ADMIN, timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def detener(procesos):
    for p in procesos:
        if p.poll() is None:
            p.terminate()
    for p in procesos:
        try:
            p.wait(timeout=8)
        except subprocess.TimeoutExpired:
            p.kill()


def main():
    print("=" * 56)
    print(f"🎓 {o.NOMBRE_NEGOCIO.upper()} — INICIO DE LA APLICACIÓN")
    print("=" * 56)

    titulo(1, "LIBRERÍAS Y CATÁLOGO")
    try:
        o.preparar_librerias()
        import dotenv  # noqa: F401
        import telegram  # noqa: F401
        from google import genai  # noqa: F401
        ok("Librerías de Telegram, Gemini y .env disponibles")
        o.verificar_catalogo()
        for p in o.PRODUCTOS.values():
            ok(f"{p['codigo']} — {p['tutor']} ({o.pesos(p['precio'])}/h)")
    except Exception as error:
        falla(f"No se pudo preparar: {error}")
        return

    titulo(2, "BASE DE DATOS")
    try:
        o.iniciar_db(silencioso=True)
        ok(f"SQLite preparada: {o.DB.name}")
        ok(f"Solicitudes almacenadas: {o.contar_pedidos()}")
    except Exception as error:
        falla(f"SQLite: {error}")
        return

    titulo(3, "CONFIGURACIÓN Y TELEGRAM")
    from dotenv import load_dotenv
    load_dotenv(BASE / ".env")
    token = (os.getenv("TELEGRAM_TOKEN") or "").strip()
    if not token:
        falla("Falta TELEGRAM_TOKEN en .env")
        return
    try:
        usuario = obtener_identidad(token)
    except Exception as error:
        falla(f"No hay conexión con Telegram: {type(error).__name__}")
        return
    if not usuario:
        falla("Telegram rechazó el token. Pida uno nuevo en @BotFather.")
        return
    if usuario.lower() != o.USUARIO_BOT.lower():
        falla(f"El token es de @{usuario}, pero la página usa @{o.USUARIO_BOT}.")
        return
    ok(f"Identidad verificada por Telegram: @{usuario}")

    o.ARCHIVO_LISTO.unlink(missing_ok=True)
    opciones = {"cwd": BASE, "stderr": subprocess.STDOUT}
    if os.name == "nt":
        opciones["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    entorno = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
    log_bot = open(BASE / "orquestador.log", "a", encoding="utf-8")
    log_panel = open(BASE / "consultas.log", "a", encoding="utf-8")
    bot = subprocess.Popen([sys.executable, "orquestador.py"], stdout=log_bot,
                           env=entorno, **opciones)
    panel = subprocess.Popen([sys.executable, "consultas.py"], stdout=log_panel,
                             env=entorno, **opciones)
    procesos = [bot, panel]

    try:
        listo = None
        for _ in range(60):                       # hasta 30 segundos
            if bot.poll() is not None:
                break
            if o.ARCHIVO_LISTO.exists():
                datos = json.loads(o.ARCHIVO_LISTO.read_text(encoding="utf-8"))
                if datos.get("pid") == bot.pid and \
                        datos.get("usuario", "").lower() == o.USUARIO_BOT.lower():
                    listo = datos
                    break
            time.sleep(0.5)
        if not listo:
            falla("El bot no confirmó su inicio. Revise orquestador.log")
            detener(procesos)
            return
        ok(f"Bot conectado y preparado: @{listo['usuario']}")

        titulo(4, "ASISTENTES Y FUNCIONES")
        if os.getenv("GROQ_API_KEY"):
            ok("Groq principal configurado")
        else:
            print("   ⚪ Groq sin clave: se usará Gemini directamente")
        if os.getenv("GEMINI_API_KEY"):
            ok("Gemini emergente configurado")
        print("   ℹ️  La conexión de IA se comprueba con una pregunta real en Telegram.")

        titulo(5, "ACCESOS")
        for _ in range(20):
            if panel_responde():
                break
            time.sleep(0.5)
        else:
            falla("El panel no respondió. Revise consultas.log (¿puerto 8000 ocupado?)")
            detener(procesos)
            return
        ok(f"Administrador: {URL_ADMIN}")
        ok(f"Estudiantes: https://t.me/{o.USUARIO_BOT}")
        webbrowser.open((BASE / "index.html").as_uri())
        webbrowser.open(URL_ADMIN)
        print("\n✅ APLICACIÓN LISTA PARA ATENDER SOLICITUDES")
        print("   Mantenga esta ventana abierta. Para cerrar todo: Ctrl+C\n")
        while all(p.poll() is None for p in procesos):
            time.sleep(1)
        falla("Un programa se detuvo. Revise orquestador.log y consultas.log")
    except KeyboardInterrupt:
        print("\nCerrando Mi Tutor...")
    finally:
        detener(procesos)
        o.ARCHIVO_LISTO.unlink(missing_ok=True)
        log_bot.close()
        log_panel.close()
        print("Programas detenidos. Las solicitudes siguen guardadas en SQLite.")


if __name__ == "__main__":
    main()
