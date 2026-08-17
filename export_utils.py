# -*- coding: utf-8 -*-
"""Utilidades de limpieza y exportacion."""

from pathlib import Path

import pandas as pd


EXPORT_COLUMNS = [
    "place_id",
    "nombre",
    "categoria",
    "rating",
    "num_resenas",
    "direccion",
    "telefono",
    "sitio_web",
    "google_maps_url",
    "ancla_busqueda",
    "query",
    "pais",
    "fecha_extraccion",
]


def build_fallback_key(row):
    name = normalize_text(row.get("nombre", "")).lower()
    address = normalize_text(row.get("direccion", "")).lower()
    if not name and not address:
        return ""
    return f"{name}|{address}"


def normalize_text(value):
    if value is None:
        return ""
    text = str(value).replace("\r", " ").replace("\n", " ")
    return " ".join(text.split())


def normalize_phone(value):
    text = normalize_text(value)
    if not text:
        return ""
    if text.startswith("+"):
        return "+" + "".join(ch for ch in text[1:] if ch.isdigit())
    return "".join(ch for ch in text if ch.isdigit())


def load_and_clean_results(csv_path):
    csv_file = Path(csv_path)
    if not csv_file.exists():
        raise FileNotFoundError(f"No existe el CSV: {csv_file}")

    df = pd.read_csv(csv_file, dtype=str).fillna("")

    for column in EXPORT_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    text_columns = [
        "place_id",
        "nombre",
        "categoria",
        "rating",
        "num_resenas",
        "direccion",
        "sitio_web",
        "google_maps_url",
        "ancla_busqueda",
        "query",
        "pais",
        "fecha_extraccion",
    ]
    for column in text_columns:
        df[column] = df[column].map(normalize_text)

    df["telefono"] = df["telefono"].map(normalize_phone)
    df["_fallback_key"] = df.apply(build_fallback_key, axis=1)

    df = df.drop_duplicates(subset=["place_id"], keep="first")
    fallback_mask = df["_fallback_key"] != ""
    df = pd.concat(
        [
            df.loc[~fallback_mask],
            df.loc[fallback_mask].drop_duplicates(subset=["_fallback_key"], keep="first"),
        ],
        ignore_index=True,
    )
    df = df.sort_values(
        by=["pais", "ancla_busqueda", "query", "nombre"],
        kind="stable",
    )

    return df[EXPORT_COLUMNS]


def export_country_excel(csv_path, excel_path):
    df = load_and_clean_results(csv_path)
    excel_file = Path(excel_path)
    excel_file.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="resultados")
    return excel_file
