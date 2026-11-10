# ============================================================
# consultas.py — Panel administrativo local de Mi Tutor
# ------------------------------------------------------------
# ACTUALIZADO SEMANA 04 (Guía 04, paso 6).
# Dos pestañas en el mismo servicio: Solicitudes y Estadísticas.
#   - Filtros Desde/Hasta (fecha de creación), estado y consecutivo.
#   - 10 solicitudes por página; las estadísticas usan TODO el filtro.
#   - Detalle con historial y decisiones (aprobar, no aprobar,
#     cancelar) enviadas por POST con token temporal.
#
# Solo funciona en ESTE computador: http://127.0.0.1:8000
# No agregue esta dirección a la página pública.
# Todas las herramientas usadas aquí vienen con Python.
# ============================================================
import secrets
from collections import Counter
from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
from math import ceil
from urllib.parse import parse_qs, urlencode, urlparse

from orquestador import (
    COMISION, DB, ESTADOS, NOMBRE_NEGOCIO, PREFIJO, PRODUCTOS,
    cambiar_estado, consultar, historial, iniciar_db, pesos,
)

PUERTO = 8000
POR_PAGINA = 10
ACTOR = "ADMINISTRADOR LOCAL"
# Token de formulario: cambia en cada inicio. Recargar el detalle
# después de reiniciar entrega el token nuevo.
TOKEN = secrets.token_urlsafe(24)

CLASE_ESTADO = {
    "PENDIENTE": "pendiente", "APROBADO": "aprobado",
    "NO APROBADO": "no-aprobado", "CANCELADO": "cancelado",
}


# ========================================================
# 1. FILTROS COMPARTIDOS ENTRE TABLA Y ESTADÍSTICAS
# ========================================================
def leer_filtros(parametros):
    return {clave: parametros.get(clave, [""])[0].strip()
            for clave in ("desde", "hasta", "estado", "buscar")}


def pedidos_filtrados(filtros):
    # El mismo conjunto alimenta tabla, indicadores y gráficos.
    codigo = filtros["buscar"].upper()
    return consultar("pedido" if codigo else "todos", codigo or None,
                     desde=filtros["desde"], hasta=filtros["hasta"],
                     estado=filtros["estado"])


def enlace(filtros, **opciones):
    valores = {k: v for k, v in filtros.items() if v}
    valores.update({k: v for k, v in opciones.items() if v not in ("", None)})
    return "/?" + urlencode(valores)


def e(valor):
    return escape(str(valor), quote=True)


def pastilla(estado):
    return f'<span class="estado {CLASE_ESTADO.get(estado, "")}">{e(estado.capitalize())}</span>'


# ========================================================
# 2. INDICADORES COHERENTES CON EL FILTRO
# ========================================================
def resumen(pedidos):
    conteos = Counter(p["estado"] for p in pedidos)
    aprobados = [p for p in pedidos if p["estado"] == "APROBADO"]
    valor = sum(p["total"] for p in aprobados)
    horas = Counter()
    for p in pedidos:
        tutor = PRODUCTOS.get(p["codigo_producto"], {}).get("tutor", p["nombre_producto"])
        horas[tutor] += p["cantidad"]
    return {"total": len(pedidos), "estados": conteos, "valor_aprobado": valor,
            "promedio_aprobado": valor / len(aprobados) if aprobados else 0,
            "horas": horas}


def barras(datos, clase_por_clave=None):
    if not datos:
        return '<p class="vacio">Sin datos para graficar con estos filtros.</p>'
    maximo = max(datos.values()) or 1
    filas = ""
    for clave, valor in datos.items():
        ancho = round(valor / maximo * 100, 1)
        clase = (clase_por_clave or {}).get(clave, "")
        filas += (f'<div class="barra"><span class="barra-rotulo">{e(clave)}</span>'
                  f'<span class="barra-pista"><span class="barra-relleno {clase}" '
                  f'style="width:{ancho}%"></span></span>'
                  f'<span class="barra-valor">{valor}</span></div>')
    return filas


def vista_estadisticas(pedidos):
    r = resumen(pedidos)
    tiles = [
        ("Solicitudes en el filtro", r["total"], ""),
        ("Pendientes", r["estados"].get("PENDIENTE", 0), "pendiente"),
        ("Aprobadas", r["estados"].get("APROBADO", 0), "aprobado"),
        ("No aprobadas", r["estados"].get("NO APROBADO", 0), "no-aprobado"),
        ("Canceladas", r["estados"].get("CANCELADO", 0), "cancelado"),
    ]
    html = '<div class="kpis">'
    for rotulo, valor, clase in tiles:
        html += (f'<div class="kpi {clase}"><span class="kpi-valor">{valor}</span>'
                 f'<span class="kpi-rotulo">{rotulo}</span></div>')
    html += "</div>"
    html += ('<div class="kpis kpis-dinero">'
             f'<div class="kpi"><span class="kpi-valor">{pesos(r["valor_aprobado"])}</span>'
             '<span class="kpi-rotulo">Valor aprobado (suma de totales APROBADOS; '
             'no es recaudo ni utilidad)</span></div>'
             f'<div class="kpi"><span class="kpi-valor">{pesos(round(r["promedio_aprobado"]))}</span>'
             '<span class="kpi-rotulo">Promedio por solicitud aprobada</span></div></div>')
    por_estado = {estado.capitalize(): r["estados"].get(estado, 0) for estado in ESTADOS}
    clases = {estado.capitalize(): CLASE_ESTADO[estado] for estado in ESTADOS}
    html += ('<div class="graficos">'
             '<section class="panel"><h3>Solicitudes por estado</h3>'
             + barras(por_estado if r["total"] else {}, clases) + '</section>'
             '<section class="panel"><h3>Horas solicitadas por tutor</h3>'
             + barras(dict(r["horas"].most_common())) + '</section></div>')
    return html


# ========================================================
# 3. TABLA PAGINADA Y DETALLE CON DECISIONES
# ========================================================
def vista_tabla(pedidos, filtros, pagina, seleccionado):
    total_paginas = max(1, ceil(len(pedidos) / POR_PAGINA))
    pagina = min(max(1, pagina), total_paginas)
    # Lo más reciente primero para el trabajo diario.
    ordenados = list(reversed(pedidos))
    visibles = ordenados[(pagina - 1) * POR_PAGINA:pagina * POR_PAGINA]
    filas = ""
    for p in visibles:
        url = enlace(filtros, vista="solicitudes", detalle=p["consecutivo"], pagina=pagina)
        activa = ' class="activa"' if p["consecutivo"] == seleccionado else ""
        filas += (
            f'<tr{activa}><td><a class="consecutivo" href="{e(url)}">{e(p["consecutivo"])}</a></td>'
            f'<td>{e(p["cliente"])}</td><td>{e(p["nombre_producto"].replace("Tutoría con ", ""))}</td>'
            f'<td class="num">{p["cantidad"]} h</td><td class="num">{pesos(p["total"])}</td>'
            f'<td class="tenue">{e(p["fecha"])} {e(p["hora"][:5])}</td>'
            f'<td>{pastilla(p["estado"])}</td>'
            f'<td><a class="ver" href="{e(url)}">Ver detalle</a></td></tr>'
        )
    if not filas:
        filas = ('<tr><td colspan="8" class="vacio">No hay solicitudes en el período '
                 'seleccionado con estos filtros. Prueba ampliar las fechas o elegir '
                 '«Todos los estados».</td></tr>')
    navegacion = ""
    if pagina > 1:
        navegacion += f'<a class="boton secundario" href="{e(enlace(filtros, vista="solicitudes", pagina=pagina - 1))}">Anterior</a>'
    if pagina < total_paginas:
        navegacion += f'<a class="boton secundario" href="{e(enlace(filtros, vista="solicitudes", pagina=pagina + 1))}">Siguiente</a>'
    return (
        '<div class="tabla-envoltura"><table><thead><tr>'
        + "".join(f"<th>{t}</th>" for t in (
            "Solicitud", "Estudiante", "Tutor", "Horas", "Total",
            "Creada", "Estado", ""))
        + "</tr></thead><tbody>" + filas + "</tbody></table></div>"
        f'<div class="paginacion"><span>Página {pagina} de {total_paginas}, '
        f'{len(pedidos)} solicitudes, {POR_PAGINA} por página</span>'
        f'<span class="paginacion-botones">{navegacion}</span></div>'
    )


def vista_detalle(consecutivo, filtros, pagina):
    encontrados = consultar("pedido", consecutivo)
    cerrar = e(enlace(filtros, vista="solicitudes", pagina=pagina))
    if not encontrados:
        return (f'<aside class="detalle panel"><a class="cerrar" href="{cerrar}" '
                f'aria-label="Cerrar detalle">×</a><p>No existe la solicitud '
                f'{e(consecutivo)}.</p></aside>')
    p = encontrados[0]
    datos = [
        ("Estudiante", p["cliente"]), ("Chat de Telegram", p["chat_id"]),
        ("Tutor", f'{p["codigo_producto"]} — {p["nombre_producto"]}'),
        ("Horas", p["cantidad"]),
        (f"Valor por hora (con {COMISION} %)", pesos(p["precio_unitario"])),
        ("Total", pesos(p["total"])),
        ("Creada", f'{p["fecha"]} {p["hora"]}'),
    ]
    if p["motivo"]:
        datos.append(("Motivo", p["motivo"]))
    if p["actualizado_en"]:
        datos.append(("Última decisión", f'{p["actualizado_en"]} por {p["actualizado_por"]}'))
    html = (f'<aside class="detalle panel"><a class="cerrar" href="{cerrar}" '
            'aria-label="Cerrar detalle">×</a>'
            f'<h2>{e(p["consecutivo"])} {pastilla(p["estado"])}</h2><dl>')
    for k, v in datos:
        html += f"<dt>{e(k)}</dt><dd>{e(v)}</dd>"
    html += "</dl><h3>Historial</h3>"
    eventos = historial(p["id"])
    if eventos:
        html += '<ol class="historial">'
        for h in eventos:
            motivo = f' — {e(h["motivo"])}' if h["motivo"] else ""
            html += (f'<li><strong>{e(h["estado_anterior"].capitalize())} a '
                     f'{e(h["estado_nuevo"].capitalize())}</strong>{motivo}'
                     f'<span>{e(h["fecha_hora"])}, {e(h["actor"])}</span></li>')
        html += "</ol>"
    else:
        html += '<p class="tenue">Sin decisiones registradas todavía.</p>'

    if p["estado"] == "PENDIENTE":
        oculto = (f'<input type="hidden" name="token" value="{TOKEN}">'
                  f'<input type="hidden" name="consecutivo" value="{e(p["consecutivo"])}">'
                  + "".join(f'<input type="hidden" name="f_{k}" value="{e(v)}">'
                            for k, v in filtros.items())
                  + f'<input type="hidden" name="pagina" value="{pagina}">')
        html += (
            '<h3>Decidir</h3><div class="decisiones">'
            f'<form method="post">{oculto}<input type="hidden" name="decision" value="APROBADO">'
            '<button class="boton aprobar">Confirmar aprobación</button>'
            '<p class="ayuda">Aprobar significa aceptar la solicitud. No certifica un pago.</p></form>'
            f'<form method="post">{oculto}<input type="hidden" name="decision" value="NO APROBADO">'
            '<label for="motivo-na">Motivo de no aprobación</label>'
            '<textarea id="motivo-na" name="motivo" maxlength="500" required '
            'placeholder="Ej.: el tutor no tiene disponibilidad esta semana"></textarea>'
            '<button class="boton rechazar">Confirmar no aprobación</button></form>'
            f'<form method="post">{oculto}<input type="hidden" name="decision" value="CANCELADO">'
            '<label for="motivo-c">Motivo de cancelación</label>'
            '<textarea id="motivo-c" name="motivo" maxlength="500" required '
            'placeholder="Ej.: el estudiante pidió cancelar por WhatsApp"></textarea>'
            '<label class="casilla"><input type="checkbox" name="confirmar" value="si" required> '
            f'Revisé {e(p["consecutivo"])} y sus datos</label>'
            '<button class="boton secundario">Confirmar cancelación</button></form></div>'
        )
    else:
        html += ('<p class="cerrada">Esta solicitud ya no está pendiente: su estado es '
                 'final y no admite más decisiones.</p>')
    return html + "</aside>"


# ========================================================
# 4. PÁGINA COMPLETA
# ========================================================
ESTILOS = """
:root{--papel:#F3F6F5;--hoja:#FFFFFF;--tinta:#16233A;--tinta-suave:#56647A;--linea:#D9E1DF;
--pizarra:#1D6B53;--pizarra-osc:#14513E;--resaltador:#F4D35E;
--pend:#9A6A00;--pend-f:#FBF0CF;--apro:#1D6B53;--apro-f:#DDEFE7;--noap:#A83A32;--noap-f:#F7E1DE;
--canc:#5B6676;--canc-f:#E7EAEE;--radio:10px}
*{box-sizing:border-box}body{margin:0;background:var(--papel);color:var(--tinta);
font:15px/1.5 "Public Sans",system-ui,-apple-system,"Segoe UI",sans-serif}
h1,h2,h3{font-family:"Bricolage Grotesque","Public Sans",system-ui,sans-serif;margin:0;letter-spacing:-.01em}
a{color:var(--pizarra)}:focus-visible{outline:3px solid var(--resaltador);outline-offset:2px}
.barra-sup{background:var(--tinta);color:#fff}
.barra-sup .cont{display:flex;align-items:center;justify-content:space-between;gap:16px;height:60px}
.marca{display:flex;align-items:center;gap:10px;font-family:"Bricolage Grotesque",sans-serif;font-weight:700;font-size:1.1rem}
.marca svg{flex:none}.marca small{font:500 .8rem "Public Sans",sans-serif;color:#AFC0D6}
.barra-sup .local{font-size:.8rem;color:#AFC0D6}
.cont{max-width:1240px;margin:0 auto;padding:0 20px}
main.cont{padding-top:24px;padding-bottom:48px}
.encabezado{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-bottom:18px}
.encabezado h1{font-size:1.6rem}.encabezado p{margin:4px 0 0;color:var(--tinta-suave)}
.pestanas{display:inline-flex;background:#E3E9E7;border-radius:999px;padding:4px}
.pestanas a{padding:7px 16px;border-radius:999px;text-decoration:none;color:var(--tinta-suave);font-weight:600;font-size:.9rem}
.pestanas a.activa{background:var(--hoja);color:var(--tinta);box-shadow:0 1px 2px rgba(22,35,58,.12)}
.filtros{display:flex;flex-wrap:wrap;gap:12px;align-items:flex-end;background:var(--hoja);
border:1px solid var(--linea);border-radius:var(--radio);padding:14px 16px;margin-bottom:16px}
.filtros label{display:flex;flex-direction:column;gap:4px;font-size:.78rem;font-weight:600;color:var(--tinta-suave)}
input,select,textarea{font:inherit;color:var(--tinta);border:1px solid var(--linea);border-radius:8px;padding:8px 10px;background:#fff}
textarea{width:100%;min-height:64px;resize:vertical}
.boton{display:inline-flex;align-items:center;justify-content:center;border:0;border-radius:8px;
padding:9px 16px;font:600 .9rem "Public Sans",sans-serif;cursor:pointer;text-decoration:none;background:var(--pizarra);color:#fff}
.boton:hover{background:var(--pizarra-osc)}
.boton.secundario{background:transparent;color:var(--tinta);border:1px solid var(--linea)}
.boton.secundario:hover{background:#E9EEEC}
.boton.aprobar{background:var(--apro)}.boton.rechazar{background:var(--noap)}.boton.rechazar:hover{background:#8A2F28}
.aviso{border-radius:var(--radio);padding:11px 14px;margin-bottom:16px;font-weight:500}
.aviso.ok{background:var(--apro-f);color:var(--pizarra-osc)}.aviso.error{background:var(--noap-f);color:var(--noap)}
.espacio{display:grid;grid-template-columns:minmax(0,1fr);gap:18px;align-items:start}
.espacio.con-detalle{grid-template-columns:minmax(0,1fr) 380px}
.panel{background:var(--hoja);border:1px solid var(--linea);border-radius:var(--radio);padding:18px}
.tabla-envoltura{background:var(--hoja);border:1px solid var(--linea);border-radius:var(--radio);overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:.9rem}
th{text-align:left;font-size:.76rem;font-weight:600;color:var(--tinta-suave);padding:11px 12px;border-bottom:1px solid var(--linea);background:#F8FAF9;white-space:nowrap}
td{padding:11px 10px;border-bottom:1px solid #EDF1F0;white-space:nowrap}
tr:last-child td{border-bottom:0}tr.activa td{background:#FFFBEA}
td.num{text-align:right;font-variant-numeric:tabular-nums}.tenue{color:var(--tinta-suave)}
.consecutivo{font-weight:700;text-decoration:none;color:var(--tinta);font-variant-numeric:tabular-nums}
.ver{font-weight:600;font-size:.85rem}
.vacio{text-align:center;color:var(--tinta-suave);padding:28px 12px;white-space:normal}
.paginacion{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-top:12px;font-size:.85rem;color:var(--tinta-suave);flex-wrap:wrap}
.paginacion-botones{display:flex;gap:8px}
.estado{display:inline-block;padding:3px 10px;border-radius:999px;font-size:.78rem;font-weight:700}
.estado.pendiente{background:var(--pend-f);color:var(--pend)}.estado.aprobado{background:var(--apro-f);color:var(--apro)}
.estado.no-aprobado{background:var(--noap-f);color:var(--noap)}.estado.cancelado{background:var(--canc-f);color:var(--canc)}
.detalle{position:sticky;top:16px}.detalle h2{font-size:1.3rem;display:flex;align-items:center;gap:10px;margin-bottom:12px;padding-right:24px}
.detalle h3{font-size:.95rem;margin:18px 0 8px}
.cerrar{position:absolute;right:14px;top:10px;font-size:1.5rem;text-decoration:none;color:var(--tinta-suave)}
dl{display:grid;grid-template-columns:auto 1fr;gap:6px 14px;margin:0;font-size:.88rem}
dt{color:var(--tinta-suave)}dd{margin:0;font-weight:600;word-break:break-word}
.historial{list-style:none;margin:0;padding:0 0 0 14px;border-left:2px solid var(--linea);font-size:.85rem}
.historial li{margin-bottom:10px}.historial span{display:block;color:var(--tinta-suave);font-size:.78rem}
.decisiones form{border-top:1px solid #EDF1F0;padding:12px 0;display:flex;flex-direction:column;gap:8px}
.decisiones label{font-size:.8rem;font-weight:600}.decisiones .casilla{font-weight:500;display:flex;gap:8px;align-items:center}
.ayuda{margin:0;font-size:.78rem;color:var(--tinta-suave)}
.cerrada{background:#F3F5F7;border-radius:8px;padding:10px 12px;font-size:.85rem;color:var(--tinta-suave)}
.kpis{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:12px}
.kpis-dinero{grid-template-columns:repeat(2,1fr)}
.kpi{background:var(--hoja);border:1px solid var(--linea);border-radius:var(--radio);padding:14px 16px;border-top:4px solid var(--tinta)}
.kpi.pendiente{border-top-color:#D9A514}.kpi.aprobado{border-top-color:var(--apro)}
.kpi.no-aprobado{border-top-color:var(--noap)}.kpi.cancelado{border-top-color:var(--canc)}
.kpi-valor{display:block;font:700 1.7rem "Bricolage Grotesque",sans-serif;font-variant-numeric:tabular-nums}
.kpi-rotulo{font-size:.8rem;color:var(--tinta-suave)}
.graficos{display:grid;grid-template-columns:1fr 1fr;gap:12px}.graficos h3{font-size:1rem;margin-bottom:14px}
.barra{display:grid;grid-template-columns:130px 1fr 40px;gap:10px;align-items:center;margin-bottom:10px;font-size:.85rem}
.barra-pista{height:14px;background:#EDF1F0;border-radius:4px;overflow:hidden}
.barra-relleno{display:block;height:100%;background:var(--tinta);border-radius:4px}
.barra-relleno.pendiente{background:#D9A514}.barra-relleno.aprobado{background:var(--apro)}
.barra-relleno.no-aprobado{background:var(--noap)}.barra-relleno.cancelado{background:var(--canc)}
.barra-valor{text-align:right;font-weight:700;font-variant-numeric:tabular-nums}
.pie{color:var(--tinta-suave);font-size:.8rem;margin-top:28px}
@media(max-width:1000px){.espacio.con-detalle{grid-template-columns:minmax(0,1fr)}.detalle{position:static}
.kpis{grid-template-columns:repeat(2,1fr)}.graficos{grid-template-columns:1fr}}
@media(max-width:560px){.barra-sup .local,.marca small{display:none}.barra{grid-template-columns:96px 1fr 32px}.filtros label{flex:1 1 140px}}
"""

LOGO = ('<svg width="28" height="28" viewBox="0 0 32 32" aria-hidden="true">'
        '<rect width="32" height="32" rx="8" fill="#F4D35E"/>'
        '<path d="M9 22V10l7 7 7-7v12" fill="none" stroke="#16233A" stroke-width="3" '
        'stroke-linecap="round" stroke-linejoin="round"/></svg>')


def pagina(parametros):
    filtros = leer_filtros(parametros)
    vista = parametros.get("vista", ["solicitudes"])[0]
    if vista not in ("solicitudes", "estadisticas"):
        vista = "solicitudes"
    try:
        numero = int(parametros.get("pagina", ["1"])[0])
    except ValueError:
        numero = 1
    detalle = parametros.get("detalle", [""])[0].upper()
    mensaje = parametros.get("msg", [""])[0]
    tipo_msg = parametros.get("tipo", ["ok"])[0]

    error = ""
    try:
        pedidos = pedidos_filtrados(filtros)
    except ValueError as falla:
        error = str(falla)
        pedidos = []

    opciones = '<option value="">Todos los estados</option>' + "".join(
        f'<option value="{e(s)}"{" selected" if filtros["estado"] == s else ""}>{e(s.capitalize())}</option>'
        for s in ESTADOS)
    formulario = (
        '<form class="filtros" method="get">'
        f'<input type="hidden" name="vista" value="{vista}">'
        f'<label>Desde<input type="date" name="desde" value="{e(filtros["desde"])}"></label>'
        f'<label>Hasta<input type="date" name="hasta" value="{e(filtros["hasta"])}"></label>'
        f'<label>Estado<select name="estado">{opciones}</select></label>'
        f'<label>Consecutivo<input name="buscar" value="{e(filtros["buscar"])}" '
        f'placeholder="{PREFIJO}-0001" size="10"></label>'
        '<button class="boton">Aplicar filtros</button>'
        f'<a class="boton secundario" href="/?vista={vista}">Limpiar filtros</a></form>'
    )
    avisos = ""
    if error:
        avisos += f'<div class="aviso error" role="alert">{e(error)} Corrige el filtro para continuar.</div>'
    if mensaje:
        clase = "ok" if tipo_msg == "ok" else "error"
        avisos += f'<div class="aviso {clase}" role="status">{e(mensaje)}</div>'

    if vista == "estadisticas":
        cuerpo = vista_estadisticas(pedidos)
    else:
        tabla = vista_tabla(pedidos, filtros, numero, detalle)
        if detalle:
            cuerpo = (f'<div class="espacio con-detalle"><div>{tabla}</div>'
                      f'{vista_detalle(detalle, filtros, numero)}</div>')
        else:
            cuerpo = f'<div class="espacio">{tabla}</div>'

    def pestana(clave, rotulo):
        activa = " activa" if vista == clave else ""
        return f'<a class="{activa.strip()}" href="{e(enlace(filtros, vista=clave))}">{rotulo}</a>'

    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Administración — {e(NOMBRE_NEGOCIO)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700&family=Public+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{ESTILOS}</style></head><body>
<header class="barra-sup"><div class="cont">
<div class="marca">{LOGO}<span>{e(NOMBRE_NEGOCIO)} <small>Administración local</small></span></div>
<span class="local">Solo en este computador</span></div></header>
<main class="cont">
<div class="encabezado"><div><h1>Solicitudes de tutoría</h1>
<p>Revisa, aprueba o cancela solicitudes pendientes. Las decisiones quedan guardadas en SQLite.</p></div>
<nav class="pestanas" aria-label="Vistas">{pestana("solicitudes", "Solicitudes")}{pestana("estadisticas", "Estadísticas")}</nav></div>
{formulario}{avisos}{cuerpo}
<p class="pie">Base de datos: {e(DB.name)}. Recarga la página para ver solicitudes nuevas del bot.</p>
</main></body></html>"""


# ========================================================
# 5. ATENDER LECTURAS (GET) Y DECISIONES (POST)
# ========================================================
class ConsultaLocal(BaseHTTPRequestHandler):
    def _responder(self, contenido, codigo=200):
        datos = contenido.encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def do_GET(self):
        ruta = urlparse(self.path)
        if ruta.path != "/":
            self.send_error(404)
            return
        try:
            self._responder(pagina(parse_qs(ruta.query)))
        except Exception as error:
            print("❌ Error al consultar:", type(error).__name__)
            self.send_error(503, "Revise la base de datos local")

    def do_POST(self):
        if urlparse(self.path).path != "/":
            self.send_error(404)
            return
        largo = min(int(self.headers.get("Content-Length", 0) or 0), 20000)
        datos = parse_qs(self.rfile.read(largo).decode("utf-8"))
        campo = lambda k: datos.get(k, [""])[0].strip()  # noqa: E731
        filtros = {k: campo("f_" + k) for k in ("desde", "hasta", "estado", "buscar")}
        consecutivo = campo("consecutivo").upper()
        decision = campo("decision")
        destino = dict(vista="solicitudes", detalle=consecutivo, pagina=campo("pagina") or 1)
        if not secrets.compare_digest(campo("token"), TOKEN):
            destino.update(msg="El formulario venció porque el panel se reinició. "
                               "Revisa el estado actual y vuelve a decidir.", tipo="error")
        elif decision == "CANCELADO" and campo("confirmar") != "si":
            destino.update(msg="Marca la casilla de revisión para confirmar la cancelación.",
                           tipo="error")
        elif decision == "CANCELADO" and not campo("motivo"):
            destino.update(msg="Escribe el motivo de la cancelación.", tipo="error")
        else:
            try:
                p = cambiar_estado(consecutivo, decision, ACTOR, campo("motivo"))
                destino.update(msg=f"{p['consecutivo']} quedó {p['estado']}. "
                                   "El estudiante lo verá en Mis solicitudes.", tipo="ok")
                print(f"✅ {p['consecutivo']} → {p['estado']} ({ACTOR})")
            except ValueError as error:
                destino.update(msg=str(error), tipo="error")
        # Patrón POST → redirección → GET: recargar no repite la decisión.
        self.send_response(303)
        self.send_header("Location", enlace(filtros, **destino))
        self.end_headers()

    def log_message(self, formato, *args):
        pass  # Consola limpia; los errores se informan arriba.


# ========================================================
# 6. PREPARAR SQLITE E INICIAR LA PÁGINA LOCAL
# ========================================================
def main():
    try:
        iniciar_db()
    except Exception as error:
        print("❌ No se pudo preparar SQLite:", error)
        print("📌 Revise permisos y diseño de la tabla.")
        return
    try:
        servidor = HTTPServer(("127.0.0.1", PUERTO), ConsultaLocal)
    except OSError:
        print(f"❌ No fue posible abrir el puerto {PUERTO}.")
        print("📌 Compruebe si consultas.py ya está ejecutándose.")
        return
    print("✅ Panel administrativo iniciado")
    print(f"🌐 Abra http://127.0.0.1:{PUERTO} en ESTE computador.")
    print("📌 Mantenga esta terminal abierta. Para detener: Ctrl+C.")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nPanel detenido. Las solicitudes siguen guardadas.")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
