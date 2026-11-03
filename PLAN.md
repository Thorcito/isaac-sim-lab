# Plan · Celda de encajado y paletizado en Isaac Sim 6.2

Objetivo: simular una estación de una celda con dos robots colaborativos. El **CR6AL** arma cajas desde un magazine y encaja estuches que llegan por una banda de 5 canales. El **CR20A** estiba las cajas llenas en 4 tarimas en cruz. Una cámara clasifica cada estuche. El script de Python hace de orquestador.

El plan sigue las 6 etapas del ejercicio. Cada etapa tiene su carpeta `faseN/` y un criterio de "lista" que se comprueba con un script, no a ojo.

- **Fuente única de medidas:** [`fase1/celda.json`](fase1/celda.json). En `datos` está solo lo que da el ejercicio; en `_supuestos`, todo lo demás, con su `valor` y su `razon`. Ningún script tiene medidas escritas a mano.
- **Geometría derivada:** [`fase1/piezas.py`](fase1/piezas.py) es el único lugar donde se calculan piezas, punto de toma, camadas, etc.

| Etapa | Carpeta | Estado |
| --- | --- | --- |
| 0 · Orientación (interfaz, física, ejemplos) | `fase0/` | Hecha, no cambia |
| 1 · Escena a escala | `fase1/` | Scripts listos, falta correrlos en la máquina |
| 2 · Robots y alcances | `fase2/` | Script listo, falta correrlo en la máquina |
| 3 · Producto y banda | `fase3/` | Pendiente |
| 4 · Tomar y dejar | `fase4/` | Pendiente |
| 5 · Visión | `fase5/` | Pendiente |
| 6 · Ritmo y fallas | `fase6/` | Pendiente |

---

## Etapa 1 · Escena a escala

Piso de 7,7 × 5,5 m con pasos de personal, zona de estiba de 2,7 × 2,7 m, 4 tarimas de 1,2 × 1,0 m, pedestal del CR20A, banda de 5 canales, mini-banda de 1,5 m con tope y punto de toma fijo, bahías B1 a B4, pedestal del CR6AL, magazine, pórtico con cámara, tablero, tablet y baliza. Todo en metros y con Z arriba.

- `correr("fase1/armar_escena.py")`: arma `/World/Celda` y la guarda en `escenas/etapa1/celda.usd`.
- `correr("fase1/verificar_escena.py")`: mide cada pieza y la compara con `celda.json` y con los datos del ejercicio. Revisa la tolerancia de 5 cm de las tarimas, que nada se pise y que los pasos estén libres, y dibuja los círculos de 1,7 y 1,8 m.

**Lista cuando** `verificar_escena.py` dice `ETAPA 1 LISTA` (26 controles PASA).

## Etapa 2 · Robots y alcances

URDF oficiales de Dobot (`Dobot-Arm/DOBOT_6Axis_ROS2_V4`, licencia MIT): existen el `cr20` y el `cr6al`, así que no hace falta un robot parecido ni escalar el alcance. Medido sobre la cadena del URDF, con la herramienta hacia abajo, el alcance da 1,705 m y 1,81 m.

- `correr("fase2/robots.py")`: baja URDF y mallas con urllib, los corrige (rutas, masas, esfuerzos), los importa con `isaacsim.asset.importer.urdf`, los pone sobre sus pedestales y revisa con cinemática inversa ([`fase2/cinematica.py`](fase2/cinematica.py)):
  - CR20A: la caja más lejana de la camada más alta en las 4 tarimas, con 0,10 m de aproximación; la misma con la tarima corrida 5 cm hacia afuera; la camada de abajo (lejos y cerca); el punto de toma.
  - CR6AL: las 4 esquinas del campo de la cámara sobre la banda, el magazine, y el estuche más lejano del fondo de cada bahía.
- Dibuja los círculos y cada punto (verde llega, rojo no) y guarda `escenas/etapa2/celda_robots.usd`.

**Lista cuando** `robots.py` dice `ETAPA 2 LISTA` (40 controles PASA) y, al dar Play 3 s, los robots se quedan quietos sobre sus pedestales.

## Etapa 3 · Producto y banda

- Estuches (`estuche` en `celda.json`) como cuerpos rígidos de 4 colores (`variedades`).
- Banda de 5 canales con `isaacsim.asset.gen.conveyor` (o un cuerpo cinemático que arrastre), a `banda.velocidad_m_s`.
- Generador de estuches con ritmo configurable entre 15 y 20 por minuto, canal y variedad al azar con semilla fija, y modo "una variedad por canal".
- Tope o zona de acumulación al final de la banda, frente al CR6AL.

**Lista cuando** la banda corre sola y cambiar un parámetro pasa el ritmo de 15 a 20 por minuto, medido contando estuches en 60 s de simulación.

## Etapa 4 · Tomar y dejar

- Ventosas con `isaacsim.robot.surface_gripper`: copas para estuches en el CR6AL y ventosa de área en el CR20A, con el largo y la masa de `herramientas`.
- Movimiento con `isaacsim.robot_motion` (Lula/cuMotion): hace falta generar la descripción del robot (esferas de colisión) desde el URDF. La cinemática inversa de `fase2/cinematica.py` sirve como respaldo y para validar.
- CR6AL: tomar una caja plana del magazine y dejar una caja abierta en su bahía. Simplificación aceptable: que la caja "aparezca" armada. Después encajar 36 estuches según `receta_encajado`.
- Salida de la caja llena hacia la mini-banda, tope y punto de toma.
- CR20A: estibar con el trabado de `trabado` (patrón A en camadas impares, A girado 180° en pares).
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
- **Hipótesis a comprobar:** el cuello de botella es el CR6AL. A 20 estuches por minuto tiene 3 s por estuche, y además arma una caja cada 36 estuches. El CR20A recibe una caja cada 108 s (36 / 20 por minuto), así que le sobra tiempo. La herramienta doble del CR20A (12,1 kg con dos cajas, bajo sus 20 kg) entra en peso, pero solo sirve si el CR20A resulta ser el que frena.
- Falla "falta de cartón": el magazine se vacía (`magazine.capacidad_cartones`). ¿Qué pasa con los estuches que siguen llegando?
- Falla "variedad fuera de receta": entra una quinta variedad o una duda. Decidir qué hace la celda: dejarla pasar, desviarla o detenerse con la baliza en alerta.
- Escribir la nota final en `notas/`: alcances verificados, ciclo medido, cuello de botella y qué cambiarías.

**Lista cuando** sabés cuántos estuches por minuto logra la celda y qué la frena.

---

## Decisiones y hallazgos

1. **Tarimas en molinete, separación 0,30 m.** Una cruz simple no entra en 2,7 m. El molinete anterior, con separación 0,45 m y pedestal de 0,6 m, **no llegaba** a la caja más lejana de la camada más alta (la caja queda a 1,63 m en planta). Con separación 0,45 m ninguna altura de pedestal llega a la vez arriba y abajo. Con 0,30 m el conjunto mide 2,50 m y el pedestal es de 0,40 m de lado (0,05 m de holgura = la tolerancia).
2. **Pedestal del CR20A de 1,0 m.** Con la herramienta vertical, la muñeca tiene que quedar arriba de la caja; por eso el alcance útil depende de la altura. Barrido con el URDF: con 1,0 m llega a la camada de arriba (con aproximación) y a la de abajo, se lea "estiba de 1,4 m" desde el piso o desde la tarima. Margen a la caja más lejana de arriba: solo 2 cm.
3. **URDF de Dobot con masas de prueba** (0,027 kg y 0,007 kg en total) y esfuerzos bajos. `robots.py` los reemplaza por valores de `_supuestos`. Sirven para que la simulación sea estable, no para estudiar dinámica.
4. **Malla del último link del CR6AL:** parece girada 90° respecto del eje del joint 6. No cambia el alcance; revisarlo en el viewport en la etapa 4.
5. **Bahías a los costados de la mini-banda.** El ejercicio no dice cómo sale la caja llena; se supone salida lateral hacia la mini-banda.

## Datos a confirmar con el cliente

Están en `celda.json → _supuestos`. Las preguntas abiertas son: desde dónde se mide la estiba de 1,4 m; medidas, peso y receta reales de estuches y cajas; alto de la banda existente y velocidad; cómo salen las cajas de las bahías; el magazine (capacidad y elevador); qué hacer con una variedad fuera de receta; si hay pared o algo más allá del borde del piso.
