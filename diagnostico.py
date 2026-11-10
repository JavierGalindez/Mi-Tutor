# ============================================================
# diagnostico.py - ¿Por qué mi bot no responde?
# Ejecuta:  python diagnostico.py   (o  py diagnostico.py)
# Revisa .env, el token de Telegram y la API Key de Gemini.
# ============================================================
import os
import sys
import json
import urllib.request
import urllib.error

CARPETA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(CARPETA, "libs"))


def ok(t): print(f"  ✅ {t}")
def mal(t): print(f"  ❌ {t}")
def ojo(t): print(f"  ⚠️  {t}")


print("\n(Ejecuta este diagnóstico con orquestador.py DETENIDO)")
print("\n1) Archivo .env")
ruta_env = os.path.join(CARPETA, ".env")
if not os.path.exists(ruta_env):
    mal(f"No existe {ruta_env}. Créalo con TELEGRAM_TOKEN=... y GEMINI_API_KEY=...")
    sys.exit(1)
from dotenv import load_dotenv
load_dotenv(ruta_env)
token = (os.getenv("TELEGRAM_TOKEN") or "").strip().strip('"').strip("'")
clave = (os.getenv("GEMINI_API_KEY") or "").strip().strip('"').strip("'")
modelos = [(os.getenv("GEMINI_MODEL") or os.getenv("GEMINI_MODELO") or "gemini-3.5-flash-lite").strip(),
           os.getenv("GEMINI_MODELO_RESPALDO", "gemini-3.6-flash").strip()]
ok("TELEGRAM_TOKEN encontrado") if token else mal("Falta TELEGRAM_TOKEN")
ok("GEMINI_API_KEY encontrada") if clave else mal("Falta GEMINI_API_KEY")


def telegram(metodo):
    url = f"https://api.telegram.org/bot{token}/{metodo}"
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return json.load(e)


print("\n2) Telegram")
try:
    yo = telegram("getMe")
    if yo.get("ok"):
        ok(f"Token válido. El bot es @{yo['result']['username']}")
        if yo["result"]["username"].lower() != "MiTutorKevin_bot_bot":
            ojo("Los botones de la página apuntan a @MiTutorKevin_bot_bot: deben coincidir.")
    else:
        mal(f"Token rechazado ({yo.get('description')}). Genera uno nuevo en @BotFather "
            "→ /mybots → tu bot → API Token, y pégalo en .env")
    hook = telegram("getWebhookInfo")
    if hook.get("ok") and hook["result"].get("url"):
        ojo("Hay un webhook activo; orquestador.py lo quita al arrancar.")
    prueba = telegram("getUpdates?timeout=0&limit=1")
    if prueba.get("error_code") == 409:
        mal("CONFLICTO: otro programa está usando este bot ahora mismo "
            "(otra consola, otro PC, Colab o un compañero). Ciérralo.")
    elif prueba.get("ok"):
        ok("Nadie más está escuchando este bot en este momento.")
except Exception as e:
    mal(f"No hay conexión con Telegram: {e}")

print("\n3) Gemini")
try:
    from google import genai
    cliente = genai.Client(api_key=clave)
    disponibles = []
    try:
        disponibles = [m.name.replace("models/", "") for m in cliente.models.list()]
        ok(f"API Key válida ({len(disponibles)} modelos visibles)")
    except Exception as e:
        mal(f"La API Key no funciona: {e}")
        print("     → Crea una nueva en https://aistudio.google.com/apikey y pégala en .env")
    for modelo in modelos:
        if disponibles and modelo not in disponibles:
            ojo(f"{modelo} no aparece en la lista de modelos de tu cuenta.")
        try:
            r = cliente.interactions.create(model=modelo, input="Responde solo: OK")
            ok(f"{modelo} responde: {(r.output_text or '').strip()[:40]}")
        except Exception as e:
            mal(f"{modelo} falla: {e}")
    flash = sorted(m for m in disponibles if "flash" in m)
    if flash:
        print("\n  Modelos 'flash' de tu cuenta (puedes poner uno en GEMINI_MODELO del .env):")
        for m in flash:
            print(f"     - {m}")
except Exception as e:
    mal(f"No se pudo probar Gemini: {e}")

print("\nSi todo sale ✅ y el bot sigue sin responder: ¿está abierta la consola con "
      "Iniciar.bat (o py orquestador.py)? El bot SOLO responde mientras corre.\n")
