"""
Configuración central del scraper de docentes de música.
Modificá este archivo para agregar instrumentos, zonas o fuentes nuevas.
"""

# ─── Instrumentos ───────────────────────────────────────────────────────────
INSTRUMENTS = [
    "guitarra",
    "piano",
    "batería",
    "canto",
    "bajo",
    "violín",
    "flauta",
    "saxofón",
    "trompeta",
    #"ukelele",
    "teclado",
    #"acordeón",
    #"contrabajo",
    #"viola",
    #"oboe",
    #"clarinete",
]

# ─── Zonas ──────────────────────────────────────────────────────────────────
# Cada zona es un dict con:
#   "nombre": se agrega al query de búsqueda (ej: "clases de guitarra Palermo")
#   "ll":     coordenadas GPS requeridas por SerpApi para paginación
#             formato: @latitud,longitud,zoomz
ZONES = {
    "CABA": [
        {"nombre": "Buenos Aires",   "ll": "@-34.6037,-58.3816,12z"},
        {"nombre": "Palermo",        "ll": "@-34.5885,-58.4317,14z"},
        {"nombre": "Caballito",      "ll": "@-34.6162,-58.4390,14z"},
        {"nombre": "Belgrano",       "ll": "@-34.5621,-58.4572,14z"},
        {"nombre": "San Telmo",      "ll": "@-34.6218,-58.3731,15z"},
        {"nombre": "Villa Urquiza",  "ll": "@-34.5772,-58.4894,14z"},
    ],
    "GBA_Norte": [
        {"nombre": "San Isidro",     "ll": "@-34.4708,-58.5169,13z"},
        {"nombre": "Vicente López",  "ll": "@-34.5262,-58.4788,13z"},
        {"nombre": "Tigre",          "ll": "@-34.4260,-58.5796,13z"},
    ],
    "GBA_Sur": [
        {"nombre": "Lanús",          "ll": "@-34.7006,-58.3958,13z"},
        {"nombre": "Lomas de Zamora","ll": "@-34.7612,-58.4054,13z"},
        {"nombre": "Quilmes",        "ll": "@-34.7206,-58.2540,13z"},
    ],
    "GBA_Oeste": [
        {"nombre": "Morón",          "ll": "@-34.6534,-58.6198,13z"},
        {"nombre": "La Matanza",     "ll": "@-34.7717,-58.5001,12z"},
        {"nombre": "Tres de Febrero","ll": "@-34.6059,-58.5614,13z"},
    ],
    "Córdoba": [
        {"nombre": "Córdoba",        "ll": "@-31.4201,-64.1888,12z"},
    ],
    "Rosario": [
        {"nombre": "Rosario",        "ll": "@-32.9468,-60.6393,12z"},
    ],
}

# Zonas activas para esta corrida (modificar según necesidad)
ACTIVE_ZONES = ["CABA"]

# ─── SerpApi ────────────────────────────────────────────────────────────────
import os

from dotenv import load_dotenv
load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "") 

# ─── Scraping general ───────────────────────────────────────────────────────
REQUEST_DELAY_SECONDS = 2
REQUEST_TIMEOUT_SECONDS = 15
MAX_RETRIES = 3

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-AR,es;q=0.9",
}

# ─── Superprof ──────────────────────────────────────────────────────────────
SUPERPROF_BASE_URL = "https://www.superprof.com.ar"
SUPERPROF_MAX_PAGES = 5

# ─── TusClases ──────────────────────────────────────────────────────────────
TUSCLASES_BASE_URL = "https://www.tusclases.com.ar"
TUSCLASES_MAX_PAGES = 5

# ─── Output ─────────────────────────────────────────────────────────────────
OUTPUT_DIR = "output"
OUTPUT_FILENAME = "docentes_musica.csv"

CSV_COLUMNS = [
    "nombre",
    "instrumento",
    "telefono",
    "email",
    "website",
    "instagram",
    "direccion",
    "barrio",
    "rating",
    "fuente",
]
