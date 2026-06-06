# database.py
import sqlite3
from datetime import date, datetime, timedelta

DB_NAME = "agricola.db"

# ==============================================================
# DEFINICIÓN DE CICLOS AGRÍCOLAS (Basado en Calendario Sinaloa)
# ==============================================================
CICLOS_AGRICOLAS = {
    "maiz": {
        "nombre": "Maíz Blanco",
        "duracion_dias": 210,       # ~7 meses hasta cosecha
        "riegos": [
            {"dia": 0,   "nombre": "Riego de Presiembra", "descripcion": "Inunda el terreno para acumular humedad profunda (tierra venida)."},
            {"dia": 25,  "nombre": "1er Riego de Auxilio", "descripcion": "Primera aplicación de auxilio, monitorear germinación."},
            {"dia": 55,  "nombre": "2do Riego de Auxilio", "descripcion": "Etapa vegetativa activa. Vigilar Gusano Cogollero."},
            {"dia": 85,  "nombre": "3er Riego de Auxilio", "descripcion": "Fase crítica: inicio de jiloteo (aparece el pelo de la mazorca)."},
            {"dia": 110, "nombre": "4to Riego de Auxilio", "descripcion": "Llenado de grano. JAMÁS debe faltar agua en esta etapa."},
        ],
        "plagas": [
            {"dia_inicio": 10, "dia_fin": 60,  "nombre": "Gusano Cogollero", "descripcion": "Ataca la etapa vegetativa temprana. Revisa el cogollo diariamente. Aplica insecticida si hay daño > 15%."},
            {"dia_inicio": 150,"dia_fin": 210, "nombre": "Araña Roja / Gusano Elotero", "descripcion": "Presionan al final del ciclo cuando el ambiente se vuelve seco y caluroso. Monitorea la parte inferior de las hojas."},
        ],
        "cosecha_dia_inicio": 180,
        "cosecha_dia_fin": 210,
        "humedad_cosecha": "Entre 14% y 16% de humedad del grano para evitar castigos en bodega.",
    },
    "tomate": {
        "nombre": "Tomate / Hortalizas",
        "duracion_dias": 180,
        "riegos": [
            {"dia": 0,  "nombre": "Riego Trasplante", "descripcion": "Riego por goteo al momento del trasplante. Mantener suelo a capacidad de campo."},
            {"dia": 2,  "nombre": "Riego Diario/2 días", "descripcion": "Con goteo: aplicaciones diarias o cada 2 días en dosis milimétricas. NUNCA saturar."},
            {"dia": 30, "nombre": "Revisión Humedad", "descripcion": "Verificar que el suelo esté constantemente húmedo pero no saturado (evitar pudrición de raíces)."},
        ],
        "plagas": [
            {"dia_inicio": 0,  "dia_fin": 60,  "nombre": "Mosquita Blanca (Bemisia tabaci) y Trips", "descripcion": "CRÍTICO desde el trasplante. Transmiten virus que enrollan y detienen la planta. Colocar trampas amarillas."},
            {"dia_inicio": 100,"dia_fin": 150, "nombre": "Rebrote Mosquita Blanca", "descripcion": "Poblaciones explotan con el calor de feb-marzo. Aumentar monitoreo y rotación de insecticidas."},
        ],
        "cosecha_dia_inicio": 90,
        "cosecha_dia_fin": 180,
        "humedad_cosecha": "Cosecha manual escalonada. Múltiples cortes a medida que los tomates maduran.",
    },
    "frijol": {
        "nombre": "Frijol Azufrado",
        "duracion_dias": 120,
        "riegos": [
            {"dia": 0,  "nombre": "Riego de Presiembra", "descripcion": "Único riego pesado. La planta NO tolera exceso de agua."},
            {"dia": 30, "nombre": "1er Riego de Auxilio (si necesario)", "descripcion": "Solo si el suelo lo requiere. Máximo 1-2 auxilios o la planta se pudre."},
            {"dia": 60, "nombre": "2do Riego de Auxilio (máximo)", "descripcion": "Último riego posible. Evalúa humedad del suelo antes de aplicar."},
        ],
        "plagas": [
            {"dia_inicio": 0, "dia_fin": 30, "nombre": "Mosquita Blanca y Minador de la Hoja", "descripcion": "Activos en los primeros 30 días. Monitoreo intensivo en etapa inicial."},
        ],
        "cosecha_dia_inicio": 100,
        "cosecha_dia_fin": 120,
        "humedad_cosecha": "Se arranca la planta, se enchoriza (hileras a secar) y luego pasa trilladora.",
    },
    "garbanzo": {
        "nombre": "Garbanzo Blanco Sinaloa",
        "duracion_dias": 130,
        "riegos": [
            {"dia": 0,  "nombre": "Riego de Presiembra", "descripcion": "Único riego obligatorio. Si la tierra retiene bien humedad puede no necesitar auxilios."},
            {"dia": 50, "nombre": "Riego de Auxilio Ligero (opcional)", "descripcion": "Solo si el suelo no retiene bien la humedad. Evalúa antes de aplicar."},
        ],
        "plagas": [
            {"dia_inicio": 70, "dia_fin": 110, "nombre": "Gusano de la Cápsula (Heliothis)", "descripcion": "Ataca cuando se forma el grano, perfora la vaina. Monitoreo diario en etapa de formación."},
        ],
        "cosecha_dia_inicio": 110,
        "cosecha_dia_fin": 130,
        "humedad_cosecha": "Trillado mecánico cuando la vaina esté completamente seca.",
    },
}

# ==============================================================
# FUNCIONES DE BASE DE DATOS
# ==============================================================

def inicializar_db():
    """Crea la base de datos y todas las tablas necesarias."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Tabla principal de siembras
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS siembras (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            cultivo         TEXT NOT NULL,
            cultivo_tipo    TEXT NOT NULL,
            fecha_siembra   DATE NOT NULL,
            fecha_fin       DATE NOT NULL,
            parcela         TEXT DEFAULT 'Sin nombre',
            superficie_ha   REAL DEFAULT 0.0,
            notas           TEXT DEFAULT '',
            estado          TEXT DEFAULT 'activo',
            fecha_registro  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabla de alertas enviadas (para no repetir)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alertas_enviadas (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            siembra_id      INTEGER NOT NULL,
            tipo_alerta     TEXT NOT NULL,
            descripcion     TEXT,
            fecha_envio     DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (siembra_id) REFERENCES siembras(id)
        )
    ''')

    conn.commit()
    conn.close()
    print("Base de datos inicializada correctamente.")


def registrar_siembra(cultivo_nombre, cultivo_tipo, fecha_siembra_str, parcela="Sin nombre", superficie=0.0, notas=""):
    """Guarda un nuevo ciclo agrícola con fecha de fin calculada automáticamente."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    fecha_siembra = datetime.strptime(fecha_siembra_str, "%Y-%m-%d").date()
    duracion = CICLOS_AGRICOLAS.get(cultivo_tipo, {}).get("duracion_dias", 180)
    fecha_fin = fecha_siembra + timedelta(days=duracion)

    cursor.execute(
        "INSERT INTO siembras (cultivo, cultivo_tipo, fecha_siembra, fecha_fin, parcela, superficie_ha, notas) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (cultivo_nombre, cultivo_tipo, fecha_siembra_str, str(fecha_fin), parcela, superficie, notas)
    )
    conn.commit()
    nuevo_id = cursor.lastrowid
    conn.close()
    return nuevo_id, str(fecha_fin)


def obtener_siembras_activas():
    """Recupera todos los cultivos activos con todos sus datos."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, cultivo, cultivo_tipo, fecha_siembra, fecha_fin, parcela, superficie_ha, notas
        FROM siembras
        WHERE estado = 'activo'
        ORDER BY fecha_siembra DESC
    """)
    resultados = cursor.fetchall()
    conn.close()
    return resultados


def obtener_todas_siembras():
    """Recupera todas las siembras para el calendario."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, cultivo, cultivo_tipo, fecha_siembra, fecha_fin, parcela, estado
        FROM siembras
        ORDER BY fecha_siembra DESC
    """)
    resultados = cursor.fetchall()
    conn.close()
    return resultados


def alerta_ya_enviada(siembra_id, tipo_alerta):
    """Verifica si ya se envió una alerta específica para evitar duplicados."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM alertas_enviadas WHERE siembra_id = ? AND tipo_alerta = ?",
        (siembra_id, tipo_alerta)
    )
    resultado = cursor.fetchone()
    conn.close()
    return resultado is not None


def registrar_alerta_enviada(siembra_id, tipo_alerta, descripcion=""):
    """Registra que una alerta fue enviada para no repetirla."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO alertas_enviadas (siembra_id, tipo_alerta, descripcion) VALUES (?, ?, ?)",
        (siembra_id, tipo_alerta, descripcion)
    )
    conn.commit()
    conn.close()


def cerrar_siembra(siembra_id):
    """Marca una siembra como completada."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE siembras SET estado = 'completado' WHERE id = ?", (siembra_id,))
    conn.commit()
    conn.close()