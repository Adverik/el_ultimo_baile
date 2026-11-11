# Banco y botín: cómo funciona por dentro

Rama `propuestas`. Nada de esto está en producción.

## Banco (`banco.html` + `banco.json`)

- `banco.json` ahora lo genera `scripts/banco_ejemplo.py` con **datos de ejemplo** (`"ejemplo": true`):
  objetos, iconos y precios de vendedor reales del catálogo de Blizzard, y nombres y cantidades inventados.
- Formato que la web espera:
  - `oro`: cobre en el banco.
  - `objetos`: `{id: {n, q, ico, venta (cobre), obj}}`.
  - `pestanas`: `[{nombre, ico, huecos: [{id, cant}]}]`, con 98 huecos por pestaña.
  - `registro`: `[{t, pj, clase, tipo: deposito|retirada, oro | id+cant}]`.
- El top 5 se calcula en la web: oro ingresado más objetos depositados × precio de vendedor. Las retiradas no restan.
- Fuente real (cuando se abra el banco en el juego). En la beta de Forever hay banco de hermandad, a falta de confirmar pestañas y registro en el lanzamiento.
  - Addons que ya exportan contenido y registro en Forever: Ultimate Bank (`/togbank`), GBankClassic Revived (con ranking de donaciones por valor de vendedor), Guild Bank Export (`/gbx`) y Guild Bank Logger (`/gbl export`).
  - Flujo previsto: un oficial abre el banco con el addon, exporta, y sube el texto al repo (`datos/banco/export.txt`) o lo pega en Discord con el bot. Una Action lo convierte en `banco.json`.
  - Precio de vendedor: lo da la API de Blizzard (`/data/wow/item/{id}`, `sell_price`, namespace `static-forever-eu`), cacheado por id.

## Botín (`loot.html` + `loot.json` + `scripts/epgp.py`)

- `loot.json` guarda todas las variables: EP por concepto, GP base, multiplicadores de ranura y de respuesta, calidad rara, desgaste, EP mínimo y una tabla de ejemplo.
- `scripts/epgp.py` lee `datos/botin/registro.csv` y escribe `prioridad.json`. Si `prioridad.json` existe, la web usa esos datos y quita el aviso de ejemplo.
  - Formato del CSV: `fecha,pj,clase,concepto,ranura,respuesta,calidad,motivo`.
  - Recalcula siempre desde cero y aplica el desgaste cada viernes a las 06:00 (hora de Madrid). El GP base sirve de suelo.
- Pendiente para automatizarlo del todo:
  - Asistencia: de Warcraft Logs o de wowaudit, al CSV.
  - Repartos: de la exportación del addon de consejo, al CSV.
  - Una Action semanal (viernes) que ejecute `epgp.py`.
- Bot de Discord (opcional): `/prioridad` (respuesta privada), `/botin` y `/banco buscar`. Se puede alojar en el lab, solo con conexiones salientes.
