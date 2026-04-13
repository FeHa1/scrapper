#!/usr/bin/env python3
"""
Orquestador principal del scraper de docentes de música.

Uso:
    # Correr todas las fuentes (requiere API key de Outscraper)
    python main.py

    # Solo fuentes gratuitas (sin Outscraper)
    python main.py --skip-maps

    # Solo un instrumento para pruebas rápidas
    python main.py --instruments guitarra piano --skip-maps

    # Combinar con corridas anteriores (merge + dedup)
    python main.py --merge-existing

    # Modo verbose
    python main.py --verbose
"""

import argparse
import logging
import sys
from pathlib import Path

# Asegurar que el root del proyecto esté en el path
sys.path.insert(0, str(Path(__file__).parent))

from config import INSTRUMENTS, OUTPUT_FILENAME
from scrapers import scrape_google_maps, scrape_superprof, scrape_tusclases
from utils import deduplicate, has_contact, load_existing_csv, save_to_csv, setup_logging

logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="Scraper de docentes de música en Argentina")
    parser.add_argument(
        "--instruments",
        nargs="+",
        default=None,
        metavar="INSTRUMENTO",
        help="Lista de instrumentos a buscar (default: todos en config.py)",
    )
    parser.add_argument(
        "--skip-maps",
        action="store_true",
        help="No usar Outscraper (útil para pruebas sin API key)",
    )
    parser.add_argument(
        "--skip-superprof",
        action="store_true",
        help="Omitir Superprof",
    )
    parser.add_argument(
        "--skip-tusclases",
        action="store_true",
        help="Omitir TusClases",
    )
    parser.add_argument(
        "--merge-existing",
        action="store_true",
        help="Combinar resultados con el CSV existente (si hay uno)",
    )
    parser.add_argument(
        "--output",
        default=OUTPUT_FILENAME,
        help=f"Nombre del archivo CSV de salida (default: {OUTPUT_FILENAME})",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Logging detallado (DEBUG)",
    )
    return parser.parse_args()


def run(args) -> Path:
    setup_logging(logging.DEBUG if args.verbose else logging.INFO)
    instruments = args.instruments or INSTRUMENTS

    logger.info("=" * 60)
    logger.info("SCRAPER DE DOCENTES DE MÚSICA — INICIO")
    logger.info(f"Instrumentos: {instruments}")
    logger.info("=" * 60)

    all_records = []

    # ── Fuente 1: Google Maps (Outscraper) ───────────────────────────────────
    if not args.skip_maps:
        logger.info("\n[1/3] Google Maps vía Outscraper...")
        maps_records = scrape_google_maps(instruments=instruments)
        logger.info(f"     → {len(maps_records)} registros")
        all_records.extend(maps_records)
    else:
        logger.info("\n[1/3] Google Maps — OMITIDO (--skip-maps)")

    # ── Fuente 2: Superprof ──────────────────────────────────────────────────
    if not args.skip_superprof:
        logger.info("\n[2/3] Superprof...")
        superprof_records = scrape_superprof(instruments=instruments)
        logger.info(f"     → {len(superprof_records)} registros")
        all_records.extend(superprof_records)
    else:
        logger.info("\n[2/3] Superprof — OMITIDO (--skip-superprof)")

    # ── Fuente 3: TusClases ──────────────────────────────────────────────────
    if not args.skip_tusclases:
        logger.info("\n[3/3] TusClases...")
        tusclases_records = scrape_tusclases(instruments=instruments)
        logger.info(f"     → {len(tusclases_records)} registros")
        all_records.extend(tusclases_records)
    else:
        logger.info("\n[3/3] TusClases — OMITIDO (--skip-tusclases)")

    # ── Merge con corrida anterior ────────────────────────────────────────────
    if args.merge_existing:
        existing = load_existing_csv(args.output)
        if existing:
            logger.info(f"\nMergeando con {len(existing)} registros existentes...")
            all_records = existing + all_records

    # ── Deduplicación ─────────────────────────────────────────────────────────
    before = len(all_records)
    all_records = deduplicate(all_records)
    logger.info(f"\nDeduplicación: {before} → {len(all_records)} registros únicos")

    # ── Filtrado final (doble check) ─────────────────────────────────────────
    all_records = [r for r in all_records if has_contact(r)]
    logger.info(f"Tras filtro de contacto: {len(all_records)} registros")

    # ── Exportar ──────────────────────────────────────────────────────────────
    if not all_records:
        logger.warning("No se encontraron registros válidos. Revisá los logs.")
        return None

    path = save_to_csv(all_records, args.output)

    # ── Resumen final ─────────────────────────────────────────────────────────
    from collections import Counter
    sources = Counter(r["fuente"] for r in all_records)
    instruments_count = Counter(r["instrumento"] for r in all_records)

    logger.info("\n" + "=" * 60)
    logger.info("RESUMEN FINAL")
    logger.info("=" * 60)
    logger.info(f"Total registros: {len(all_records)}")
    logger.info("\nPor fuente:")
    for src, count in sources.most_common():
        logger.info(f"  {src:<20} {count:>5}")
    logger.info("\nTop instrumentos:")
    for inst, count in instruments_count.most_common(8):
        logger.info(f"  {inst:<20} {count:>5}")
    logger.info(f"\nCSV guardado en: {path}")
    logger.info("=" * 60)

    return path


if __name__ == "__main__":
    args = parse_args()
    run(args)
