# scraping_google

Scraper de Google Maps basado en Playwright, reutilizable por rubro y ahora con ejecucion por `Streamlit`, soporte multi-pais y exportacion a Excel.

## Paises soportados

- Chile
- Peru
- Argentina
- Bolivia
- Ecuador
- Uruguay

Cada pais incluye una cobertura amplia de anclas urbanas para uso inmediato.

## Instalacion

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

## Uso con Streamlit

```bash
streamlit run app.py
```

Desde la interfaz puedes:

1. Elegir uno o mas paises.
2. Definir `SEARCH_QUERIES` en un campo multilinea.
3. Nombrar la campana.
4. Ejecutar con o sin navegador visible.
5. Descargar un Excel si es un pais, o un ZIP con un Excel por pais si son varios.

## Uso por consola

```bash
python scraper.py
```

La ejecucion por consola usa los valores por defecto de `config.py`.

## Salidas

- CSV incremental en `outputs/csv/`
- Excel final en `outputs/excel/`
- Estado de reanudacion en `state/`

Los archivos de estado se separan por pais y campana para no mezclar corridas.
Cada corrida genera un Excel independiente por pais.

## Estructura

- `app.py`: interfaz `Streamlit`
- `scraper.py`: logica de scraping reutilizable
- `countries.py`: catalogo de paises y anclas
- `export_utils.py`: limpieza y exportacion a Excel
- `config.py`: configuracion por defecto

## Notas importantes

- No usa la API oficial de Google Maps.
- Google puede cambiar selectores o mostrar CAPTCHA.
- Conviene empezar con `HEADLESS = False` si necesitas resolver un CAPTCHA manualmente.
- El scraper deduplica por `place_id` dentro de cada campana.
