# -*- coding: utf-8 -*-
"""Configuracion por defecto del scraper."""

DEFAULT_COUNTRY = "Chile"

SEARCH_QUERIES = [
    "empresas contra incendio",
    "extintores",
    "sistemas contra incendio",
    "seguridad contra incendio",
    "sprinklers contra incendio",
    "fire",
]

HEADLESS = False
VISIT_DETAILS = True
MAX_SCROLLS_PER_SEARCH = 40
DELAY_BETWEEN_DETAIL_PAGES = (1.5, 3.5)
DELAY_BETWEEN_ANCHORS = (5, 12)

OUTPUT_DIR = "outputs"
STATE_DIR = "state"
DEFAULT_CAMPAIGN_NAME = "general"
