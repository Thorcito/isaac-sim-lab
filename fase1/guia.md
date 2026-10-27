# Fase 1 · USD y escena a escala

**Duración:** unas 2,5 h, en una o dos sesiones.
**Objetivo:** entender cómo está hecha una escena por dentro (prims, grupos, transformadas, unidades, referencias) y construir el layout de la celda a escala real desde un archivo de medidas.
**Listo cuando:** `layout.py` muestra **todas las verificaciones en OK**, la escena queda guardada en `escenas/fase1/celda_layout.usd`, y la bitácora (al final) tiene respuesta.

## Antes de empezar

1. Cargar las herramientas y actualizar:
   ```python
   exec(open("/isaac-sim/trabajo/repo/herramientas.py").read())
   ```
   ```python
   actualizar()
   ```
2. Las medidas de la celda están en `fase1/celda.json`. Leerlas con `ver(REPO_DIR + "/fase1/celda.json")`. Los valores de la lista `_supuestos` no vienen del ejercicio: son estimaciones para poder armar el layout.
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

## Bloque 5 · Layout paramétrico de la celda (40 min)

1. **File → New**, y después `correr("fase1/layout.py")`.
2. Se crea `/World/Celda`:
   - Piso.
   - Zona de estiba con líneas pintadas, 4 tarimas, pedestal y base del CR20A.
   - Zona de alimentación: banda de 5 canales, magazine, base del CR6AL, bahías, mini-banda y punto de toma.
   - Marcador de la cámara con su campo de visión pintado sobre la banda.
3. La ventana **Layout: verificación** mide la escena ya construida y la compara con los datos. Debe dar **todo OK**.
4. Recorrer la jerarquía en el panel Stage. Ocultar y mostrar grupos con el ojo. Usar `medir()` en lo que te interese verificar a mano.
5. Leer la parte de **distancias informativas** y la lista de **supuestos**: son medidas que el ejercicio no da y que el script asume.
6. **Cambiar un parámetro y regenerar.** `layout.py` usa tu copia `scripts/celda.json` si existe, y si no la del repo. Así podés experimentar sin que `actualizar()` pise tus cambios. Por ejemplo, la separación entre tarimas:
   ```python
   import json; p = MIS_SCRIPTS + "/celda.json"; d = json.load(open(REPO_DIR + "/fase1/celda.json")); d["tarimas_molinete"]["separacion"] = 0.30; json.dump(d, open(p, "w"), indent=2, ensure_ascii=False); correr("fase1/layout.py")
   ```
   *¿Qué verificación falla y por qué?* La primera línea de la ventana dice qué archivo de datos usó. Para volver a los valores originales, borrar la copia y regenerar:
   ```python
   os.remove(MIS_SCRIPTS + "/celda.json"); correr("fase1/layout.py")
   ```
7. Guardar como `/isaac-sim/trabajo/escenas/fase1/celda_layout.usd`.

---

## Bitácora (responder en el chat)

1. **Size vs Scale:** ¿se ven igual? ¿Qué dato cambia en Property y en el `.usda` en cada caso? ¿Cuál conviene para que la escena "diga" las medidas reales?
2. Al mover el `Grupo`, ¿qué pasó con la posición **local** del cubo y con su posición de **mundo**?
3. ¿En qué orden aplica USD translate, rotate y scale? ¿Qué pasó en el experimento del Bloque 2 al cambiar el orden?
4. **Tarimas:** ¿por qué `layout.py` las acomoda en **molinete** y no en una cruz simple (una tarima centrada a cada lado del pedestal)? Calculá el lado que necesitaría la cruz simple con un pedestal de 0,5 m y comparalo con la zona de estiba.
5. La verificación dice que la esquina más lejana de las tarimas está a más distancia que el alcance del CR20A, medida en planta. ¿Es necesariamente un problema? ¿Qué falta considerar? Pistas: dónde cae el centro de la caja más lejana, la altura de la camada y la altura del pedestal. Se resuelve en la fase 3.
6. **Referencias:** después de cambiar `tarima.usda`, ¿cambiaron las 4 copias? ¿Qué ventaja da esto para la celda?
7. De la lista `_supuestos` de `celda.json`, ¿cuáles le pedirías a Fundametl que confirme?
8. ¿Qué fue confuso o no respondió por el streaming?
