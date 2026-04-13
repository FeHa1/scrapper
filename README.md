# 🎸 Scraper de Docentes de Música — Argentina

Herramienta de scraping para construir una base de contactos de docentes de música en Argentina, orientada a outreach para SaaS de gestión pedagógica musical.

## Estructura del proyecto

```
music_scraper/
├── main.py                  # Orquestador principal (entry point)
├── config.py                # ← Configuración central (instrumentos, zonas, API keys)
├── requirements.txt
├── scrapers/
│   ├── outscraper_maps.py   # Google Maps vía Outscraper SDK
│   ├── superprof.py         # Superprof Argentina (BS4 + Playwright opcional)
│   └── tusclases.py         # TusClases Argentina (BS4 + Playwright opcional)
├── utils/
│   └── helpers.py           # Normalización, dedup, filtrado, CSV, HTTP
└── output/
    └── docentes_musica.csv  # Output generado
```

## Setup

```bash
# 1. Crear entorno virtual
python -m venv venv
source venv/bin/activate      # Mac/Linux
venv\Scripts\activate         # Windows

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar API key de Outscraper
# Opción A: editar config.py
OUTSCRAPER_API_KEY = "tu_api_key_aqui"

# Opción B: variable de entorno (recomendado)
export OUTSCRAPER_API_KEY="tu_api_key_aqui"
```

## Uso

```bash
# Corrida completa (todas las fuentes, todos los instrumentos, CABA)
python main.py

# Prueba rápida sin API key de Outscraper
python main.py --skip-maps --instruments guitarra piano

# Instrumentos específicos
python main.py --instruments guitarra canto piano --skip-maps

# Combinar con corrida anterior (no pierde registros viejos)
python main.py --merge-existing

# Ver logs detallados
python main.py --verbose

# Nombre de archivo de salida custom
python main.py --output docentes_cordoba.csv
```

## Agregar una nueva fuente

1. Crear `scrapers/nueva_fuente.py` con una función `scrape_nueva_fuente(instruments) -> list[dict]`
2. Cada record debe usar `build_record(...)` de `utils`
3. Importar y agregar al pipeline en `main.py`

## Agregar nuevas zonas

En `config.py`, agregar a `ZONES` y a `ACTIVE_ZONES`:

```python
ZONES = {
    ...
    "Mendoza": ["Mendoza, Argentina"],
}
ACTIVE_ZONES = ["CABA", "Mendoza"]
```

## Playwright (JS dinámico)

Si Superprof o TusClases cambian su estructura y BeautifulSoup deja de funcionar:

```bash
pip install playwright
playwright install chromium
```

Luego en `scrapers/superprof.py` o `scrapers/tusclases.py`, cambiar:
```python
USAR_PLAYWRIGHT = True
```

## Columnas del CSV

| Columna     | Descripción                              |
|-------------|------------------------------------------|
| nombre      | Nombre del docente                       |
| instrumento | Instrumento que enseña                   |
| telefono    | Solo dígitos (normalizado)               |
| email       | Email de contacto                        |
| website     | Sitio web o URL de perfil                |
| instagram   | Handle con @ o vacío                     |
| direccion   | Dirección completa                       |
| barrio      | Barrio o localidad                       |
| rating      | Puntuación (si disponible)               |
| fuente      | `google_maps` / `superprof` / `tusclases`|

## Criterio de inclusión

Un registro se incluye **solo si tiene al menos uno** de: teléfono, email, website, instagram.

## Deduplicación

Se deduplicada por `nombre normalizado + teléfono`. Si no hay teléfono, por `nombre + instrumento`.

## Notas sobre rate limits

- **Outscraper free tier**: ~500 resultados/mes. Con 16 instrumentos × 1 zona × 20 resultados = 320 queries de resultado. Suficiente para CABA completo.
- **Superprof / TusClases**: El delay de 2 segundos entre requests evita bloqueos. Aumentar `REQUEST_DELAY_SECONDS` en `config.py` si se detectan 429 o bloqueos.
