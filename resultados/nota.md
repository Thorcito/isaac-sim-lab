# Nota de resultados · Celda de encajado y paletizado (BORRADOR)

Una estación: un CR6AL que arma cajas y encaja estuches desde una banda de 5 canales, y un CR20A que estiba en 4 tarimas en molinete. Todas las medidas están en `fase1/celda.json`; lo que no da el ejercicio está en `_supuestos`, cada valor con su razón.

Estado: los números de este borrador salen de la lógica probada en la PC (`celda/`, 66 pruebas), con la cinemática de los URDF oficiales de Dobot. Lo que solo se puede medir en Isaac Sim está marcado **[PENDIENTE: medir en Isaac]**.

## 1. Alcances verificados

| Qué | Resultado | Cómo se verificó |
| --- | --- | --- |
| Alcance de los modelos | CR20A 1,705 m, CR6AL 1,810 m (datos: 1,7 y 1,8 m) | Radio máximo de la brida con la herramienta vertical, sobre el URDF |
| CR20A: las 4 tarimas, la caja más lejana de la camada más alta | Llega, con 0,10 m de aproximación | Cinemática inversa, herramienta vertical, pedestal de 1,0 m |
| CR20A: la misma caja con la tarima corrida 5 cm hacia afuera (tolerancia) | Llega | Ídem |
| CR20A: **las 200 posiciones** (4 tarimas × 5 camadas × 10 cajas), cada una con su aproximación | Llega a todas | `pruebas/test_recetas.py` |
| CR6AL: las 4 esquinas del campo de la cámara, el magazine, las 4 bahías | Llega | `fase2/robots.py` (40 de 40 en PC) |
| CR6AL: **las 144 posiciones de estuche** (4 bahías × 36), con entrada vertical a la caja | Llega a todas | `pruebas/test_recetas.py` |
| En la escena de Isaac, con los robots importados | [PENDIENTE: medir en Isaac] — `fase2/robots.py` y el Play de 3 s | |

**Riesgo:** al CR20A le sobran solo **2 cm** hacia afuera en la caja más lejana de la camada más alta. Eso cubre la tolerancia de 5 cm porque esa caja no queda en la diagonal más larga, pero no deja margen para errores de instalación del pedestal ni para un pallet más grande. Si en planta se mide la estiba de 1,4 m desde el piso y no desde la tarima, el margen mejora: hay una camada menos de altura. Es la primera pregunta para el cliente.

Para llegar se cambió el layout que salía a primera vista. Las tarimas van en molinete con 0,30 m de separación, porque una cruz simple no entra en 2,7 m. El pedestal del CR20A mide 1,0 m: con 0,6 m no llega a la camada alta.

## 2. Producto, receta y trabado

- Caja de 0,40 × 0,30 × 0,28 m, 36 estuches en 3 × 3 × 4: es la que más mete con la caja de cartón de 3 mm. Caja llena: 4,31 kg. Con la herramienta doble del CR20A, el total es 12,1 kg, bajo sus 20 kg.
- Trabado calculado por `celda/recetas.py`, que prueba todos los patrones de bloques:
  - 10 cajas por camada: 6 con el largo en X y 4 girado, 100 % de la tarima, sin voladizo;
  - la camada par es la impar girada 180°;
  - **el 100 % de las cajas apoya en dos o más cajas de abajo**, y solo 0,40 m de junta coinciden entre camadas.
  - 5 camadas: tope a 1,544 m del piso (1,4 m sobre la tarima).
  - Imágenes en `resultados/camadas/`.
- Orden de estiba: de la caja más lejana a la más cercana, para que el brazo nunca pase bajo sobre una caja recién puesta.
- Estiba real en Isaac: [PENDIENTE: medir en Isaac] — camada completa sin choques (etapa 4).

## 3. Ciclo

Tiempos del modelo (`resultados/tiempos.md`):

- perfil trapezoidal por joint con las velocidades de catálogo de Dobot y la cinemática inversa de cada punto;
- bajada y subida vertical a 0,5 m/s;
- vacío: 0,15 s para tomar y 0,10 s para soltar.

| Operación | Tiempo medio (mín-máx) |
| --- | --- |
| CR6AL, ciclo de un estuche (banda → caja → banda) | **5,8 s** (4,6-6,7) |
| CR6AL, armar una caja (magazine → abrir → bahía) | 8,5 s (7,9-8,9), incluye 4 s supuestos de abrir |
| CR6AL, desviar un estuche al rechazo | 4,6 s |
| CR20A, ciclo de una caja (punto fijo → tarima → punto fijo) | **4,8 s** (3,5-5,9) |

Ciclo medido en Isaac: [PENDIENTE: medir en Isaac] — `fase4/ventosas.py` hace un ciclo de cada robot con estos mismos ángulos y tiempos.

Por qué el CR6AL tarda tanto:

- la banda queda al oeste del robot y las bahías al este, así que J1 gira unos 150° en cada viaje;
- para encajar, el estuche baja hasta 0,31 m dentro de la caja, y eso se hace lento.

## 4. Cuello de botella

Modelo de eventos discretos (`resultados/ritmo.md` y `ritmo.png`): una hora medida, 5 semillas, el orquestador de `celda/orquestador.py` decidiendo en cada momento.

| Configuración | Llegan 15/min | Llegan 20/min | Cuello |
| --- | --- | --- | --- |
| Actual: 1 copa, variedades mezcladas | 10,0 encajados/min (300 perdidos/h) | 10,0 (601 perdidos/h) | **CR6AL al 100 %** |
| 3 copas que toman de a una | 14,0 | 14,0 | CR6AL al 100 % |
| Herramienta doble en el CR20A | 10,0 | 10,0 | No cambia nada: el CR20A está al 2 % |
| **Propuesta: una variedad por canal + fila de 3 copas** | **14,9** | **19,9** | Ninguno: sigue el ritmo, CR6AL al 54 % y 72 % |

- **Cuello de botella: el CR6AL.** Tal como está planteada, la celda no llega ni a 15 estuches por minuto. El CR20A recibe una caja cada 2 a 4 minutos y está quieto más del 95 % del tiempo.
- La herramienta doble del CR20A no hace falta.
- Con la propuesta, una fila de 3 estuches de la misma variedad se toma con una sola bajada y se deja con una sola bajada: es una fila entera de la caja (3 × 0,13 m). El ciclo queda casi igual, pero mueve 3 estuches.
- Ritmo medido en Isaac: [PENDIENTE: medir en Isaac] — conteo de 60 s de `fase3/banda_estuches.py`, y después el ciclo completo con los dos robots.

## 5. Fallas

Escenarios de la propuesta a 20/min, con la política recomendada (`celda.json → politica_fallas`):

| Falla | Qué pasa | Resultado |
| --- | --- | --- |
| Falta de cartón: 10 cartones y el operador repone 5 min después de vaciarse | Las variedades con caja abierta siguen; la que se queda sin caja acumula en su canal | 19,6/min; 20 estuches perdidos en la hora; baliza amarilla |
| Variedad fuera de receta (5 %) | La visión la marca "desconocida"; el CR6AL la deja en el cajón de rechazo | 18,9/min (de 19 que son de receta); 63 desviados; ninguna mal encajada |
| 5 % de dudas de la cámara | Se desvían igual que las desconocidas | 18,9/min; 61 desviados |
| Mezcla desbalanceada (55/25/15/5 %) | El canal que sobra se asigna a la variedad más frecuente | 19,9/min, sin pérdidas |

Con la configuración actual las fallas casi no se notan en el ritmo, porque el CR6AL ya está saturado. Por eso se evalúan sobre la propuesta.

Política para lo que el ejercicio no define (configurable: `desviar`, `dejar_pasar` o `detener`):

- **Duda o variedad desconocida → desviar** al cajón de rechazo, que se agrega al sur del final de la banda. Cuesta un ciclo del CR6AL, unos 4,6 s, pero no para la línea.
- **5 rechazos seguidos → detener** con la baliza en rojo: algo anda mal (luz, cámara o receta equivocada).
- **Sin cartón → seguir** con las otras variedades. La baliza avisa con 5 cartones; en el escenario de falla ese aviso se apagó a propósito.
- `dejar_pasar` sería mejor para el ritmo, pero hace falta una compuerta al final de cada canal.
- En Isaac: [PENDIENTE: medir en Isaac] — etapa 6 con el orquestador corriendo contra la escena.

**Visión** (`resultados/vision.md`). Imágenes sintéticas de los 5 canales con ruido, cambios de brillo, estuches tocándose y dos colores fuera de receta:

- **Luz normal:** 100 % de aciertos y ningún falso. Error de posición medio de 0,8 mm.
- **Luz difícil:** aparecen dudas (5 % de los estuches de receta) y algún estuche no se detecta con muy poca luz, pero **ningún estuche se clasifica como otra variedad**.
- **Naranja, entre rojo y amarillo:** queda como desconocido o en duda, nunca como A o C.
- Con imágenes de la cámara de Isaac: [PENDIENTE: medir en Isaac].

## 6. Qué cambiaría

1. **Pedir que la línea mande una variedad por canal** y usar una herramienta de 3 copas en línea en el CR6AL. Es lo único del modelo que llega a 20 por minuto con margen. Si la línea no puede, hace falta otra solución para el CR6AL:
   - acercar las bahías a la banda, para que J1 gire menos;
   - o poner un segundo robot encajador.
2. **Revisar el campo de la cámara.** Los 67 × 56 cm valen sobre la banda; sobre los estuches el campo mide 63 × 53 cm y los canales 66 cm. Subiría la cámara a unos 1,25 m o correría el campo 2 cm aguas abajo, para que el estuche detenido contra el tope se vea entero.
3. **Confirmar desde dónde se mide la estiba de 1,4 m.** Con la lectura más exigente, el CR20A llega con solo 2 cm de margen.
4. **Agregar cajón de rechazo o compuerta.** Sin eso, una duda tapa su canal hasta que alguien la saque.
5. **Pedir a Dobot los datos del CR6AL** (velocidades y aceleraciones por joint). El ciclo de 5,8 s usa estimaciones de la serie CRA, y todo el resultado depende de ese número.
