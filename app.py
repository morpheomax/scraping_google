# -*- coding: utf-8 -*-
"""Interfaz Streamlit para ejecutar el scraper."""

from pathlib import Path
import streamlit as st

import config
from countries import get_country_names
from export_utils import load_and_clean_results
from scraper import run_scraper, slugify


st.set_page_config(page_title="Google Maps Scraper", layout="wide")
st.title("Google Maps Scraper")
st.caption("Scraping por pais con exportacion a Excel ordenada")


def parse_queries(raw_text):
    return [line.strip() for line in raw_text.splitlines() if line.strip()]


default_queries = "\n".join(config.SEARCH_QUERIES)
country_name = st.selectbox("Pais", get_country_names(), index=get_country_names().index(config.DEFAULT_COUNTRY))
campaign_name = st.text_input("Nombre de campana", value=config.DEFAULT_CAMPAIGN_NAME)
queries_text = st.text_area("SEARCH_QUERIES (una por linea)", value=default_queries, height=180)

col1, col2, col3 = st.columns(3)
with col1:
    headless = st.checkbox("Headless", value=config.HEADLESS)
with col2:
    visit_details = st.checkbox("Visitar detalle", value=config.VISIT_DETAILS)
with col3:
    max_scrolls = st.number_input("Max scrolls por busqueda", min_value=5, max_value=100, value=config.MAX_SCROLLS_PER_SEARCH)

run_button = st.button("Iniciar scraping", type="primary")

if run_button:
    queries = parse_queries(queries_text)
    if not queries:
        st.error("Debes ingresar al menos una query.")
    else:
        log_placeholder = st.empty()
        log_lines = []

        def push_log(message):
            log_lines.append(message)
            log_placeholder.code("\n".join(log_lines[-100:]), language="text")

        try:
            with st.spinner("Ejecutando scraping. Esto puede tardar bastante segun el pais y las queries."):
                result = run_scraper(
                    country_name=country_name,
                    search_queries=queries,
                    campaign_name=campaign_name,
                    headless=headless,
                    visit_details=visit_details,
                    max_scrolls=int(max_scrolls),
                    log_callback=push_log,
                )
        except Exception as exc:
            st.error(f"La corrida fallo: {exc}")
            st.stop()

        st.success("Scraping finalizado")

        metric1, metric2, metric3 = st.columns(3)
        metric1.metric("Fichas encontradas", result["total_found"])
        metric2.metric("Fichas nuevas", result["total_new"])
        metric3.metric("Filas exportadas", result["total_exported"])

        csv_path = Path(result["csv_path"])
        excel_path = Path(result["excel_path"])
        dataframe = load_and_clean_results(csv_path)

        st.subheader("Vista previa")
        st.dataframe(dataframe, use_container_width=True, height=500)

        download_name = excel_path.name
        with excel_path.open("rb") as file_handle:
            st.download_button(
                "Descargar Excel",
                data=file_handle.read(),
                file_name=download_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        st.caption(f"CSV: {csv_path}")
        st.caption(f"Excel: {excel_path}")

else:
    st.info("Configura el pais y las queries para iniciar una corrida nueva.")
