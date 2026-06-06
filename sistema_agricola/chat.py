# chat.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from motor_tareas import revisar_calendario_agricola
from google import genai
from google.genai import types
from dotenv import load_dotenv
import uvicorn
import os
import database
import bot_alerta
import asyncio
from datetime import datetime, timedelta

# ==============================================================
# 1. CONFIGURACIÓN DE IA  (nueva librería google-genai)
# ==============================================================
load_dotenv()

# Leer la llave desde el archivo .env
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
MODELO = "gemini-3.5-flash"

# ==============================================================
# 2. SCHEDULER
# ==============================================================
scheduler = AsyncIOScheduler()

# ==============================================================
# 3. LIFESPAN  (reemplaza los @app.on_event deprecados)
# ==============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── STARTUP ──
    database.inicializar_db()
    scheduler.add_job(
        revisar_calendario_agricola,
        'interval',
        hours=24,
        next_run_time=datetime.now()
    )
    scheduler.start()
    print("[APP] Motor de tareas agrícolas iniciado. Revisión cada 24h.")
    yield
    # ── SHUTDOWN ──
    scheduler.shutdown()
    print("[APP] Scheduler detenido correctamente.")

# ==============================================================
# 4. APP
# ==============================================================
database.inicializar_db()
app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

# ==============================================================
# 5. PÁGINA PRINCIPAL
# ==============================================================
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    siembras             = database.obtener_todas_siembras()
    cultivos_disponibles = list(database.CICLOS_AGRICOLAS.keys())
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "siembras":            siembras,
            "cultivos_disponibles": cultivos_disponibles,
            "ciclos":              database.CICLOS_AGRICOLAS,
        }
    )

# ==============================================================
# 6. ENDPOINT — DIAGNÓSTICO CON IA
# ==============================================================
@app.post("/diagnostico", response_class=HTMLResponse)
async def generar_diagnostico(
    request:     Request,
    cultivo_ia:  str = Form(...),
    siembra_ia:  str = Form(...),
    clima_ia:    str = Form(...),
    pregunta_ia: str = Form(default="Dame un diagnóstico general.")
):
    try:
        fecha_siembra = datetime.strptime(siembra_ia, "%Y-%m-%d").date()
        dias_ciclo    = (datetime.now().date() - fecha_siembra).days
        fase_texto    = f"Han transcurrido {dias_ciclo} días desde la siembra."
    except Exception:
        fase_texto    = "Fecha de siembra no válida."

    ciclo_info  = database.CICLOS_AGRICOLAS.get(cultivo_ia.lower().strip(), {})
    ciclo_texto = ""
    if ciclo_info:
        ciclo_texto = (
            f"Datos del ciclo para {ciclo_info.get('nombre', cultivo_ia)}: "
            f"Duración total {ciclo_info.get('duracion_dias', 'N/D')} días."
        )

    prompt = f"""
Eres un Sistema Experto Agrícola especializado en el estado de Sinaloa, México.
Hablas de forma directa, práctica y en español.

DATOS DEL AGRICULTOR:
- Cultivo: {cultivo_ia}
- Fecha de siembra: {siembra_ia}
- {fase_texto}
- Clima actual: {clima_ia}
- {ciclo_texto}

PREGUNTA DEL AGRICULTOR:
{pregunta_ia}

Responde con estas secciones exactas:
1. FASE FENOLÓGICA ACTUAL: En qué etapa está el cultivo ahora mismo.
2. RIEGO: Qué debe hacer con el riego esta semana.
3. PLAGAS: Qué plagas vigilar en este momento y cómo.
4. FERTILIZACIÓN: Recomendación concreta si aplica.
5. ACCIÓN INMEDIATA: La cosa más importante que debe hacer HOY.

Sé específico, usa datos de Sinaloa. Máximo 150 palabras por sección.
"""

    try:
        response     = client.models.generate_content(
            model    = MODELO,
            contents = prompt,
            config   = types.GenerateContentConfig(max_output_tokens=2000)
        )
        resultado_ia = response.text
    except Exception as e:
        resultado_ia = f"⚠️ Error en la IA: {str(e)}"

    siembras             = database.obtener_todas_siembras()
    cultivos_disponibles = list(database.CICLOS_AGRICOLAS.keys())

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "resultado_diagnostico": resultado_ia,
            "siembras":              siembras,
            "cultivos_disponibles":  cultivos_disponibles,
            "ciclos":                database.CICLOS_AGRICOLAS,
            "tab_activo":            "diagnostico",
        }
    )

# ==============================================================
# 7. ENDPOINT — REGISTRAR CULTIVO
# ==============================================================
@app.post("/registrar", response_class=HTMLResponse)
async def registrar_cultivo(
    request:     Request,
    cultivo_reg: str   = Form(...),
    tipo_reg:    str   = Form(...),
    siembra_reg: str   = Form(...),
    parcela_reg: str   = Form(default="Sin nombre"),
    superficie:  float = Form(default=0.0),
    notas_reg:   str   = Form(default="")
):
    print(f"[REGISTRO] Cultivo={cultivo_reg}, Tipo={tipo_reg}, Siembra={siembra_reg}, Parcela={parcela_reg}")

    try:
        nuevo_id, fecha_fin = database.registrar_siembra(
            cultivo_nombre    = cultivo_reg,
            cultivo_tipo      = tipo_reg,
            fecha_siembra_str = siembra_reg,
            parcela           = parcela_reg,
            superficie        = superficie,
            notas             = notas_reg
        )

        asyncio.create_task(
            bot_alerta.alerta_bienvenida(
                cultivo   = cultivo_reg,
                parcela   = parcela_reg,
                fecha_fin = fecha_fin
            )
        )

        mensaje_exito = (
            f"✅ Cultivo '{cultivo_reg}' registrado en parcela '{parcela_reg}'. "
            f"Ciclo programado hasta el {fecha_fin}. "
            f"Las alertas de riego y plagas están activas."
        )

    except Exception as e:
        mensaje_exito = f"⚠️ Error al registrar: {str(e)}"
        print(f"[REGISTRO ERROR] {e}")

    siembras             = database.obtener_todas_siembras()
    cultivos_disponibles = list(database.CICLOS_AGRICOLAS.keys())

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "resultado_registro":   mensaje_exito,
            "siembras":             siembras,
            "cultivos_disponibles": cultivos_disponibles,
            "ciclos":               database.CICLOS_AGRICOLAS,
            "tab_activo":           "calendario",
        }
    )

# ==============================================================
# 8. ENDPOINT — API JSON PARA CALENDARIO
# ==============================================================
@app.get("/api/siembras")
async def api_siembras():
    siembras  = database.obtener_todas_siembras()
    resultado = []
    hoy       = datetime.now().date()

    for s in siembras:
        id_s, cultivo, cultivo_tipo, fecha_siembra_str, fecha_fin_str, parcela, estado = s

        fecha_siembra = datetime.strptime(fecha_siembra_str, "%Y-%m-%d").date()
        fecha_fin     = datetime.strptime(fecha_fin_str,     "%Y-%m-%d").date()
        dias          = (hoy - fecha_siembra).days
        ciclo         = database.CICLOS_AGRICOLAS.get(cultivo_tipo, {})
        proximos      = []

        if ciclo:
            for riego in ciclo.get("riegos", []):
                fe = fecha_siembra + timedelta(days=riego["dia"])
                if fe >= hoy:
                    proximos.append({
                        "tipo":           "riego",
                        "nombre":         riego["nombre"],
                        "fecha":          str(fe),
                        "dias_restantes": (fe - hoy).days
                    })
            for plaga in ciclo.get("plagas", []):
                fi = fecha_siembra + timedelta(days=plaga["dia_inicio"])
                fp = fecha_siembra + timedelta(days=plaga["dia_fin"])
                if fp >= hoy:
                    proximos.append({
                        "tipo":           "plaga",
                        "nombre":         plaga["nombre"],
                        "fecha":          str(fi),
                        "fecha_fin":      str(fp),
                        "dias_restantes": max(0, (fi - hoy).days)
                    })
            fc = fecha_siembra + timedelta(days=ciclo.get("cosecha_dia_inicio", 180))
            if fc >= hoy:
                proximos.append({
                    "tipo":           "cosecha",
                    "nombre":         "Inicio de Cosecha",
                    "fecha":          str(fc),
                    "dias_restantes": (fc - hoy).days
                })

        proximos.sort(key=lambda x: x["dias_restantes"])

        resultado.append({
            "id":                 id_s,
            "cultivo":            cultivo,
            "cultivo_tipo":       cultivo_tipo,
            "parcela":            parcela,
            "fecha_siembra":      fecha_siembra_str,
            "fecha_fin":          fecha_fin_str,
            "dias_transcurridos": dias,
            "estado":             estado,
            "proximos_eventos":   proximos[:5],
        })

    return JSONResponse(content=resultado)

# ==============================================================
# 9. ENDPOINT — CERRAR SIEMBRA
# ==============================================================
@app.post("/cerrar/{siembra_id}")
async def cerrar_siembra(siembra_id: int):
    try:
        database.cerrar_siembra(siembra_id)
        return JSONResponse(content={"ok": True, "mensaje": f"Siembra {siembra_id} cerrada."})
    except Exception as e:
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=500)

# ==============================================================
# 10. ENTRADA PRINCIPAL
# ==============================================================
if __name__ == "__main__":
    uvicorn.run("chat:app", host="0.0.0.0", port=8000, reload=True)