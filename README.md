# CECASP · Estación meteorológica

Página del **CECASP (Centro de Experimentación y Capacitación en Agricultura Sostenible y de Precisión)**, Piura, Perú, con los datos de su estación meteorológica.

## Cómo funciona
- `.github/workflows/actualizar.yml` ejecuta `actualizar.py` cada 10 minutos: baja las lecturas nuevas de la estación y las agrega a `data/lecturas.csv` (historial completo, nunca se recorta).
- Desde el 19/11/2026 los datos vienen de https://dpsproserver.com/station/1151 (antes, del sitio AWX de dps-promatic.com). Ese servidor entrega la hora de Italia; `actualizar.py` la convierte a hora de Perú al guardarla, igual que el historial anterior.
- `actualizar.py` también escribe `data/reciente.json` (últimos 35 días; es lo que lee la página) y llama a `eto.py`.
- `eto.py` calcula, con las mismas fórmulas del Excel de la estación (FAO-56 Penman-Monteith):
  - `data/diario.csv`: resumen diario y ETo (mm/día). Los días con menos de 44 de 48 lecturas salen como `completo = False`.
  - `data/etc_diaria.csv`: ETc por lote = Kc × ETo × factor de ambiente.
- `data/cultivos.csv` es la tabla de lotes (fechas, etapas y Kc). **Si cambia la hoja CULTIVOS del Excel, hay que actualizar este archivo.**
- `index.html` es la página: lee `reciente.json`, `diario.csv` y `etc_diaria.csv`.

No reemplazar `data/lecturas.csv` por una versión más corta: el historial se pierde.
