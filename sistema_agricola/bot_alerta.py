# bot_alerta.py
import telegram
import asyncio
from datetime import datetime

# --- CONFIGURACIÓN ---
TOKEN   = "TOKEN"
CHAT_ID = "NUMERO DE TOKEN"

# ==============================================================
# TIPOS DE ALERTA — Cada uno tiene su propio formato de mensaje
# ==============================================================

async def enviar_alerta(mensaje: str):
    """Función base: envía cualquier texto plano al bot."""
    try:
        bot = telegram.Bot(token=TOKEN)
        await bot.send_message(chat_id=CHAT_ID, text=mensaje, parse_mode="HTML")
        print(f"[TELEGRAM] Alerta enviada: {mensaje[:60]}...")
    except Exception as e:
        print(f"[TELEGRAM ERROR] No se pudo enviar: {e}")


async def alerta_riego(cultivo: str, parcela: str, nombre_riego: str, descripcion: str, dias: int):
    """Alerta específica de riego."""
    mensaje = (
        f"💧 <b>ALERTA DE RIEGO</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🌱 <b>Cultivo:</b> {cultivo}\n"
        f"📍 <b>Parcela:</b> {parcela}\n"
        f"📅 <b>Día del ciclo:</b> {dias}\n"
        f"🚿 <b>Tipo:</b> {nombre_riego}\n\n"
        f"📋 <b>Instrucciones:</b>\n{descripcion}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )
    await enviar_alerta(mensaje)


async def alerta_plaga(cultivo: str, parcela: str, nombre_plaga: str, descripcion: str, dias: int):
    """Alerta específica de riesgo de plaga."""
    mensaje = (
        f"🐛 <b>⚠️ ALERTA DE PLAGA</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🌱 <b>Cultivo:</b> {cultivo}\n"
        f"📍 <b>Parcela:</b> {parcela}\n"
        f"📅 <b>Día del ciclo:</b> {dias}\n"
        f"🦟 <b>Riesgo:</b> {nombre_plaga}\n\n"
        f"📋 <b>Qué hacer:</b>\n{descripcion}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )
    await enviar_alerta(mensaje)


async def alerta_cosecha(cultivo: str, parcela: str, descripcion: str, dias: int):
    """Alerta de inicio de ventana de cosecha."""
    mensaje = (
        f"🌾 <b>¡ÉPOCA DE COSECHA!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🌱 <b>Cultivo:</b> {cultivo}\n"
        f"📍 <b>Parcela:</b> {parcela}\n"
        f"📅 <b>Día del ciclo:</b> {dias}\n\n"
        f"📋 <b>Indicaciones:</b>\n{descripcion}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )
    await enviar_alerta(mensaje)


async def alerta_bienvenida(cultivo: str, parcela: str, fecha_fin: str):
    """Se envía cuando se registra un nuevo cultivo."""
    mensaje = (
        f"✅ <b>CULTIVO REGISTRADO</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🌱 <b>Cultivo:</b> {cultivo}\n"
        f"📍 <b>Parcela:</b> {parcela}\n"
        f"📆 <b>Fin estimado:</b> {fecha_fin}\n\n"
        f"El sistema monitoreará riegos, plagas y cosecha automáticamente.\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🌾 Sistema Agrícola Sinaloa activo."
    )
    await enviar_alerta(mensaje)


# Test directo
if __name__ == "__main__":
    asyncio.run(enviar_alerta("✅ Sistema Agrícola Sinaloa: Conexión confirmada y operativa."))