# -*- coding: utf-8 -*-
"""Interfaz Streamlit para ejecutar el scraper."""

from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
import streamlit as st

import config
from countries import get_anchor_names, get_country_names
from export_utils import export_country_excel, load_and_clean_results
from scraper import run_scraper, slugify


st.set_page_config(page_title="Google Maps Scraper", layout="wide")
st.title("Google Maps Scraper")
st.caption("Scraping por pais con exportacion a Excel ordenada")

IS_HOSTED_STREAMLIT = config.is_hosted_streamlit_environment()


def parse_queries(raw_text):
    return [line.strip() for line in raw_text.splitlines() if line.strip()]


def render_results(results, campaign_name):
    total_found = sum(item.get("total_found", 0) for item in results)
    total_new = sum(item.get("total_new", 0) for item in results)
    total_exported = sum(item.get("total_exported", 0) for item in results)

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
            "queries": len(result.get("queries", [])),
            "anclas": result.get("anchors_used", 0),
            "fichas_encontradas": result.get("total_found", 0),
            "fichas_nuevas": result.get("total_new", 0),
            "filas_exportadas": result.get("total_exported", len(dataframe)),
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


scrape_tab, convert_tab = st.tabs(["Scraping", "Convertir CSV a Excel"])

with scrape_tab:
    default_queries = "\n".join(config.SEARCH_QUERIES)
    default_country = config.DEFAULT_COUNTRY
    country_names = get_country_names()
    selected_countries = st.multiselect(
        "Paises a consultar",
        country_names,
        default=[default_country],
        help="Puedes elegir uno o varios paises. Si eliges varios, cada pais se corre completo y se exporta en su propio archivo.",
    )
    campaign_name = st.text_input(
        "Nombre de campana",
        value=config.DEFAULT_CAMPAIGN_NAME,
        help="Nombre interno de la corrida. Se usa para nombrar archivos y separar el historial de visitados.",
    )
    queries_text = st.text_area(
        "SEARCH_QUERIES (una por linea)",
        value=default_queries,
        height=180,
        help="Escribe una busqueda por linea. Ejemplo: extintores, empresas contra incendio, fire protection.",
    )

    coverage_mode = "Pais completo"
    selected_anchors = []
    if len(selected_countries) == 1:
        coverage_mode = st.radio(
            "Cobertura geografica",
            ["Pais completo", "Ciudades especificas"],
            horizontal=True,
            help="Pais completo usa todas las ciudades configuradas para ese pais. Ciudades especificas limita la corrida a las anclas seleccionadas.",
        )
        if coverage_mode == "Ciudades especificas":
            selected_anchors = st.multiselect(
                "Ciudades / anclas",
                get_anchor_names(selected_countries[0]),
                default=get_anchor_names(selected_countries[0])[:5],
                help="Selecciona solo las ciudades donde quieres buscar. Esto acelera la corrida cuando no necesitas cubrir todo el pais.",
            )
    elif len(selected_countries) > 1:
        st.caption("Con varios paises seleccionados, la corrida usa automaticamente la cobertura de pais completo en cada uno.")

    col1, col2, col3 = st.columns(3)
    with col1:
        headless = st.checkbox(
            "Ejecutar sin abrir navegador (Headless)",
            value=True if IS_HOSTED_STREAMLIT else config.HEADLESS,
            disabled=IS_HOSTED_STREAMLIT,
            help=(
                "En Streamlit web queda forzado para que Chromium pueda iniciar sin escritorio grafico."
                if IS_HOSTED_STREAMLIT
                else "Activado: el navegador corre oculto. Desactivado: ves la ventana del navegador, util para resolver CAPTCHA o revisar manualmente."
            ),
        )
    with col2:
        visit_details = st.checkbox(
            "Entrar a cada ficha para extraer telefono, web y direccion completa",
            value=config.VISIT_DETAILS,
            help="Activado: abre cada negocio para sacar mas datos. Desactivado: corre mas rapido, pero exporta menos informacion.",
        )
    with col3:
        max_scrolls = st.number_input(
            "Maximo de scrolls por busqueda",
            min_value=5,
            max_value=500,
            value=config.MAX_SCROLLS_PER_SEARCH,
            step=5,
            help="Controla cuantas veces se desplaza la lista de resultados en Google Maps. Para pais completo o rubros grandes, 80, 120 o mas puede ser necesario.",
        )

    if IS_HOSTED_STREAMLIT:
        st.caption("Entorno web detectado: el navegador se ejecuta en modo headless y depende de las librerias del archivo `packages.txt`.")
    else:
        st.caption("Sugerencia: si es tu primera corrida o Google te muestra CAPTCHA, desactiva el modo Headless para ver el navegador.")

    run_button = st.button("Iniciar scraping", type="primary")

    if run_button:
        queries = parse_queries(queries_text)
        if not selected_countries:
            st.error("Debes seleccionar al menos un pais.")
        elif not queries:
            st.error("Debes ingresar al menos una query.")
        elif len(selected_countries) == 1 and coverage_mode == "Ciudades especificas" and not selected_anchors:
            st.error("Debes seleccionar al menos una ciudad o ancla.")
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
                        anchor_names = None
                        if len(selected_countries) == 1 and coverage_mode == "Ciudades especificas":
                            anchor_names = selected_anchors
                        result = run_scraper(
                            country_name=country_name,
                            search_queries=queries,
                            selected_anchor_names=anchor_names,
                            campaign_name=campaign_name,
                            headless=headless,
                            visit_details=visit_details,
                            max_scrolls=int(max_scrolls),
                            log_callback=push_log,
                        )
                        results.append(result)
            except Exception as exc:
                st.error(f"La corrida fallo: {exc}")
                error_text = str(exc)
                if "playwright install chromium" in error_text:
                    st.info("Si tu entorno bloquea la descarga automatica del navegador, ejecuta `playwright install chromium` en la terminal del servidor o entorno donde corre Streamlit.")
                if "packages.txt" in error_text or "libglib2.0-0" in error_text or "headless" in error_text:
                    st.info("Si esto ocurre en Streamlit web, revisa que el repo incluya `packages.txt` con las dependencias Linux de Chromium y vuelve a desplegar la app.")
                st.stop()

            st.success("Scraping finalizado")
            render_results(results, campaign_name)
    else:
        st.info("Configura uno o mas paises, elige si quieres pais completo o ciudades especificas, y luego inicia una corrida nueva.")

with convert_tab:
    st.write("Convierte un CSV existente a Excel limpio y ordenado sin volver a scrapear.")
    uploaded_file = st.file_uploader("CSV de entrada", type=["csv"])
    convert_campaign = st.text_input("Nombre base para el archivo", value="conversion")
    convert_button = st.button("Convertir CSV a Excel")

    if convert_button:
        if uploaded_file is None:
            st.error("Debes cargar un archivo CSV.")
        else:
            uploads_dir = Path(config.OUTPUT_DIR) / "uploads"
            uploads_dir.mkdir(parents=True, exist_ok=True)
            csv_path = uploads_dir / uploaded_file.name
            csv_path.write_bytes(uploaded_file.getbuffer())

            excel_path = Path(config.OUTPUT_DIR) / "excel" / f"{slugify(convert_campaign)}_{csv_path.stem}.xlsx"
            export_country_excel(csv_path, excel_path)
            dataframe = load_and_clean_results(csv_path)

            st.success("Conversion finalizada")
            st.metric("Filas exportadas", len(dataframe))
            st.dataframe(dataframe, use_container_width=True, height=500)

            with excel_path.open("rb") as file_handle:
                st.download_button(
                    "Descargar Excel convertido",
                    data=file_handle.read(),
                    file_name=excel_path.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

            st.caption(f"CSV: {csv_path}")
            st.caption(f"Excel: {excel_path}")
