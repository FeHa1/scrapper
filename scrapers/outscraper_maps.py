"""
Scraper de Google Maps vía SerpApi.

Documentación: https://serpapi.com/google-maps-api
Free tier: 250 búsquedas/mes (non-commercial).

No requiere SDK — usa requests directamente.
"""

import logging
import os
import time
from typing import Optional

import requests

from config import (
    ACTIVE_ZONES,
    INSTRUMENTS,
    SERPAPI_KEY,
    ZONES,
)
from utils import build_record, extract_email, extract_instagram, has_contact

logger = logging.getLogger(__name__)

SERPAPI_ENDPOINT = "https://serpapi.com/search"
MAX_START = 100       # SerpApi recomienda no pasar de start=100 en Maps
RESULTS_PER_PAGE = 20
DELAY_SECONDS = 1.5   # pausa entre requests para no quemar rate limit


def get_api_key() -> Optional[str]:
    key = SERPAPI_KEY or os.getenv("SERPAPI_KEY", "")
    if not key:
        logger.error(
            "No se encontró la API key de SerpApi. "
            "Definila en config.py o como variable de entorno SERPAPI_KEY."
        )
    return key or None


def parse_serpapi_result(result: dict, instrumento: str) -> Optional[dict]:
    """
    Mapea un resultado crudo de SerpApi (local_results) a nuestro esquema estándar.

    Campos relevantes que devuelve SerpApi:
    - title, phone, website, address, rating
    - gps_coordinates (lat/lng)
    """
    nombre = result.get("title", "")
    if not nombre:
        return None

    telefono = result.get("phone", "") or ""
    website = result.get("website", "") or ""

    # SerpApi Maps no expone emails directamente — dejamos vacío
    email = ""

    # Instagram tampoco viene en Maps — dejamos vacío
    # (se puede enriquecer después visitando el website)
    instagram = ""

    direccion = result.get("address", "") or ""

    # Barrio: SerpApi no tiene campo borough, lo inferimos del address
    barrio = direccion.split(",")[0].strip() if direccion else ""

    rating = result.get("rating", "") or ""

    record = build_record(
        nombre=nombre,
        instrumento=instrumento,
        telefono=telefono,
        email=email,
        website=website,
        instagram=instagram,
        direccion=direccion,
        barrio=barrio,
        rating=str(rating),
        fuente="google_maps",
    )

    return record if has_contact(record) else None


def _fetch_page(query: str, ll: str, start: int, api_key: str) -> list[dict]:
    """
    Llama a SerpApi y devuelve los local_results de una página.
    ll es obligatorio para paginación (start > 0) según la doc oficial.
    """
    params = {
        "engine": "google_maps",
        "type": "search",
        "q": query,
        "ll": ll,
        "hl": "es",
        "gl": "ar",
        "start": start,
        "api_key": api_key,
    }

    try:
        resp = requests.get(SERPAPI_ENDPOINT, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.error(f"[SerpApi] Error HTTP en query {query!r} start={start}: {e}")
        return []
    except ValueError as e:
        logger.error(f"[SerpApi] Error parseando JSON en query {query!r}: {e}")
        return []

    if "error" in data:
        logger.error(f"[SerpApi] Error de API: {data['error']}")
        return []

    return data.get("local_results", [])


def scrape_google_maps(
    instruments: list[str] = None,
    zones: list[str] = None,
) -> list[dict]:
    """
    Busca docentes de música en Google Maps para cada combinación
    instrumento × zona, con paginación automática.

    Args:
        instruments: Lista de instrumentos. Default: INSTRUMENTS de config.
        zones: Lista de zonas como dicts con 'nombre' y 'll'. 
               Default: ACTIVE_ZONES de config.

    Returns:
        Lista de dicts normalizados.
    """
    api_key = get_api_key()
    if not api_key:
        return []

    instruments = instruments or INSTRUMENTS

    # Construir lista de zonas activas desde config
    if zones is None:
        zones = []
        for zone_key in ACTIVE_ZONES:
            zones.extend(ZONES.get(zone_key, []))

    records = []
    total_queries = len(instruments) * len(zones)
    query_count = 0

    for instrumento in instruments:
        for zona in zones:
            query_count += 1

            # zona puede ser dict {"nombre": ..., "ll": ...} o string legacy
            if isinstance(zona, dict):
                zona_nombre = zona.get("nombre", "")
                ll = zona.get("ll", "@-34.6037,-58.3816,12z")  # fallback: centro CABA
            else:
                zona_nombre = zona
                ll = "@-34.6037,-58.3816,12z"

            query = f"clases de {instrumento} {zona_nombre}"
            logger.info(f"[SerpApi {query_count}/{total_queries}] Buscando: {query!r}")

            zona_records = []
            start = 0

            # Paginación: hasta start=100 (6 páginas de 20)
            while start <= MAX_START:
                page_results = _fetch_page(query, ll, start, api_key)

                if not page_results:
                    break

                for item in page_results:
                    record = parse_serpapi_result(item, instrumento)
                    if record:
                        zona_records.append(record)

                logger.debug(f"  Página start={start}: {len(page_results)} resultados")

                # Si devolvió menos de 20, no hay más páginas
                if len(page_results) < RESULTS_PER_PAGE:
                    break

                start += RESULTS_PER_PAGE
                time.sleep(DELAY_SECONDS)

            logger.info(f"  → {len(zona_records)} contactos válidos")
            records.extend(zona_records)
            time.sleep(DELAY_SECONDS)

    logger.info(f"[SerpApi] Total registros válidos: {len(records)}")
    return records
