# Plan · Celda de encajado y paletizado en Isaac Sim 6.2

Objetivo: simular una estación de una celda con dos robots colaborativos. El **CR6AL** arma cajas desde un magazine y encaja estuches que llegan por una banda de 5 canales. El **CR20A** estiba las cajas llenas en 4 tarimas en cruz. Una cámara clasifica cada estuche. El script de Python hace de orquestador.

El plan sigue las 6 etapas del ejercicio. Cada etapa tiene su carpeta `faseN/` y un criterio de "lista" que se comprueba con un script, no a ojo.

- **Fuente única de medidas:** [`fase1/celda.json`](fase1/celda.json). En `datos` está solo lo que da el ejercicio; en `_supuestos`, todo lo demás, con su `valor` y su `razon`. Ningún script tiene medidas escritas a mano.
- **Geometría derivada:** [`celda/geometria.py`](celda/geometria.py) es el único lugar donde se calculan piezas, punto de toma, camadas, etc.

## Estructura: lógica separada de Isaac

La celda se divide en dos capas:

| Capa | Dónde | Qué puede importar | Cómo se prueba |
| --- | --- | --- | --- |
| **Lógica** | [`celda/`](celda/) | Solo stdlib de Python y numpy. Nada de `isaacsim`, `omni` ni `pxr` | En la PC con pytest: `python -m pytest pruebas` |
| **Adaptadores** | `faseN/` | Isaac Sim 6.2 y `celda/` | En la máquina, con `correr(...)` |

Un adaptador lee `celda.json`, le pide a la lógica qué hacer (piezas, ángulos, tiempos, acciones) y lo traduce a la escena: prims, joints, ventosas, cámara. Así casi todo se prueba sin la máquina. Lo que solo puede fallar en Isaac (APIs, física, render) queda en archivos cortos.

En la máquina, `usar_celda()` (de `herramientas.py`) deja importable el paquete y lo recarga después de cada `actualizar()`: `usar_celda(); from celda import recetas`.

| Módulo de `celda/` | Qué resuelve |
| --- | --- |
| `datos.py` | Lee `celda.json` y los URDF (en la PC; en la máquina se usa `leer_celda()`) |
| `geometria.py` | Piezas de la escena, punto de toma, cajas de cada camada (antes `fase1/piezas.py`) |
| `cinematica.py` | Cinemática directa e inversa desde el URDF (antes `fase2/cinematica.py`) |
| `recetas.py` | Estuches dentro de la caja, trabado de camadas, orden de estiba |
| `tiempos.py` | Tiempo de cada movimiento: trapecio por joint con la IK real, vacío y aproximación |
| `llegadas.py` | Ritmo, variedad y canal de cada estuche (lo comparten el modelo y la etapa 3) |
| `orquestador.py` | Máquina de estados: qué hace cada robot y cómo reacciona a cada falla |
| `modelo_ritmo.py` | Simulación de eventos discretos de la estación (motor propio, sin simpy) |
| `vision.py` | HSV, confianza, duda, centroide, orientación y píxel a metros; imágenes sintéticas |

Las pruebas viven en `pruebas/test_*.py` (y `pruebas/probar_herramientas.py` sigue siendo la prueba de la máquina). Los resultados de la lógica se regeneran con `python resultados/generar.py` y quedan en [`resultados/`](resultados/).

| Etapa | Carpeta | Estado |
| --- | --- | --- |
| 0 · Orientación (interfaz, física, ejemplos) | `fase0/` | Hecha, no cambia |
| 1 · Escena a escala | `fase1/` | Armada en la máquina; volver a verificar tras el paso a `celda/` (en PC: 26 de 26) |
| 2 · Robots y alcances | `fase2/` | Falta el Play con la física corregida (ver `MAÑANA.md`) |
| 3 · Producto y banda | `fase3/` | Esqueleto `banda_estuches.py`, sin probar en la máquina |
| 4 · Tomar y dejar | `fase4/` | Esqueleto `ventosas.py`, sin probar; recetas y trabado listos en `celda/` |
| 5 · Visión | `fase5/` | Lógica lista en `celda/vision.py`; falta el adaptador de la cámara |
| 6 · Ritmo y fallas | `fase6/` | Modelo de ritmo y orquestador listos en `celda/`; falta medir en Isaac |

---

## Etapa 1 · Escena a escala

Piso de 7,7 × 5,5 m con pasos de personal, zona de estiba de 2,7 × 2,7 m, 4 tarimas de 1,2 × 1,0 m, pedestal del CR20A, banda de 5 canales, mini-banda de 1,5 m con tope y punto de toma fijo, bahías B1 a B4, pedestal del CR6AL, magazine, pórtico con cámara, tablero, tablet y baliza. Todo en metros y con Z arriba.

- `correr("fase1/armar_escena.py")`: arma `/World/Celda` y la guarda en `escenas/etapa1/celda.usd`.
- `correr("fase1/verificar_escena.py")`: mide cada pieza y la compara con `celda.json` y con los datos del ejercicio. Revisa la tolerancia de 5 cm de las tarimas, que nada se pise y que los pasos estén libres, y dibuja los círculos de 1,7 y 1,8 m.

**Lista cuando** `verificar_escena.py` dice `ETAPA 1 LISTA` (26 controles PASA).

## Etapa 2 · Robots y alcances

URDF oficiales de Dobot (`Dobot-Arm/DOBOT_6Axis_ROS2_V4`, licencia MIT): existen el `cr20` y el `cr6al`, así que no hace falta un robot parecido ni escalar el alcance. Medido sobre la cadena del URDF, con la herramienta hacia abajo, el alcance da 1,705 m y 1,81 m.

- `correr("fase2/robots.py")`: baja URDF y mallas con urllib, los corrige (rutas, masas, esfuerzos), los importa con `isaacsim.asset.importer.urdf`, los pone sobre sus pedestales y revisa con cinemática inversa ([`celda/cinematica.py`](celda/cinematica.py)):
  - CR20A: la caja más lejana de la camada más alta en las 4 tarimas, con 0,10 m de aproximación; la misma con la tarima corrida 5 cm hacia afuera; la camada de abajo (lejos y cerca); el punto de toma.
  - CR6AL: las 4 esquinas del campo de la cámara sobre la banda, el magazine, y el estuche más lejano del fondo de cada bahía.
- Dibuja los círculos y cada punto (verde llega, rojo no) y guarda `escenas/etapa2/celda_robots.usd`.

**Lista cuando** `robots.py` dice `ETAPA 2 LISTA` (40 controles PASA) y, al dar Play 3 s, los robots se quedan quietos sobre sus pedestales.

## Etapa 3 · Producto y banda

- Estuches (`estuche` en `celda.json`) como cuerpos rígidos de 4 colores (`variedades`).
- Banda de 5 canales con `isaacsim.asset.gen.conveyor` (o un cuerpo cinemático que arrastre), a `banda.velocidad_m_s`.
- Generador de estuches con ritmo configurable entre 15 y 20 por minuto, canal y variedad al azar con semilla fija, y modo "una variedad por canal".
- Tope o zona de acumulación al final de la banda, frente al CR6AL.

Esqueleto: `correr("fase3/banda_estuches.py")` y Play. Usa `create_conveyor_belt` (el comando `CreateConveyorBelt` está deprecado en 6.2) y el generador de `celda/llegadas.py`.

**Lista cuando** la banda corre sola y cambiar un parámetro pasa el ritmo de 15 a 20 por minuto, medido contando estuches en 60 s de simulación.

## Etapa 4 · Tomar y dejar

- Ventosas con `isaacsim.robot.surface_gripper`: copas para estuches en el CR6AL y ventosa de área en el CR20A, con el largo y la masa de `herramientas`.
- Movimiento con `isaacsim.robot_motion` (Lula/cuMotion): hace falta generar la descripción del robot (esferas de colisión) desde el URDF. La cinemática inversa de `fase2/cinematica.py` sirve como respaldo y para validar.
- CR6AL: tomar una caja plana del magazine y dejar una caja abierta en su bahía. Simplificación aceptable: que la caja "aparezca" armada. Después encajar 36 estuches según `receta_encajado`.
- Salida de la caja llena hacia la mini-banda, tope y punto de toma.
- CR20A: estibar con el trabado que calcula `celda/recetas.py`: 10 cajas por camada en molinete, la camada par es la impar girada 180°, el 100 % de las cajas puentean. El orden va de la caja más lejana a la más cercana. Las imágenes están en `resultados/camadas/`.
- Esqueleto: `correr("fase4/ventosas.py")` crea las dos ventosas y hace un ciclo de tomar y dejar por robot con los ángulos y tiempos de `celda/`.
- Choques: revisar el brazo contra las pilas altas y la zona compartida entre los dos círculos (se solapan 0,25 m cerca del punto de toma).

**Lista cuando** se llena una caja y se completa una camada de 10 cajas sin choques.

## Etapa 5 · Visión

- Cámara con `isaacsim.sensors.camera`: lente de 12 mm, sensor de 6,71 × 5,61 mm y 2448 × 2048 px, a 1,2 m sobre la banda. Con eso el campo da 67 × 56 cm.
- Clasificación por color (HSV) con una confianza; por debajo de `vision_umbral_confianza` el estuche queda en **duda**. Agregar ruido de iluminación o mezcla de colores para que aparezcan dudas reales.
- De píxel a posición en la banda con los intrínsecos de la cámara, y de ahí la orden al CR6AL.
- Registro de aciertos, dudas y errores contra la variedad real de cada estuche.

**Lista cuando** la celda decide sola a qué bahía va cada estuche y hay un conteo de aciertos y dudas.

## Etapa 6 · Ritmo y fallas

- Medir el tiempo de cada operación (toma de estuche, armado de caja, salida, estiba) y los estuches por minuto que logra la celda.
- **Hipótesis confirmada por el modelo de ritmo** (`resultados/ritmo.md`): el cuello de botella es el CR6AL. Con una copa, el ciclo de un estuche dura unos 5,8 s: J1 gira unos 150° entre la banda y las bahías, y el estuche baja hasta 0,31 m dentro de la caja. Así logra unos 10 estuches por minuto, aunque lleguen 15 o 20. El CR20A queda al 2-4 % de ocupación, y la herramienta doble no cambia nada.
- **Propuesta:** una variedad por canal y una herramienta de 3 copas en línea que toma y deja una fila entera de la caja (3 estuches de 0,13 m). Sigue los 20 por minuto con el CR6AL al 72 %. Depende de que la línea pueda mandar una variedad por canal: es pregunta para el cliente.
- Falla "falta de cartón": el magazine se vacía (`magazine.capacidad_cartones`). ¿Qué pasa con los estuches que siguen llegando?
- Falla "variedad fuera de receta": entra una quinta variedad o una duda. Decidir qué hace la celda: dejarla pasar, desviarla o detenerse con la baliza en alerta.
- Política de fallas configurable en `celda.json → politica_fallas` (desviar, dejar pasar o detener) y aplicada por `celda/orquestador.py`.
- Borrador de la nota final: [`resultados/nota.md`](resultados/nota.md), con los huecos marcados `[PENDIENTE: medir en Isaac]`.

**Lista cuando** sabés cuántos estuches por minuto logra la celda y qué la frena.

---

## Decisiones y hallazgos

1. **Tarimas en molinete, separación 0,30 m.** Una cruz simple no entra en 2,7 m. El molinete anterior, con separación 0,45 m y pedestal de 0,6 m, **no llegaba** a la caja más lejana de la camada más alta (la caja queda a 1,63 m en planta). Con separación 0,45 m ninguna altura de pedestal llega a la vez arriba y abajo. Con 0,30 m el conjunto mide 2,50 m y el pedestal es de 0,40 m de lado (0,05 m de holgura = la tolerancia).
2. **Pedestal del CR20A de 1,0 m.** Con la herramienta vertical, la muñeca tiene que quedar arriba de la caja; por eso el alcance útil depende de la altura. Barrido con el URDF: con 1,0 m llega a la camada de arriba (con aproximación) y a la de abajo, se lea "estiba de 1,4 m" desde el piso o desde la tarima. Margen a la caja más lejana de arriba: solo 2 cm.
3. **URDF de Dobot con masas de prueba** (0,027 kg y 0,007 kg en total) y esfuerzos bajos. `robots.py` los reemplaza por valores de `_supuestos`. Sirven para que la simulación sea estable, no para estudiar dinámica.
4. **Malla del último link del CR6AL:** parece girada 90° respecto del eje del joint 6. No cambia el alcance; revisarlo en el viewport en la etapa 4.
5. **Bahías a los costados de la mini-banda.** El ejercicio no dice cómo sale la caja llena; se supone salida lateral hacia la mini-banda.
6. **Trabado calculado, no escrito a mano.** `celda/recetas.py` prueba patrones de bloques y elige la pareja impar/par que más traba. Para la caja de 0,40 × 0,30 sale el mismo molinete de 10 cajas que antes estaba en `celda.json`.
7. **Cuello de botella en el CR6AL** (modelo de ritmo): ver Etapa 6. Es el hallazgo más importante para el cliente.
8. **Campo de la cámara justo.** Los 67 × 56 cm del dato valen sobre la banda. Sobre la cara de arriba de los estuches (6,5 cm más cerca) el campo mide 63,4 × 53,1 cm, y los 5 canales ocupan 66 cm. Un estuche pegado a la pared de un canal exterior queda en parte fuera, y el estuche contra el tope queda 1 cm fuera del borde del campo. La visión lo marca como duda, no lo ignora. Arreglos posibles: subir la cámara a unos 1,25 m o correr el campo 2 cm aguas abajo.

## Datos a confirmar con el cliente

Están en `celda.json → _supuestos`. Las preguntas abiertas son: desde dónde se mide la estiba de 1,4 m; medidas, peso y receta reales de estuches y cajas; alto de la banda existente y velocidad; cómo salen las cajas de las bahías; el magazine (capacidad y elevador); qué hacer con una variedad fuera de receta; si hay pared o algo más allá del borde del piso. Las preguntas nuevas, salidas del modelo:

- ¿La línea puede mandar **una variedad por canal**? De eso depende llegar a 20 por minuto.
- Velocidades del CR6AL: no hay hoja de datos pública; se usaron las de la serie CRA. Pedir también las aceleraciones de los dos robots.
- ¿Se puede agregar una **compuerta o un cajón de rechazo** al final de la banda?
- ¿Cuánto tarda en la práctica abrir una caja plana con vacío y plegar el fondo? Se supuso 4 s.
- ¿Los 67 × 56 cm de campo de la cámara se midieron sobre la banda o sobre el producto?
