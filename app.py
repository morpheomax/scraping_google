# -*- coding: utf-8 -*-
"""Interfaz Streamlit para ejecutar el scraper."""

from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
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
default_country = config.DEFAULT_COUNTRY
country_names = get_country_names()
selected_countries = st.multiselect(
    "Paises",
    country_names,
    default=[default_country],
)
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
    if not selected_countries:
        st.error("Debes seleccionar al menos un pais.")
    elif not queries:
        st.error("Debes ingresar al menos una query.")
    else:
        log_placeholder = st.empty()
        log_lines = []

        def push_log(message):
            log_lines.append(message)
            log_placeholder.code("\n".join(log_lines[-100:]), language="text")

        try:
            with st.spinner("Ejecutando scraping. Esto puede tardar bastante segun el pais y las queries."):
                results = []
                for country_name in selected_countries:
                    push_log(f"=== Iniciando corrida para {country_name} ===")
                    result = run_scraper(
                        country_name=country_name,
                        search_queries=queries,
                        campaign_name=campaign_name,
                        headless=headless,
                        visit_details=visit_details,
                        max_scrolls=int(max_scrolls),
                        log_callback=push_log,
                    )
                    results.append(result)
        except Exception as exc:
            st.error(f"La corrida fallo: {exc}")
            st.stop()

        st.success("Scraping finalizado")

        total_found = sum(item["total_found"] for item in results)
        total_new = sum(item["total_new"] for item in results)
        total_exported = sum(item["total_exported"] for item in results)

        metric1, metric2, metric3, metric4 = st.columns(4)
        metric1.metric("Paises procesados", len(results))
        metric2.metric("Fichas encontradas", total_found)
        metric3.metric("Fichas nuevas", total_new)
        metric4.metric("Filas exportadas", total_exported)

        summary_rows = []
        preview_frames = []
        for result in results:
            csv_path = Path(result["csv_path"])
            dataframe = load_and_clean_results(csv_path)
            preview_frames.append(dataframe)
            summary_rows.append({
                "pais": result["country"],
                "campana": result["campaign"],
                "queries": len(result["queries"]),
                "anclas": result["anchors_used"],
                "fichas_encontradas": result["total_found"],
                "fichas_nuevas": result["total_new"],
                "filas_exportadas": result["total_exported"],
                "csv": result["csv_path"],
                "excel": result["excel_path"],
            })

        st.subheader("Resumen por pais")
        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

        st.subheader("Vista previa consolidada")
        preview_df = pd.concat(preview_frames, ignore_index=True) if preview_frames else pd.DataFrame()
        st.dataframe(preview_df, use_container_width=True, height=500)

        if len(results) == 1:
            excel_path = Path(results[0]["excel_path"])
            with excel_path.open("rb") as file_handle:
                st.download_button(
                    "Descargar Excel",
                    data=file_handle.read(),
                    file_name=excel_path.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
        else:
            zip_buffer = BytesIO()
            with ZipFile(zip_buffer, "w", ZIP_DEFLATED) as zip_file:
                for result in results:
                    excel_path = Path(result["excel_path"])
                    zip_file.write(excel_path, arcname=excel_path.name)
            st.download_button(
                "Descargar Excels por pais (ZIP)",
                data=zip_buffer.getvalue(),
                file_name=f"excels_{slugify(campaign_name)}.zip",
                mime="application/zip",
            )

        for result in results:
            st.caption(f"{result['country']} | CSV: {result['csv_path']}")
            st.caption(f"{result['country']} | Excel: {result['excel_path']}")

else:
    st.info("Configura uno o mas paises y las queries para iniciar una corrida nueva.")
