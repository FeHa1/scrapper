"""
Scraper para Superprof Argentina (https://www.superprof.com.ar).

Estrategia:
- Superprof renderiza el listado de profesores con SSR (HTML estático para los
  cards principales), así que BeautifulSoup suele alcanzar.
- Si la paginación falla o los datos no aparecen, activar USAR_PLAYWRIGHT=True
  para usar Playwright en modo headless.

Instalar dependencias:
    pip install requests beautifulsoup4
    # Opcional para JS dinámico:
    pip install playwright && playwright install chromium
"""

import logging
import re
import time

import requests
from bs4 import BeautifulSoup

from config import (
    INSTRUMENTS,
    REQUEST_DELAY_SECONDS,
    SUPERPROF_BASE_URL,
    SUPERPROF_MAX_PAGES,
)
from utils import build_record, extract_email, extract_instagram, has_contact, safe_get

logger = logging.getLogger(__name__)

# ─── Configuración ────────────────────────────────────────────────────────────

# Cambiar a True si BeautifulSoup no captura resultados (JS dinámico)
USAR_PLAYWRIGHT = False

# Mapa instrumento → slug de URL en Superprof
INSTRUMENT_SLUGS = {
    "guitarra": "clases-guitarra",
    "piano": "clases-piano",
    "batería": "clases-bateria",
    "canto": "clases-canto",
    "bajo": "clases-bajo",
    "violín": "clases-violin",
    "flauta": "clases-flauta",
    "saxofón": "clases-saxofon",
    "trompeta": "clases-trompeta",
    "ukelele": "clases-ukelele",
    "teclado": "clases-teclado",
    "acordeón": "clases-acordeon",
    "contrabajo": "clases-contrabajo",
    "viola": "clases-viola",
    "oboe": "clases-oboe",
    "clarinete": "clases-clarinete",
}


# ─── Parser HTML ──────────────────────────────────────────────────────────────

def parse_teacher_card(card, instrumento: str) -> dict | None:
    """
    Extrae datos de un card de profesor del HTML de Superprof.
    La estructura puede cambiar — revisar selectores si el scraper falla.
    """
    try:
        # Nombre
        nombre_el = card.select_one(".ProfileCard__name, h2.teacher-name, .tutor-name, [data-testid='tutor-name']")
        nombre = nombre_el.get_text(strip=True) if nombre_el else ""
        if not nombre:
            # Fallback genérico
            nombre_el = card.find(["h2", "h3"])
            nombre = nombre_el.get_text(strip=True) if nombre_el else ""

        if not nombre:
            return None

        # Descripción / bio (donde pueden estar datos de contacto)
        desc_el = card.select_one(".ProfileCard__description, .tutor-description, .teacher-bio")
        desc_text = desc_el.get_text(" ", strip=True) if desc_el else ""

        # Email desde descripción (raro que lo pongan, pero por si acaso)
        email = extract_email(desc_text) or ""

        # Instagram desde descripción o atributos
        instagram = extract_instagram(desc_text) or ""

        # Website: algunos teachers ponen links
        website = ""
        for a in card.find_all("a", href=True):
            href = a["href"]
            if "superprof" not in href and href.startswith("http"):
                website = href
                break

        # Rating
        rating_el = card.select_one(".rating, .star-rating, [data-testid='rating'], .ProfileCard__rating")
        rating = ""
        if rating_el:
            rating_text = rating_el.get_text(strip=True)
            match = re.search(r"[\d.,]+", rating_text)
            rating = match.group(0) if match else ""

        # Barrio / ubicación
        location_el = card.select_one(
            ".ProfileCard__location, .teacher-location, .location, [data-testid='location']"
        )
        barrio = location_el.get_text(strip=True) if location_el else ""

        # URL de perfil → podría scrapear más datos en segunda pasada
        profile_link = card.select_one("a[href*='/profesor/'], a[href*='/tutor/']")
        profile_url = ""
        if profile_link:
            href = profile_link.get("href", "")
            profile_url = href if href.startswith("http") else SUPERPROF_BASE_URL + href

        record = build_record(
            nombre=nombre,
            instrumento=instrumento,
            email=email,
            website=website or profile_url,
            instagram=instagram,
            barrio=barrio,
            rating=rating,
            fuente="superprof",
        )
        return record if has_contact(record) else None

    except Exception as e:
        logger.debug(f"[Superprof] Error parseando card: {e}")
        return None


# ─── Scraping con Requests + BeautifulSoup ────────────────────────────────────

def scrape_instrument_bs4(instrumento: str, session: requests.Session) -> list[dict]:
    """Scrapea todas las páginas para un instrumento con BS4."""
    slug = INSTRUMENT_SLUGS.get(instrumento)
    if not slug:
        logger.warning(f"[Superprof] Sin slug para {instrumento!r}, intentando URL genérica")
        slug = f"clases-{instrumento.lower().replace(' ', '-')}"

    records = []

    for page in range(1, SUPERPROF_MAX_PAGES + 1):
        if page == 1:
            url = f"{SUPERPROF_BASE_URL}/{slug}/"
        else:
            url = f"{SUPERPROF_BASE_URL}/{slug}/{page}/"

        logger.info(f"[Superprof] {instrumento} — página {page}: {url}")

        resp = safe_get(url, session=session)
        if resp is None:
            break

        soup = BeautifulSoup(resp.text, "html.parser")

        # Selectores de cards (Superprof actualiza su HTML con frecuencia)
        cards = soup.select(
            ".ProfileCard, .teacher-card, .tutor-card, "
            "article.teacher, [data-testid='tutor-card'], "
            "li.tutor-item"
        )

        if not cards:
            logger.warning(
                f"[Superprof] No se encontraron cards en {url}. "
                "Puede que la estructura haya cambiado o haya JS dinámico. "
                "Activá USAR_PLAYWRIGHT=True si el problema persiste."
            )
            # Intentar con selectores más amplios
            cards = soup.find_all("article") or soup.find_all("li", class_=re.compile("teacher|tutor|profesor"))

        if not cards:
            logger.info(f"[Superprof] Sin más resultados en página {page}, deteniendo.")
            break

        for card in cards:
            record = parse_teacher_card(card, instrumento)
            if record:
                records.append(record)
                logger.debug(f"  ✓ {record['nombre']}")

        # Verificar si hay página siguiente
        next_btn = soup.select_one("a[rel='next'], .pagination .next, a.next-page")
        if not next_btn:
            logger.info(f"[Superprof] No hay más páginas para {instrumento}.")
            break

    return records


# ─── Scraping con Playwright ──────────────────────────────────────────────────

def scrape_instrument_playwright(instrumento: str) -> list[dict]:
    """
    Alternativa con Playwright para cuando Superprof renderiza con JS.
    Requiere: pip install playwright && playwright install chromium
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("Playwright no instalado. Ejecutá: pip install playwright && playwright install chromium")
        return []

    slug = INSTRUMENT_SLUGS.get(instrumento, f"clases-{instrumento.lower()}")
    records = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(locale="es-AR")
        page = context.new_page()

        for page_num in range(1, SUPERPROF_MAX_PAGES + 1):
            url = f"{SUPERPROF_BASE_URL}/{slug}/" if page_num == 1 else f"{SUPERPROF_BASE_URL}/{slug}/{page_num}/"
            logger.info(f"[Superprof/Playwright] {instrumento} — página {page_num}: {url}")

            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
                time.sleep(REQUEST_DELAY_SECONDS)

                html = page.content()
                soup = BeautifulSoup(html, "html.parser")
                cards = soup.select(".ProfileCard, .teacher-card, .tutor-card, article.teacher")

                if not cards:
                    logger.info(f"[Superprof/Playwright] Sin cards en página {page_num}.")
                    break

                for card in cards:
                    record = parse_teacher_card(card, instrumento)
                    if record:
                        records.append(record)

                next_btn = soup.select_one("a[rel='next'], .pagination .next")
                if not next_btn:
                    break

            except Exception as e:
                logger.error(f"[Superprof/Playwright] Error en {url}: {e}")
                break

        browser.close()

    return records


# ─── Entry point ──────────────────────────────────────────────────────────────

def scrape_superprof(instruments: list[str] = None) -> list[dict]:
    """
    Scrapea Superprof para todos los instrumentos dados.
    Elige BS4 o Playwright según USAR_PLAYWRIGHT.
    """
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

    logger.info(f"[Superprof] Total registros válidos: {len(all_records)}")
    return all_records
