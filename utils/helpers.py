"""
Utilidades compartidas: normalización, deduplicación, filtrado y exportación CSV.
"""

import re
import time
import logging
import unicodedata
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

from config import (
    CSV_COLUMNS,
    OUTPUT_DIR,
    OUTPUT_FILENAME,
    REQUEST_DELAY_SECONDS,
    REQUEST_TIMEOUT_SECONDS,
    MAX_RETRIES,
    HEADERS,
)

logger = logging.getLogger(__name__)


# ─── Normalización ──────────────────────────────────────────────────────────

def normalize_text(text: str) -> str:
    """Lowercase + sin acentos + strip, para comparaciones."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    return ascii_str.lower().strip()


def normalize_phone(phone: str) -> str:
    """Deja solo dígitos, útil para comparar duplicados."""
    if not phone:
        return ""
    return re.sub(r"\D", "", str(phone))


def extract_instagram(text: str) -> Optional[str]:
    """Extrae handle de Instagram de una URL o texto libre."""
    if not text:
        return None
    # URL completa → sacar handle
    match = re.search(r"instagram\.com/([A-Za-z0-9_.]+)", text)
    if match:
        return "@" + match.group(1)
    # @handle suelto
    match = re.search(r"@([A-Za-z0-9_.]+)", text)
    if match:
        return "@" + match.group(1)
    return None


def extract_email(text: str) -> Optional[str]:
    """Extrae primer email encontrado en un texto."""
    if not text:
        return None
    match = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
    return match.group(0) if match else None


# ─── Filtrado ────────────────────────────────────────────────────────────────

def has_contact(row: dict) -> bool:
    """
    Regla de negocio: incluir el registro solo si tiene AL MENOS UN dato
    de contacto (teléfono, email, website o instagram).
    """
    contact_fields = ["telefono", "email", "website", "instagram"]
    return any(bool(row.get(f)) for f in contact_fields)


# ─── Deduplicación ──────────────────────────────────────────────────────────

def deduplicate(records: list[dict]) -> list[dict]:
    """
    Elimina duplicados entre fuentes.
    Criterio: mismo nombre normalizado + mismo teléfono (solo dígitos).
    Si el teléfono está vacío, usa nombre + instrumento como fallback.
    """
    seen = set()
    unique = []
    for r in records:
        nombre_key = normalize_text(r.get("nombre", ""))
        phone_key = normalize_phone(r.get("telefono", ""))
        instrumento_key = normalize_text(r.get("instrumento", ""))

        if phone_key:
            key = (nombre_key, phone_key)
        else:
            key = (nombre_key, instrumento_key)

        if key not in seen:
            seen.add(key)
            unique.append(r)
        else:
            logger.debug(f"Duplicado descartado: {r.get('nombre')} ({r.get('fuente')})")

    return unique


# ─── Construcción de registro ────────────────────────────────────────────────

def build_record(
    nombre: str = "",
    instrumento: str = "",
    telefono: str = "",
    email: str = "",
    website: str = "",
    instagram: str = "",
    direccion: str = "",
    barrio: str = "",
    rating: str = "",
    fuente: str = "",
) -> dict:
    """Construye un dict con las columnas estándar del CSV."""
    return {
        "nombre": (nombre or "").strip(),
        "instrumento": (instrumento or "").strip(),
        "telefono": normalize_phone(telefono),
        "email": (email or "").strip().lower(),
        "website": (website or "").strip(),
        "instagram": (instagram or "").strip(),
        "direccion": (direccion or "").strip(),
        "barrio": (barrio or "").strip(),
        "rating": str(rating).strip() if rating else "",
        "fuente": (fuente or "").strip(),
    }


# ─── Exportación CSV ─────────────────────────────────────────────────────────

def save_to_csv(records: list[dict], filename: str = OUTPUT_FILENAME) -> Path:
    """Guarda los registros en CSV dentro de OUTPUT_DIR."""
    Path(OUTPUT_DIR).mkdir(exist_ok=True)
    path = Path(OUTPUT_DIR) / filename

    df = pd.DataFrame(records, columns=CSV_COLUMNS)

    # Limpiar columnas extra que puedan haber colado los scrapers
    for col in CSV_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df = df[CSV_COLUMNS]
    df.to_csv(path, index=False, encoding="utf-8-sig")  # utf-8-sig para Excel en Windows
    logger.info(f"CSV guardado: {path} ({len(df)} registros)")
    return path


def load_existing_csv(filename: str = OUTPUT_FILENAME) -> list[dict]:
    """Carga un CSV existente para hacer merge con nueva corrida."""
    path = Path(OUTPUT_DIR) / filename
    if not path.exists():
        return []
    df = pd.read_csv(path, dtype=str).fillna("")
    return df.to_dict("records")


# ─── HTTP helpers ─────────────────────────────────────────────────────────────

def safe_get(url: str, session: requests.Session = None, **kwargs) -> Optional[requests.Response]:
    """
    GET con reintentos y delay.
    Usa una sesión si se provee, sino crea una temporal.
    """
    getter = session or requests
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            time.sleep(REQUEST_DELAY_SECONDS)
            resp = getter.get(
                url,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT_SECONDS,
                **kwargs,
            )
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            logger.warning(f"[Intento {attempt}/{MAX_RETRIES}] Error GET {url}: {e}")
            if attempt == MAX_RETRIES:
                logger.error(f"Abandonando {url} tras {MAX_RETRIES} intentos.")
                return None
    return None


# ─── Logging setup ────────────────────────────────────────────────────────────

def setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )
