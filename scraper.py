# -*- coding: utf-8 -*-
"""Scraper generico de Google Maps reutilizable por consola o Streamlit."""

import csv
import random
import re
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

import config
from countries import filter_anchors, get_country_config
from export_utils import export_country_excel, normalize_phone, normalize_text


CSV_COLUMNS = [
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


def slugify(value):
    value = normalize_text(value).lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "general"


def ensure_parent_dir(file_path):
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)


def load_visited_ids(visited_file):
    path = Path(visited_file)
    if not path.exists():
        return set()
    with path.open("r", encoding="utf-8") as file_handle:
        return {line.strip() for line in file_handle if line.strip()}


def mark_visited(visited_file, place_id):
    ensure_parent_dir(visited_file)
    with Path(visited_file).open("a", encoding="utf-8") as file_handle:
        file_handle.write(place_id + "\n")


def ensure_csv_header(csv_file):
    path = Path(csv_file)
    if path.exists() and path.stat().st_size > 0:
        return
    ensure_parent_dir(csv_file)
    with path.open("w", newline="", encoding="utf-8") as file_handle:
        writer = csv.writer(file_handle)
        writer.writerow(CSV_COLUMNS)


def append_row(csv_file, row):
    ensure_parent_dir(csv_file)
    with Path(csv_file).open("a", newline="", encoding="utf-8") as file_handle:
        writer = csv.writer(file_handle)
        writer.writerow([row.get(column, "") for column in CSV_COLUMNS])


def extract_place_id(href):
    match = re.search(r"!1s(0x[0-9a-fA-F]+:0x[0-9a-fA-F]+)", href)
    if match:
        return match.group(1)
    match = re.search(r"/maps/place/([^/]+)/", href)
    return match.group(1) if match else href


def build_search_url(query, lat, lng, zoom, query_suffix):
    effective_query = f"{normalize_text(query)} en {query_suffix}" if query_suffix else normalize_text(query)
    return f"https://www.google.com/maps/search/{urllib.parse.quote(effective_query)}/@{lat},{lng},{zoom}z"


def scroll_and_collect_links(page, max_scrolls):
    try:
        page.wait_for_selector('div[role="feed"]', timeout=15000)
    except PWTimeout:
        return set(page.eval_on_selector_all(
            'a[href*="/maps/place/"]', "els => els.map(e => e.href)"
        ))

    feed = page.query_selector('div[role="feed"]')
    seen_count = -1
    stable_rounds = 0

    for _ in range(max_scrolls):
        page.evaluate("(el) => el.scrollTo(0, el.scrollHeight)", feed)
        time.sleep(random.uniform(1.2, 2.2))

        links = page.eval_on_selector_all(
            'div[role="feed"] a[href*="/maps/place/"]',
            "els => els.map(e => e.href)",
        )
        current_count = len(set(links))

        end_marker = page.query_selector("text=has llegado al final de la lista")
        if end_marker is None:
            end_marker = page.query_selector("text=You've reached the end of the list")

        if current_count == seen_count:
            stable_rounds += 1
        else:
            stable_rounds = 0
        seen_count = current_count

        if end_marker or stable_rounds >= 3:
            break

    links = page.eval_on_selector_all(
        'div[role="feed"] a[href*="/maps/place/"]',
        "els => els.map(e => e.href)",
    )
    return set(links)


def scrape_detail(page, href):
    page.goto(href, wait_until="domcontentloaded", timeout=30000)
    try:
        page.wait_for_selector("h1", timeout=15000)
    except PWTimeout:
        return None

    def safe_text(selector):
        element = page.query_selector(selector)
        return element.inner_text().strip() if element else ""

    def safe_attr(selector, attr):
        element = page.query_selector(selector)
        value = element.get_attribute(attr) if element else ""
        return value.strip() if value else ""

    phone_element = page.query_selector('button[data-item-id^="phone:tel:"]')
    phone = ""
    if phone_element:
        phone = phone_element.get_attribute("data-item-id").replace("phone:tel:", "")

    return {
        "nombre": safe_text("h1"),
        "categoria": safe_text('button[jsaction*="category"]'),
        "rating": safe_text('div.F7nice span[aria-hidden="true"]'),
        "num_resenas": re.sub(
            r"[^\d]",
            "",
            safe_text('div.F7nice span[aria-label*="reseñas"], div.F7nice span[aria-label*="reviews"]'),
        ),
        "direccion": safe_text('button[data-item-id="address"]'),
        "telefono": phone,
        "sitio_web": safe_attr('a[data-item-id="authority"]', "href"),
    }


def build_run_paths(country_name, campaign_name, output_dir=None, state_dir=None):
    output_root = Path(output_dir or config.OUTPUT_DIR)
    state_root = Path(state_dir or config.STATE_DIR)
    country_slug = slugify(country_name)
    campaign_slug = slugify(campaign_name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    csv_file = output_root / "csv" / f"resultados_{country_slug}_{campaign_slug}.csv"
    excel_file = output_root / "excel" / f"resultados_{country_slug}_{campaign_slug}_{timestamp}.xlsx"
    visited_file = state_root / f"visited_ids_{country_slug}_{campaign_slug}.txt"
    return {
        "csv": csv_file,
        "excel": excel_file,
        "visited": visited_file,
    }


def run_scraper(
    country_name,
    search_queries,
    selected_anchor_names=None,
    campaign_name=None,
    headless=None,
    visit_details=None,
    max_scrolls=None,
    delay_between_detail_pages=None,
    delay_between_anchors=None,
    output_dir=None,
    state_dir=None,
    log_callback=None,
):
    country = get_country_config(country_name)
    anchors = filter_anchors(country_name, selected_anchor_names)
    queries = [normalize_text(query) for query in search_queries if normalize_text(query)]
    if not queries:
        raise ValueError("Debes indicar al menos una SEARCH_QUERY.")

    campaign = campaign_name or config.DEFAULT_CAMPAIGN_NAME
    headless = config.HEADLESS if headless is None else headless
    visit_details = config.VISIT_DETAILS if visit_details is None else visit_details
    max_scrolls = config.MAX_SCROLLS_PER_SEARCH if max_scrolls is None else max_scrolls
    delay_between_detail_pages = delay_between_detail_pages or config.DELAY_BETWEEN_DETAIL_PAGES
    delay_between_anchors = delay_between_anchors or config.DELAY_BETWEEN_ANCHORS
    paths = build_run_paths(country_name, campaign, output_dir=output_dir, state_dir=state_dir)

    def log(message):
        print(message)
        if log_callback:
            log_callback(message)

    ensure_csv_header(paths["csv"])
    visited = load_visited_ids(paths["visited"])
    total_found = 0
    total_new = 0
    total_exported = 0
    started_at = datetime.now().isoformat(timespec="seconds")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        context = browser.new_context(locale=country["locale"])
        search_page = context.new_page()

        for query in queries:
            for anchor_name, lat, lng, zoom in anchors:
                url = build_search_url(query, lat, lng, zoom, country.get("query_suffix", country_name))
                log(f"[BUSCANDO] '{query}' en {anchor_name} -> {url}")

                try:
                    search_page.goto(url, wait_until="domcontentloaded", timeout=30000)
                except PWTimeout:
                    log(f"  ! timeout cargando {anchor_name}, se omite")
                    continue

                time.sleep(random.uniform(1.5, 2.5))
                links = scroll_and_collect_links(search_page, max_scrolls)
                total_found += len(links)
                log(f"  -> {len(links)} fichas encontradas en esta ancla")

                new_links = []
                for href in links:
                    place_id = extract_place_id(href)
                    if place_id not in visited:
                        new_links.append((place_id, href))

                total_new += len(new_links)
                log(f"  -> {len(new_links)} son nuevas para esta campana")

                detail_page = context.new_page() if visit_details and new_links else None
                for place_id, href in new_links:
                    row = {
                        "place_id": place_id,
                        "nombre": "",
                        "categoria": "",
                        "rating": "",
                        "num_resenas": "",
                        "direccion": "",
                        "telefono": "",
                        "sitio_web": "",
                        "google_maps_url": href,
                        "ancla_busqueda": anchor_name,
                        "query": query,
                        "pais": country_name,
                        "fecha_extraccion": datetime.now().isoformat(timespec="seconds"),
                    }

                    if detail_page:
                        try:
                            data = scrape_detail(detail_page, href)
                        except Exception as exc:
                            log(f"    ! error en {href}: {exc}")
                            continue
                        if data is None:
                            continue
                        row.update({
                            "nombre": normalize_text(data["nombre"]),
                            "categoria": normalize_text(data["categoria"]),
                            "rating": normalize_text(data["rating"]),
                            "num_resenas": normalize_text(data["num_resenas"]),
                            "direccion": normalize_text(data["direccion"]),
                            "telefono": normalize_phone(data["telefono"]),
                            "sitio_web": normalize_text(data["sitio_web"]),
                        })

                    append_row(paths["csv"], row)
                    mark_visited(paths["visited"], place_id)
                    visited.add(place_id)
                    total_exported += 1
                    if row["nombre"]:
                        log(f"    + {row['nombre']}")
                    if detail_page:
                        time.sleep(random.uniform(*delay_between_detail_pages))

                if detail_page:
                    detail_page.close()

                time.sleep(random.uniform(*delay_between_anchors))

        browser.close()

    excel_file = export_country_excel(paths["csv"], paths["excel"])
    log(f"Listo. CSV en {paths['csv']}")
    log(f"Excel en {excel_file}")

    return {
        "country": country_name,
        "campaign": campaign,
        "csv_path": str(paths["csv"]),
        "excel_path": str(excel_file),
        "visited_path": str(paths["visited"]),
        "total_found": total_found,
        "total_new": total_new,
        "total_exported": total_exported,
        "started_at": started_at,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "queries": queries,
        "anchors_used": len(anchors),
    }


def run():
    return run_scraper(
        country_name=config.DEFAULT_COUNTRY,
        search_queries=config.SEARCH_QUERIES,
        campaign_name=config.DEFAULT_CAMPAIGN_NAME,
    )


if __name__ == "__main__":
    run()
