# Fase 0 · Orientación

**Duración:** unas 2 h, en una o dos sesiones.
**Objetivo:** moverse por la interfaz con soltura, entender qué hace la física al dar Play, saber qué hay dentro de un ejemplo, y comprobar que el trabajo guardado sobrevive a un apagado.
**Listo cuando:** la escena `escenas/fase0_cubo.usd` se vuelve a abrir después de Apagar y Encender la máquina, y las preguntas de la bitácora (al final) tienen respuesta.

## Antes de empezar

1. Encender la máquina y abrir Isaac Sim.
2. En el Script Editor, cargar las herramientas y actualizar:
   ```python
   exec(open("/isaac-sim/trabajo/repo/herramientas.py").read())
   ```
   ```python
   actualizar()
   ```
3. Herramientas que se usan en esta guía:
   - `escena()`: resumen de la escena (unidades, física, cuerpos, robots, joints, luces).
   - `prims()`: árbol completo de prims.

**Navegación del viewport** (convención de Omniverse; si algo no responde por el streaming, anotarlo):

| Acción | Cómo |
| --- | --- |
| Orbitar | Alt + clic izquierdo y arrastrar |
| Desplazar (pan) | Clic central y arrastrar |
| Zoom | Rueda del mouse, o Alt + clic derecho y arrastrar |
| Volar | Mantener clic derecho + W A S D Q E |
| Encuadrar lo seleccionado | F |
| Mover / Rotar / Escalar | W / E / R (Esc deselecciona) |

---

## Bloque 1 · Una escena desde cero, a mano (40 min)

La idea es construir lo mínimo para que algo caiga, y entender cada pieza.

1. **File → New.** La escena trae un `World` y una luz por defecto.
2. **Edit → Preferences → Stage.** Confirmar **Default Up Axis = Z** y **Default Meters Per Unit = 1.0**. Ese campo *es* la unidad: USD guarda números sin unidad, y `metersPerUnit` dice cuántos metros vale 1 unidad. 1.0 = metros, 0.01 = centímetros (el default de Omniverse Kit). No escala objetos. Ojo: esta pantalla define el valor para escenas *nuevas*; el de la escena abierta lo muestra `escena()` en la línea "Unidades". Un asset hecho en centímetros dentro de una escena en metros aparece 100 veces más grande.
3. **Create → Physics → Physics Scene.** Seleccionar `PhysicsScene` en el panel Stage y mirar sus propiedades. La documentación recomienda, para pocas piezas, desactivar **Enable GPU dynamics** y usar **Broadphase: MBP**.
4. **Create → Physics → Ground Plane.**
5. **Create → Shape → Cube.** En Property → Transform, poner **Translate Z = 2** (2 m de altura).
6. **Play** (flecha a la izquierda del viewport). *¿Qué pasa?* El cubo no cae, porque todavía no tiene física.
7. **Stop.** Con el cubo seleccionado: Property → **Add → Physics → Rigid Body with Colliders Preset**.
8. **Play.** Ahora cae y choca con el suelo. **Stop**: *¿dónde queda el cubo?*
9. Correr `escena()` y ubicar el cubo en "CUERPOS RIGIDOS" y el suelo en "COLISIONADORES ESTATICOS".

**Experimentos** (cada uno: Stop → cambiar → Play → observar):

- **Segundo cubo con solo colisión:** Add → Physics → **Collider** (sin Rigid Body), a 1 m. Ponerlo debajo de la trayectoria del primero. *¿Se mueve cuando lo golpean?*
- **Rotación inicial:** rotar el cubo rígido 30° en X antes de soltarlo.
- **Masa y rebote:** en Property → Physics, cambiar la masa. *¿Cambia la caída?* (pista: Galileo). Luego buscar un **Physics Material** y subir la restitución.

10. **Guardar:** File → Save As → `/isaac-sim/trabajo/escenas/fase0_cubo.usd`. Si la carpeta `escenas` no existe, crearla desde el diálogo. Después, `archivos()` para verificar que quedó guardada.

## Bloque 2 · Physics Demo "Box on a table" (20 min)

1. Abrir la pestaña **Physics Demo Scenes** → **Basics → Box on a table** → cargar.
2. Play y Stop. Correr `escena()`: *¿cuántos cuerpos rígidos hay? ¿la mesa es rígida o estática? ¿cuántos pasos de física por segundo usa?*
3. Comparar con tu escena del Bloque 1: *¿qué tiene esta que la tuya no?*
4. En el panel de la demo suele haber un botón para ver el código Python que la arma. Si está, abrirlo y ubicar dónde se crea la caja.

## Bloque 3 · Robotics Example "Hello World" (20 min)

1. **Robotics Examples → General → Hello World** → **Load**.
2. Ver el código con `codigo_ejemplo("Hello World")`: abre los archivos del ejemplo y lista sus rutas. En la 6.2 no se encontró el botón **Open Script** de la documentación.
3. Buscar en el código: *¿importa `World` o `isaacsim.core.api`?* Si sí, usa la API vieja (deprecada desde la 6.0): sirve para entender el concepto, no para copiar.
4. Correr `escena()` y `prims()` sobre lo que cargó.

## Bloque 4 · Robotics Example "UR10 Palletizing" (30 min)

Es el ejemplo más parecido a la celda del ejercicio: robot + ventosa + cajas + estiba.

1. **Robotics Examples → Manipulation → UR10 Palletizing** → **Load**, y luego el botón para iniciar la tarea.
2. Observar el ciclo completo: *¿cuántos segundos tarda en tomar y dejar una caja?* (aproximado, con reloj).
3. Correr `escena()`: anotar el robot (articulación), la cantidad y el tipo de joints, y si las cajas son cuerpos rígidos.
4. Abrir el **Robot Inspector** (pestaña junto a Stage) con el robot seleccionado y recorrer sus joints: nombres, tipo, límites.
5. Correr `prims("<ruta del robot>")`, con la ruta que mostró `escena()`, para ver su estructura interna: links, joints y dónde está la ventosa.
6. `codigo_ejemplo("UR10 Palletizing")` y ubicar dónde se decide a qué posición va cada caja.

## Bloque 5 · Persistencia (10 min)

1. Guardar todo y anotar la hora.
2. En el portal: **Apagar**, esperar a que confirme, **Encender**.
3. Abrir Isaac Sim → File → Open → `/isaac-sim/trabajo/escenas/fase0_cubo.usd`.
4. Play: *¿el cubo vuelve a caer igual?* Si sí, la **fase 0 está lista**.

---

## Bitácora (responder en el chat o copiar a `notas/fase0.md` en la máquina)

1. Al dar **Stop**, ¿qué pasa con la posición de los objetos? ¿Por qué creés que es así?
2. Diferencia observada entre: cubo sin física / con solo Collider / con Rigid Body + Collider.
3. ¿La masa cambió la velocidad de caída? ¿Qué sí cambió?
4. Pasos de física por segundo de "Box on a table" y de tu escena.
5. ¿Hello World usa la API vieja (`World`)? ¿Qué líneas lo delatan?
6. UR10 Palletizing: tiempo de ciclo aproximado, cantidad y tipo de joints, ruta del robot, dónde está la ventosa.
7. ¿Qué fue confuso o no respondió por el streaming?
