# Mi Tutor — versión Corte 03 (Guías 03, 04 y C3S1)

Adaptación de Pizza MVP a Mi Tutor: el "producto" es una **hora de tutoría con un tutor** (TUT-01 … TUT-08) y el "pedido" es una **solicitud** con consecutivo `SOL-0001`.

## Cómo actualizar tu proyecto

1. Detén el bot anterior (Ctrl+C) y cualquier copia en Colab.
2. Haz una copia de respaldo de tu carpeta actual.
3. Copia todos los archivos de este paquete en tu carpeta. **Conserva tu `.env`** (este paquete no lo incluye; `.env.example` solo muestra los nombres de las variables).
4. Opcional: agrega `GROQ_API_KEY=...` a tu `.env` para usar Groq como proveedor principal. Sin esa clave, el bot usa Gemini directamente.
5. Ejecuta `Instalar.bat` una vez (crea el acceso directo "Mi Tutor" en el escritorio).
6. Abre **Iniciar.bat** (o el acceso directo). La primera vez descarga las librerías en `libs`.
7. En `index.html`, reemplaza `URL_FORMULARIO` por el enlace real de tu Google Forms.

Para diagnóstico individual: `py orquestador.py` y, en otra terminal, `py consultas.py`.

## Archivos

| Archivo | Qué hace |
|---|---|
| `orquestador.py` | Bot de Telegram (equivale a `pizza.py`, bloques A–H): SQLite, cotizar, solicitar, Mis solicitudes, cancelar con Sí/No, Groq + Gemini |
| `consultas.py` | Panel administrativo local `http://127.0.0.1:8000`: pestañas Solicitudes y Estadísticas, filtros, paginación, historial, aprobar / no aprobar / cancelar |
| `iniciar.py`, `Iniciar.bat`, `Instalar.bat` | Inicio conjunto en 5 bloques de verificación |
| `tutores.py` | Catálogo oficial (sin cambios) |
| `mitutor.db` | Se crea solo al iniciar. No lo borres. |
| `index.html`, `estudiante.html`, `tutor.html`, `css/`, `js/` | Página web rediseñada |

## Equivalencias con las guías

| Guía (Pizza MVP) | Mi Tutor |
|---|---|
| `pizza.py` | `orquestador.py` |
| `productos.py` | `tutores.py` (los precios incluyen el 10 % de comisión al guardarse) |
| `pizzeria.db` | `mitutor.db` (misma tabla `pedidos`, mismas columnas y estados) |
| `PED-0001` | `SOL-0001` |
| Cantidad (pizzas, 1–999) | Horas de tutoría (1–10) |
| `/comprar`, `/mis_pedidos`, Cancelar pedido | Botones Solicitar tutoría, Mis solicitudes, Cancelar solicitud (los comandos de la guía también funcionan) |
| `?start=PIZ-002` | `?start=TUT-01` (tutor) o `?start=TUT-MAT` (área) |

## Pruebas sugeridas para la entrega

- Página → tutor → Telegram → Cotizar → `3` (no crea solicitud).
- Solicitar tutoría → `0`, `1.5` (rechazadas) → `2` (crea `SOL-000X`, PENDIENTE).
- Mis solicitudes desde la página; `/pedido SOL-000X`.
- Panel: aprobar una, no aprobar otra con motivo, cancelar otra con motivo y casilla.
- Cancelar solicitud → consecutivo → No (sigue pendiente) / Sí (CANCELADO).
- Pedir cancelación, aprobarla en el panel y luego pulsar Sí: el bot informa que ya está aprobada.
- Cerrar todo, abrir solo `consultas.py`: los datos siguen ahí.
