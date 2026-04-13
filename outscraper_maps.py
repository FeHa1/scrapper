"""
Scraper de Google Maps vía Outscraper SDK.

Documentación: https://outscraper.com/python-client/
Free tier: ~500 resultados/mes.

Instalar: pip install outscraper
"""

import logging
import os
from typing import Optional

from config import (
    ACTIVE_ZONES,
    INSTRUMENTS,
    OUTSCRAPER_API_KEY,
    OUTSCRAPER_RESULTS_PER_QUERY,
    ZONES,
)
from utils import build_record, extract_email, extract_instagram, has_contact

logger = logging.getLogger(__name__)


def get_api_key() -> Optional[str]:
    key = OUTSCRAPER_API_KEY or os.getenv("OUTSCRAPER_API_KEY", "")
    if not key:
        logger.error(
            "No se encontró la API key de Outscraper. "
            "Definila en config.py o como variable de entorno OUTSCRAPER_API_KEY."
        )
    return key or None


def parse_outscraper_result(result: dict, instrumento: str) -> Optional[dict]:
    """
    Mapea un resultado crudo de Outscraper a nuestro esquema estándar.

    Campos relevantes que devuelve Outscraper:
    - name, phone, full_address, site, rating, instagram, emails_from_website
    - borough (barrio/localidad)
    - social_networks (dict con redes sociales)
    """
    nombre = result.get("name", "")
    if not nombre:
        return None

    # Teléfono
    telefono = result.get("phone", "") or ""

    # Email: Outscraper a veces incluye emails_from_website como lista
    emails = result.get("emails_from_website") or []
    if isinstance(emails, list):
        email = emails[0] if emails else ""
    else:
        email = extract_email(str(emails)) or ""

    # Website
    website = result.get("site", "") or ""

    # Instagram: puede venir en social_networks o como campo directo
    instagram = ""
    social = result.get("social_networks") or {}
    if isinstance(social, dict):
        instagram = social.get("instagram", "") or ""
    if not instagram:
        instagram = result.get("instagram", "") or ""
    instagram = extract_instagram(instagram) or instagram

    # Dirección
    direccion = result.get("full_address", "") or ""

    # Barrio / localidad
    barrio = result.get("borough", "") or result.get("city", "") or ""

    # Rating
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


def scrape_google_maps(
    instruments: list[str] = None,
    zones: list[str] = None,
) -> list[dict]:
    """
    Busca docentes de música en Google Maps para cada combinación
    instrumento × zona.

    Args:
        instruments: Lista de instrumentos. Default: INSTRUMENTS de config.
        zones: Lista de zonas en texto libre. Default: ACTIVE_ZONES de config.

    Returns:
        Lista de dicts normalizados.
    """
    try:
        from outscraper import ApiClient
    except ImportError:
        logger.error("Outscraper SDK no instalado. Ejecutá: pip install outscraper")
        return []

    api_key = get_api_key()
    if not api_key:
        return []

    client = ApiClient(api_keys=[api_key])

    instruments = instruments or INSTRUMENTS
    if zones is None:
        zones = []
        for zone_key in ACTIVE_ZONES:
            zones.extend(ZONES.get(zone_key, []))

    records = []

    for instrumento in instruments:
        for zona in zones:
            query = f"clases de {instrumento} {zona}"
            logger.info(f"[Outscraper] Buscando: {query!r}")

            try:
                results = client.google_maps_search(
                    [query],
                    limit=OUTSCRAPER_RESULTS_PER_QUERY,
                    language="es",
                    region="AR",
                    dropDuplicates=True,
                )
            except Exception as e:
                logger.error(f"[Outscraper] Error en query {query!r}: {e}")
                continue

            # Outscraper devuelve lista de listas
            for result_group in results:
                if not isinstance(result_group, list):
                    result_group = [result_group]
                for item in result_group:
                    if not isinstance(item, dict):
                        continue
                    record = parse_outscraper_result(item, instrumento)
                    if record:
                        records.append(record)
                        logger.debug(f"  ✓ {record['nombre']}")

    logger.info(f"[Outscraper] Total registros válidos: {len(records)}")
    return records
