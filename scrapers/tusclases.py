"""
Scraper para TusClases Argentina (https://www.tusclases.com.ar).
URL pattern: /clases-musica/{instrumento}.aspx
Card selector: .itemv3
"""

import logging
import re
import requests
from bs4 import BeautifulSoup

from config import INSTRUMENTS, TUSCLASES_BASE_URL, TUSCLASES_MAX_PAGES
from utils import build_record, has_contact, safe_get

logger = logging.getLogger(__name__)

INSTRUMENT_SLUGS = {
    "guitarra": "guitarra", "piano": "piano", "batería": "bateria",
    "canto": "canto", "bajo": "bajo", "violín": "violin",
    "flauta": "flauta", "saxofón": "saxofon", "trompeta": "trompeta",
    "ukelele": "ukelele", "teclado": "teclado", "acordeón": "acordeon",
    "contrabajo": "contrabajo", "viola": "viola", "oboe": "oboe",
    "clarinete": "clarinete",
}


def parse_teacher_card(card, instrumento: str) -> dict | None:
    try:
        nombre = card.select_one(".username")
        nombre = nombre.get_text(strip=True) if nombre else ""
        if not nombre:
            return None

        # Barrio: segundo <span> dentro de .place
        barrio = ""
        place = card.select_one(".place")
        if place:
            spans = place.select("span")
            barrio = spans[-1].get_text(strip=True) if spans else ""

        # Rating
        rating = ""
        mark = card.select_one(".mark")
        if mark:
            match = re.search(r"[\d.,]+", mark.get_text(strip=True))
            rating = match.group(0) if match else ""

        # URL de perfil — está en data-link del card o en el <a class="title">
        profile_url = card.get("data-link", "")
        if not profile_url:
            a = card.select_one("a.title")
            profile_url = a.get("href", "") if a else ""
        if profile_url and not profile_url.startswith("http"):
            profile_url = TUSCLASES_BASE_URL + profile_url

        return build_record(
            nombre=nombre,
            instrumento=instrumento,
            website=profile_url,
            barrio=barrio,
            rating=rating,
            fuente="tusclases",
        )

    except Exception as e:
        logger.debug(f"[TusClases] Error parseando card: {e}")
        return None


def scrape_instrument_bs4(instrumento: str, session: requests.Session) -> list[dict]:
    slug = INSTRUMENT_SLUGS.get(instrumento, instrumento.lower())
    records = []

    for page in range(1, TUSCLASES_MAX_PAGES + 1):
        if page == 1:
            url = f"{TUSCLASES_BASE_URL}/clases-musica/{slug}.aspx"
        else:
            url = f"{TUSCLASES_BASE_URL}/clases-musica/{slug}.aspx?pagina={page}"

        logger.info(f"[TusClases] {instrumento} — página {page}: {url}")
        resp = safe_get(url, session=session)
        if resp is None:
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select(".itemv3")

        if not cards:
            logger.info(f"[TusClases] Sin cards en página {page}, deteniendo.")
            break

        logger.info(f"[TusClases] {len(cards)} cards en página {page}")
        for card in cards:
            record = parse_teacher_card(card, instrumento)
            if record:
                records.append(record)
                logger.debug(f"  ✓ {record['nombre']} — {record['barrio']}")

        if not soup.select_one("a[rel='next']"):
            logger.info(f"[TusClases] Última página para {instrumento}.")
            break

    return records


def scrape_tusclases(instruments: list[str] = None) -> list[dict]:
    instruments = instruments or INSTRUMENTS
    all_records = []
    session = requests.Session()
    for instrumento in instruments:
        all_records.extend(scrape_instrument_bs4(instrumento, session))
    logger.info(f"[TusClases] Total: {len(all_records)}")
    return all_records
