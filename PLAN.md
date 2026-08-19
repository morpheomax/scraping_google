# Plan de trabajo

Estado actual: el alcance queda enfocado en dos formas de uso: ejecucion local con `streamlit run app.py` y despliegue en Streamlit web. No se seguira con empaquetado `.exe` por ahora.

```mermaid
flowchart TD
    A[Retomar proyecto] --> B[Estabilizar version web]
    B --> B1[Agregar packages.txt con dependencias Linux de Chromium]
    B --> B2[Forzar headless en entorno web]
    B --> B3[Mejorar mensajes de error de Playwright y Streamlit]
    B --> B4[Validar despliegue en Streamlit web]

    A --> C[Documentar ejecucion local y web]
    C --> C1[Actualizar README con instalacion local]
    C --> C2[Documentar limites de Streamlit web]
    C --> C3[Explicar flujo recomendado de uso]
```

## Orden sugerido

1. Version web estable.
2. README claro para uso local y despliegue.

## Nota

La causa confirmada en Streamlit web fue la falta de librerias Linux para Chromium, empezando por `libglib-2.0.so.0`.
