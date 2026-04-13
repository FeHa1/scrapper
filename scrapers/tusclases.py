"""
Scraper para TusClases Argentina (https://www.tusclases.com.ar).
URL pattern: /clases-musica/{instrumento}.aspx
"""

import logging
import re
import time

import requests
from bs4 import BeautifulSoup

from config import (
    INSTRUMENTS,
    REQUEST_DELAY_SECONDS,
    TUSCLASES_BASE_URL,
    TUSCLASES_MAX_PAGES,
)
from utils import build_record, extract_email, extract_instagram, has_contact, safe_get

logger = logging.getLogger(__name__)

USAR_PLAYWRIGHT = False

INSTRUMENT_SLUGS = {
    "guitarra": "guitarra",
    "piano": "piano",
    "batería": "bateria",
    "canto": "canto",
    "bajo": "bajo",
    "violín": "violin",
    "flauta": "flauta",
    "saxofón": "saxofon",
    "trompeta": "trompeta",
    "ukelele": "ukelele",
    "teclado": "teclado",
    "acordeón": "acordeon",
    "contrabajo": "contrabajo",
    "viola": "viola",
    "oboe": "oboe",
    "clarinete": "clarinete",
}

TUSCLASES_CATEGORY = "clases-musica"


def parse_teacher_card(card, instrumento: str) -> dict | None:
    try:
        nombre_el = card.select_one(
            ".teacher-name, .tutor__name, h2, h3, "
            "[class*='name'], [data-testid='teacher-name']"
        )
        nombre = nombre_el.get_text(strip=True) if nombre_el else ""
        if not nombre:
            return None

        bio_el = card.select_one(
            ".teacher-bio, .tutor__description, .description, "
            "[class*='description'], [class*='bio']"
        )
        bio_text = bio_el.get_text(" ", strip=True) if bio_el else ""

        email = extract_email(bio_text) or ""
        instagram = extract_instagram(bio_text) or ""

        website = ""
        for a in card.find_all("a", href=True):
            href = a["href"]
            if "tusclases" not in href and href.startswith("http"):
                website = href
                break

        phone = ""
        phone_el = card.select_one(
            "[class*='phone'], [class*='whatsapp'], [href^='tel:'], [href^='https://wa.me']"
        )
        if phone_el:
            href = phone_el.get("href", "")
            match = re.search(r"[\d]{8,}", href)
            phone = match.group(0) if match else phone_el.get_text(strip=True)

        rating_el = card.select_one("[class*='rating'], [class*='stars'], .score")
        rating = ""
        if rating_el:
            match = re.search(r"[\d.,]+", rating_el.get_text(strip=True))
            rating = match.group(0) if match else ""

        location_el = card.select_one("[class*='location'], [class*='city'], [class*='zone']")
        barrio = location_el.get_text(strip=True) if location_el else ""

        profile_link = card.select_one("a[href*='.aspx'], a[href*='/profesor/'], a[href*='/tutor/']")
        profile_url = ""
        if profile_link:
            href = profile_link.get("href", "")
            profile_url = href if href.startswith("http") else TUSCLASES_BASE_URL + href

        record = build_record(
            nombre=nombre,
            instrumento=instrumento,
            telefono=phone,
            email=email,
            website=website or profile_url,
            instagram=instagram,
            barrio=barrio,
            rating=rating,
            fuente="tusclases",
        )
        return record if has_contact(record) else None

    except Exception as e:
        logger.debug(f"[TusClases] Error parseando card: {e}")
        return None


def scrape_instrument_bs4(instrumento: str, session: requests.Session) -> list[dict]:
    slug = INSTRUMENT_SLUGS.get(instrumento, instrumento.lower())
    records = []

    for page in range(1, TUSCLASES_MAX_PAGES + 1):
        if page == 1:
            url = f"{TUSCLASES_BASE_URL}/{TUSCLASES_CATEGORY}/{slug}.aspx"
        else:
            url = f"{TUSCLASES_BASE_URL}/{TUSCLASES_CATEGORY}/{slug}.aspx?pagina={page}"

        logger.info(f"[TusClases] {instrumento} — página {page}: {url}")

        resp = safe_get(url, session=session)
        if resp is None:
            break

        soup = BeautifulSoup(resp.text, "html.parser")

        cards = soup.select(
            ".teacher-card, .tutor-card, .profesor-card, "
            "article.teacher, article.tutor, "
            "[class*='TeacherCard'], [class*='TutorCard'], "
            "li[class*='teacher'], li[class*='tutor']"
        )

        if not cards:
            cards = [el for el in soup.find_all(["article", "li"]) if el.find(["h2", "h3"])]

        if not cards:
            logger.warning(
                f"[TusClases] No se encontraron cards en página {page}. "
                "Activar USAR_PLAYWRIGHT=True si el problema persiste."
            )
            # Dump HTML para debugging
            logger.debug(f"[TusClases] HTML snippet: {soup.prettify()[:2000]}")
            break

        for card in cards:
            record = parse_teacher_card(card, instrumento)
            if record:
                records.append(record)
                logger.debug(f"  ✓ {record['nombre']}")

        next_link = soup.select_one("a[rel='next'], .pagination a.next, a[aria-label='Siguiente']")
        if not next_link:
            logger.info(f"[TusClases] Sin más páginas para {instrumento}.")
            break

    return records


def scrape_instrument_playwright(instrumento: str) -> list[dict]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("Playwright no instalado.")
        return []

    slug = INSTRUMENT_SLUGS.get(instrumento, instrumento.lower())
    records = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(locale="es-AR")
        page = context.new_page()

        for page_num in range(1, TUSCLASES_MAX_PAGES + 1):
            if page_num == 1:
                url = f"{TUSCLASES_BASE_URL}/{TUSCLASES_CATEGORY}/{slug}.aspx"
            else:
                url = f"{TUSCLASES_BASE_URL}/{TUSCLASES_CATEGORY}/{slug}.aspx?pagina={page_num}"

            logger.info(f"[TusClases/Playwright] {instrumento} — pág {page_num}: {url}")

            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)

                html = page.content()
                soup = BeautifulSoup(html, "html.parser")

                cards = soup.select(
                    ".teacher-card, .tutor-card, article.teacher, [class*='TeacherCard']"
                )
                if not cards:
                    cards = [el for el in soup.find_all(["article", "li"]) if el.find(["h2", "h3"])]

                if not cards:
                    break

                for card in cards:
                    record = parse_teacher_card(card, instrumento)
                    if record:
                        records.append(record)

                if not soup.select_one("a[rel='next'], .pagination a.next"):
                    break

            except Exception as e:
                logger.error(f"[TusClases/Playwright] Error en {url}: {e}")
                break

        browser.close()

    return records


def scrape_tusclases(instruments: list[str] = None) -> list[dict]:
    instruments = instruments or INSTRUMENTS
    all_records = []

    if USAR_PLAYWRIGHT:
        for instrumento in instruments:
            records = scrape_instrument_playwright(instrumento)
            all_records.extend(records)
    else:
        session = requests.Session()
        for instrumento in instruments:
            records = scrape_instrument_bs4(instrumento, session)
            all_records.extend(records)

    logger.info(f"[TusClases] Total registros válidos: {len(all_records)}")
    return all_records
