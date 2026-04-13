"""
config.py
Configuración centralizada del proyecto.
Cargá las API keys como variables de entorno para no hardcodearlas.

    export SERPAPI_KEY="tu_key_aqui"
    python main.py --instruments guitarra piano
"""

import os

# ── API Keys ───────────────────────────────────────────────────────────────────
SERPAPI_KEY: str = os.getenv("SERPAPI_KEY", "")   # https://serpapi.com/manage-api-key

# ── Comportamiento del scraper ─────────────────────────────────────────────────
DELAY_BETWEEN_REQUESTS: float = 1.5   # segundos entre requests (respetar rate limits)

OUTPUT_DIR: str = "output"
OUTPUT_FILE: str = "docentes_musica.csv"

# ── Columnas finales del CSV (en orden) ───────────────────────────────────────
CSV_COLUMNS: list[str] = [
    "nombre",
    "instrumento",
    "teléfono",
    "email",
    "website",
    "instagram",
    "dirección",
    "barrio",
    "rating",
    "fuente",
]
