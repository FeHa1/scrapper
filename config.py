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
    "ukelele",
    "teclado",
    "acordeón",
    "contrabajo",
    "viola",
    "oboe",
    "clarinete",
]

# ─── Zonas ──────────────────────────────────────────────────────────────────
ZONES = {
    "CABA": [
        "Buenos Aires, Argentina",
        # Podés agregar barrios específicos si querés más granularidad:
        # "Palermo, Buenos Aires, Argentina",
        # "Caballito, Buenos Aires, Argentina",
    ],
    "GBA_Norte": [
        "San Isidro, Buenos Aires, Argentina",
        "Vicente López, Buenos Aires, Argentina",
        "Tigre, Buenos Aires, Argentina",
    ],
    "GBA_Sur": [
        "Lanús, Buenos Aires, Argentina",
        "Lomas de Zamora, Buenos Aires, Argentina",
        "Quilmes, Buenos Aires, Argentina",
    ],
    "GBA_Oeste": [
        "Morón, Buenos Aires, Argentina",
        "La Matanza, Buenos Aires, Argentina",
        "Tres de Febrero, Buenos Aires, Argentina",
    ],
    "Córdoba": [
        "Córdoba, Argentina",
    ],
    "Rosario": [
        "Rosario, Santa Fe, Argentina",
    ],
}

# Zonas activas para esta corrida (modificar según necesidad)
ACTIVE_ZONES = ["CABA"]

# ─── Outscraper ─────────────────────────────────────────────────────────────
OUTSCRAPER_API_KEY = ""  # ← Poner tu API key acá o en variable de entorno

# Límite de resultados por query en Outscraper (free tier: ~500/mes)
OUTSCRAPER_RESULTS_PER_QUERY = 20

# ─── Scraping general ───────────────────────────────────────────────────────
REQUEST_DELAY_SECONDS = 2      # Pausa entre requests para no ser bloqueado
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
SUPERPROF_MAX_PAGES = 5        # Páginas a scrapear por instrumento

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
