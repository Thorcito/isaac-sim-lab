# Fase 1 · USD y escena a escala

**Duración:** unas 2,5 h, en una o dos sesiones.
**Objetivo:** entender cómo está hecha una escena por dentro (prims, grupos, transformadas, unidades, referencias) y construir el layout de la celda a escala real desde un archivo de medidas.
**Listo cuando:** `verificar_escena.py` dice **ETAPA 1 LISTA** (todo PASA), la escena queda guardada en `escenas/etapa1/celda.usd`, y la bitácora (al final) tiene respuesta. Esta fase es la etapa 1 del ejercicio (ver `PLAN.md`).

## Antes de empezar

1. Cargar las herramientas y actualizar:
   ```python
   exec(open("/isaac-sim/trabajo/repo/herramientas.py").read())
   ```
   ```python
   actualizar()
   ```
2. Las medidas de la celda están en `fase1/celda.json`. Leerlas con `ver(REPO_DIR + "/fase1/celda.json")`. La sección `datos` trae solo lo que da el ejercicio; todo lo de `_supuestos` es estimación, con su `valor` y su `razon`.
3. Herramienta nueva de esta fase: **`medir("/ruta")`** da el tamaño, el centro y los límites reales de cualquier prim, en metros. Acepta varias rutas: `medir("/World/A", "/World/B")`.

---

## Bloque 1 · Anatomía de un prim, a mano (30 min)

Una escena USD es un **árbol de prims**. Cada prim tiene un tipo (Xform, Cube, Mesh, Camera…), una ruta (`/World/Grupo/Cubo`) y atributos.

1. **File → New.**
2. **Create → Xform.** Renombrarlo a `Grupo` (doble clic en el panel Stage).
3. **Create → Shape → Cube.** En el panel Stage, **arrastrar el cubo sobre `Grupo`** para que quede como hijo.
4. Con el cubo seleccionado, mirar **Property → Transform**: Translate, Orient (rotación) y Scale.
5. **Mover el `Grupo`** 2 m en Y. *¿Se movió el cubo? ¿Cambió el Translate del cubo en Property?*
6. Correr `medir("/World/Grupo/Cube")`. *¿El centro que da `medir` coincide con el Translate del cubo? ¿Por qué no?*
7. **Size vs Scale:** el cubo tiene un atributo **Size** (en Property, con el resto de los atributos del cubo). Probar:
   - Size = 2, Scale = 1, y correr `medir()`.
   - Size = 1, Scale = 2, y correr `medir()`.

   *¿Se ven igual? ¿Qué dato cambió en cada caso?*
8. Guardar como **texto**: File → Save As → `/isaac-sim/trabajo/escenas/fase1/a_mano.usda` (con extensión **.usda**, no .usd).
9. `ver("/isaac-sim/trabajo/escenas/fase1/a_mano.usda")`: así se ve una escena por dentro. Buscar `def Xform "Grupo"`, el `def Cube`, `xformOp:translate` y `xformOpOrder`.

## Bloque 2 · Lo mismo en código (20 min)

1. `correr("fase1/primeros_prims.py")`. Crea `/World/Practica` con dos cajas dentro de un grupo, mueve el grupo y abre dos ventanas:
   - **Primeros prims:** posición local contra posición de mundo de cada caja, y el orden de sus transformaciones.
   - **Visor:** el `.usda` resultante.
2. Leer el script con `ver("/isaac-sim/trabajo/repo/fase1/primeros_prims.py")` y ubicar cada paso del Bloque 1 en el código:
   - `UsdGeom.Xform.Define`: crear un grupo.
   - `AddTranslateOp().Set(...)`: mover.
   - `AddScaleOp`: dar medidas.
   - `CreateDisplayColorAttr`: color simple, sin material.
3. **Experimento:** copiar el script a tu espacio para modificarlo sin que `actualizar()` lo pise:
   ```python
   import shutil; shutil.copy(REPO_DIR + "/fase1/primeros_prims.py", MIS_SCRIPTS + "/mis_prims.py")
   ```
   Abrirlo en el Script Editor (File → Open), cambiar el orden de las operaciones de la `CajaB` (poner `AddRotateXYZOp` antes que `AddTranslateOp`), guardar y correr `correr("mis_prims.py")`. *¿Dónde quedó la caja?*

## Bloque 3 · Una tarima a mano (25 min)

Construir una tarima de **1,2 × 1,0 m** con piezas, usando un Xform `Tarima` como grupo:

- 3 largueros (patines) a lo largo de 1,2 m.
- 5 o más tablas de cubierta encima.
- Altura total de unos 0,14 a 0,15 m. Los espesores los decidís vos.

**Listo cuando:** `medir("/World/Tarima")` da 1,200 × 1,000 en X e Y (o al revés).

Guardar como `/isaac-sim/trabajo/escenas/fase1/tarima.usda`.

## Bloque 4 · Referencias: un modelo, muchas copias (20 min)

1. **File → New.**
2. En el panel **Content**, ir a `/isaac-sim/trabajo/escenas/fase1/` y **arrastrar `tarima.usda` al viewport 4 veces**. Ubicar cada copia en un lugar distinto.
3. Seleccionar una copia y mirar en Property: tiene una **referencia** (o un **payload**) a `tarima.usda`. En tus Preferences, el método de arrastre (Drag & Drop USD Method) está en **payload**. Un payload es una referencia que se puede descargar para aliviar escenas pesadas; para esta prueba se comportan igual.
4. Guardar esta escena como `escenas/fase1/cuatro_tarimas.usda`.
5. Abrir `tarima.usda`, cambiar algo visible (agregar una tabla, cambiar el alto) y guardar.
6. Volver a abrir `cuatro_tarimas.usda`. *¿Cambiaron las 4 copias?*

Así se arma la celda real: los robots, las tarimas y las cajas son archivos aparte, referenciados desde una escena principal.

## Bloque 5 · Escena a escala de la celda (40 min)

1. `correr("fase1/armar_escena.py")`. Abre una escena **nueva** (guardá antes lo que tengas abierto), crea `/World/Celda` y la guarda en `escenas/etapa1/celda.usd`:
   - Piso, pasos de personal (verde) y zona de estiba (amarillo).
   - 4 tarimas en molinete y el pedestal del CR20A.
   - Banda de 5 canales, mini-banda con tope y punto de toma, bahías B1 a B4, pedestal del CR6AL y magazine.
   - Pórtico con la cámara y su campo pintado sobre la banda; tablero, tablet y baliza.
2. `correr("fase1/verificar_escena.py")`. Mide cada pieza con `medidas()` (lo mismo que usa `medir()`), la compara con `celda.json` y con los datos del ejercicio, y dibuja los círculos de alcance. Debe decir **ETAPA 1 LISTA**. El reporte queda en `notas/etapa1_verificacion.txt`.
3. Recorrer la jerarquía en el panel Stage. Ocultar y mostrar grupos con el ojo. Usar `medir()` en lo que te interese verificar a mano.
4. Leer la parte **INFORMATIVO**: distancias en planta. La esquina más lejana de las tarimas queda más lejos que 1,7 m; la etapa 2 muestra por qué igual llega.
5. **Cambiar un dato y verificar.** Los scripts usan tu copia `scripts/celda.json` si existe, y si no la del repo. Así podés experimentar sin que `actualizar()` pise tus cambios. Por ejemplo, correr la tarima Norte 5 cm hacia el pedestal:
   ```python
   import json; p = MIS_SCRIPTS + "/celda.json"; d = json.load(open(REPO_DIR + "/fase1/celda.json", encoding="utf-8")); d["_supuestos"]["tarimas"]["valor"]["Norte"]["centro"] = [5.35, 3.45]; json.dump(d, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False); correr("fase1/armar_escena.py"); correr("fase1/verificar_escena.py")
   ```
   *¿Qué control falla y por qué?* La línea "Datos:" dice qué archivo se usó. Para volver a los valores originales, borrar la copia y regenerar:
   ```python
   os.remove(MIS_SCRIPTS + "/celda.json"); correr("fase1/armar_escena.py"); correr("fase1/verificar_escena.py")
   ```
6. Los círculos son dibujo de depuración, no prims: no se guardan en la escena. Se borran con `limpiar_dibujos()`.

---

## Bitácora (responder en el chat)

1. **Size vs Scale:** ¿se ven igual? ¿Qué dato cambia en Property y en el `.usda` en cada caso? ¿Cuál conviene para que la escena "diga" las medidas reales?
2. Al mover el `Grupo`, ¿qué pasó con la posición **local** del cubo y con su posición de **mundo**?
3. ¿En qué orden aplica USD translate, rotate y scale? ¿Qué pasó en el experimento del Bloque 2 al cambiar el orden?
4. **Tarimas:** ¿por qué la escena las acomoda en **molinete** y no en una cruz simple (una tarima centrada a cada lado del pedestal)? Calculá el lado que necesitaría la cruz simple sin que se toquen las esquinas y comparalo con la zona de estiba.
5. La verificación dice que la esquina más lejana de las tarimas está a 1,77 m en planta, más que el alcance del CR20A. ¿Es necesariamente un problema? ¿Qué falta considerar? Pistas: dónde cae el centro de la caja más lejana, la altura de la camada y la altura del pedestal. Se resuelve en la etapa 2 (`fase2/robots.py`).
6. **Referencias:** después de cambiar `tarima.usda`, ¿cambiaron las 4 copias? ¿Qué ventaja da esto para la celda?
7. De la lista `_supuestos` de `celda.json`, ¿cuáles le pedirías a Fundametl que confirme?
8. ¿Qué fue confuso o no respondió por el streaming?
