# motor_tareas.py
from datetime import datetime
import asyncio
import database
import bot_alerta

# ==============================================================
# MOTOR PRINCIPAL — Se ejecuta cada día automáticamente
# ==============================================================

async def revisar_calendario_agricola():
    """
    Revisa todas las siembras activas y dispara alertas según
    el día exacto del ciclo usando los datos de CICLOS_AGRICOLAS.
    """
    print(f"\n[MOTOR] Revisión iniciada: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    siembras = database.obtener_siembras_activas()

    if not siembras:
        print("[MOTOR] No hay siembras activas en este momento.")
        return

    hoy = datetime.now().date()

    for siembra in siembras:
        id_s, cultivo, cultivo_tipo, fecha_siembra_str, fecha_fin_str, parcela, superficie, notas = siembra

        fecha_siembra = datetime.strptime(fecha_siembra_str, "%Y-%m-%d").date()
        fecha_fin     = datetime.strptime(fecha_fin_str,     "%Y-%m-%d").date()
        dias          = (hoy - fecha_siembra).days

        print(f"[MOTOR] Revisando: {cultivo} | Parcela: {parcela} | Día {dias}")

        # Si ya pasó la fecha de fin, cerrar automáticamente
        if hoy > fecha_fin:
            database.cerrar_siembra(id_s)
            await bot_alerta.enviar_alerta(
                f"📦 <b>CICLO CERRADO</b>\n"
                f"El cultivo <b>{cultivo}</b> en parcela <b>{parcela}</b> "
                f"ha completado su ciclo y fue marcado como finalizado."
            )
            print(f"[MOTOR] Siembra {id_s} cerrada automáticamente.")
            continue

        # Obtener la configuración del ciclo
        ciclo = database.CICLOS_AGRICOLAS.get(cultivo_tipo)
        if not ciclo:
            print(f"[MOTOR] Tipo de cultivo '{cultivo_tipo}' no reconocido, se omite.")
            continue

        # ----------------------------------------------------------
        # 1. REVISAR RIEGOS
        # ----------------------------------------------------------
        for riego in ciclo["riegos"]:
            dia_riego   = riego["dia"]
            clave_alerta = f"riego_dia_{dia_riego}"

            if dias == dia_riego and not database.alerta_ya_enviada(id_s, clave_alerta):
                await bot_alerta.alerta_riego(
                    cultivo      = cultivo,
                    parcela      = parcela,
                    nombre_riego = riego["nombre"],
                    descripcion  = riego["descripcion"],
                    dias         = dias
                )
                database.registrar_alerta_enviada(id_s, clave_alerta, riego["nombre"])
                print(f"[MOTOR] ✅ Alerta de riego enviada: {riego['nombre']}")

        # ----------------------------------------------------------
        # 2. REVISAR PLAGAS
        # ----------------------------------------------------------
        for plaga in ciclo["plagas"]:
            dia_ini      = plaga["dia_inicio"]
            dia_fin_p    = plaga["dia_fin"]

            # Alerta al ENTRAR a la ventana de riesgo
            clave_entrada = f"plaga_inicio_{dia_ini}_{plaga['nombre'][:10]}"
            if dias == dia_ini and not database.alerta_ya_enviada(id_s, clave_entrada):
                await bot_alerta.alerta_plaga(
                    cultivo      = cultivo,
                    parcela      = parcela,
                    nombre_plaga = plaga["nombre"],
                    descripcion  = f"⚠️ INICIO DE VENTANA DE RIESGO.\n{plaga['descripcion']}",
                    dias         = dias
                )
                database.registrar_alerta_enviada(id_s, clave_entrada, plaga["nombre"])
                print(f"[MOTOR] ✅ Alerta de plaga (inicio) enviada: {plaga['nombre']}")

            # Recordatorio a MITAD de la ventana
            dia_mitad     = dia_ini + ((dia_fin_p - dia_ini) // 2)
            clave_mitad   = f"plaga_mitad_{dia_mitad}_{plaga['nombre'][:10]}"
            if dias == dia_mitad and not database.alerta_ya_enviada(id_s, clave_mitad):
                await bot_alerta.alerta_plaga(
                    cultivo      = cultivo,
                    parcela      = parcela,
                    nombre_plaga = plaga["nombre"],
                    descripcion  = f"🔁 RECORDATORIO: Sigues en ventana de riesgo.\n{plaga['descripcion']}",
                    dias         = dias
                )
                database.registrar_alerta_enviada(id_s, clave_mitad, plaga["nombre"])
                print(f"[MOTOR] ✅ Alerta de plaga (mitad) enviada: {plaga['nombre']}")

        # ----------------------------------------------------------
        # 3. REVISAR COSECHA
        # ----------------------------------------------------------
        dia_cosecha_ini = ciclo["cosecha_dia_inicio"]
        clave_cosecha   = f"cosecha_inicio_{dia_cosecha_ini}"

        if dias == dia_cosecha_ini and not database.alerta_ya_enviada(id_s, clave_cosecha):
            await bot_alerta.alerta_cosecha(
                cultivo     = cultivo,
                parcela     = parcela,
                descripcion = ciclo["humedad_cosecha"],
                dias        = dias
            )
            database.registrar_alerta_enviada(id_s, clave_cosecha, "Inicio cosecha")
            print(f"[MOTOR] ✅ Alerta de cosecha enviada.")

    print(f"[MOTOR] Revisión completada.\n")


# Test manual directo
if __name__ == "__main__":
    asyncio.run(revisar_calendario_agricola())