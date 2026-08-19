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
python -m pip install -r requirements.txt
python -m playwright install chromium
```

## Ejecucion local

```bash
streamlit run app.py
```

Flujo recomendado local:

1. Ejecuta la app con `streamlit run app.py`.
2. Si es tu primera corrida o aparece un CAPTCHA, desactiva `Headless` desde la interfaz.
3. Haz una prueba corta con una sola query y una o pocas ciudades antes de correr un pais completo.
4. Descarga el Excel desde la propia interfaz cuando termine la corrida.

## Despliegue en Streamlit web

El repo incluye `packages.txt` para que el contenedor Linux instale las dependencias de Chromium que Playwright necesita.

Pasos recomendados:

1. Desplegar el repo completo, incluyendo `requirements.txt` y `packages.txt`.
2. Dejar que Streamlit reconstruya el entorno.
3. Ejecutar la app normalmente desde `app.py`.
4. Probar primero una corrida corta para validar que Chromium abra correctamente.

En entorno web, la aplicacion fuerza `headless = True` automaticamente. Esto evita fallos por falta de escritorio grafico.

Si el despliegue falla al abrir Chromium, revisa primero mensajes que nombren librerias Linux faltantes como `libglib-2.0.so.0`. En ese caso, vuelve a desplegar verificando que `packages.txt` haya sido tomado por la plataforma.

Desde la interfaz puedes:

1. Elegir uno o mas paises.
2. Elegir cobertura de `Pais completo` o, si trabajas con un solo pais, limitarlo a ciudades especificas.
3. Definir `SEARCH_QUERIES` en un campo multilinea.
4. Nombrar la campana.
5. Ejecutar con o sin navegador visible.
6. Descargar un Excel si es un pais, o un ZIP con un Excel por pais si son varios.
7. Convertir un CSV existente a Excel sin volver a scrapear.

## Uso por consola

```bash
python scraper.py
```

La ejecucion por consola usa los valores por defecto de `config.py`.

## Salidas

- CSV incremental en `outputs/csv/`
- Excel final en `outputs/excel/`
- Estado de reanudacion en `state/`
- CSV subidos para conversion en `outputs/uploads/`

Los archivos de estado se separan por pais y campana para no mezclar corridas.
Cada corrida genera un Excel independiente por pais.

## Estructura

- `app.py`: interfaz `Streamlit`
- `scraper.py`: logica de scraping reutilizable
- `countries.py`: catalogo de paises y anclas
- `export_utils.py`: limpieza y exportacion a Excel
- `config.py`: configuracion por defecto
- `packages.txt`: dependencias Linux necesarias para desplegar Chromium en Streamlit web

## Notas importantes

- No usa la API oficial de Google Maps.
- Google puede cambiar selectores o mostrar CAPTCHA.
- Conviene empezar con `HEADLESS = False` si necesitas resolver un CAPTCHA manualmente.
- En Streamlit web el modo headless queda forzado y no conviene usar esa variante para resolver CAPTCHA manualmente.
- El exportador deduplica por `place_id` y tambien por combinacion `nombre + direccion` cuando falta un identificador confiable.
