# -*- coding: utf-8 -*-
"""Configuracion por defecto del scraper."""

import os

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
MAX_SCROLLS_PER_SEARCH = 80
DELAY_BETWEEN_DETAIL_PAGES = (1.5, 3.5)
DELAY_BETWEEN_ANCHORS = (5, 12)

OUTPUT_DIR = "outputs"
STATE_DIR = "state"
DEFAULT_CAMPAIGN_NAME = "general"


def is_hosted_streamlit_environment():
    return any(
        os.getenv(variable)
        for variable in [
            "STREAMLIT_SHARING_MODE",
            "STREAMLIT_CLOUD",
            "STREAMLIT_RUNTIME",
        ]
    )
