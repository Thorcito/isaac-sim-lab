# Lista de prueba para la próxima sesión en la máquina

Cada paso dice qué correr en el Script Editor, qué tenés que ver y qué pegarme si falla. Si un paso falla, pará ahí: los siguientes dependen de él.

## 0 · En la PC, antes de abrir Isaac

Correr `publicar.bat`. Si pide usuario, entrar como **Thorcito**: el 403 de la vez pasada era por la cuenta `nalfaro-d8`.

## 1 · Cargar y actualizar

```python
exec(open("/isaac-sim/trabajo/repo/herramientas.py").read())
```
```python
actualizar()
```

- **Esperado:** la ventana "actualizar" lista archivos nuevos: `celda/recetas.py`, `celda/tiempos.py`, `fase3/banda_estuches.py`, `fase4/ventosas.py`, `MAÑANA.md`. Ya no aparecen `fase1/piezas.py` ni `fase2/cinematica.py`.
- **Si falla:** pegame el texto de la ventana.

## 2 · Prueba de herramientas

```python
correr("pruebas/probar_herramientas.py")
```

- **Esperado:** `18 de 18 pruebas OK`. La nueva es `usar_celda`: importa la lógica de `celda/` y calcula el trabado (10 cajas por camada).
- **Si falla `usar_celda`:** pegame la línea completa. Lo más probable es que falte numpy en el Python de Isaac (no debería pasar) o un error de import.

## 3 · Etapa 1 otra vez (cambió de dónde sale la geometría)

```python
correr("fase1/armar_escena.py")
```
```python
correr("fase1/verificar_escena.py")
```

- **Esperado:** `Piezas creadas: 39` y después `ETAPA 1 LISTA: 26 de 26 controles PASA`. Es la misma escena de antes. Lo único que cambió es que la geometría ahora sale de `celda/geometria.py`.
- **Si falla:** `ver("/isaac-sim/trabajo/notas/etapa1_verificacion.txt")` y pegame las líneas FALLA.

## 4 · Etapa 2 y el Play que quedó pendiente

```python
correr("fase2/robots.py")
```

- **Esperado:** tarda 1 a 2 minutos porque reimporta los dos robots. Tiene que dar `ETAPA 2 LISTA (falta probar Play): 40 de 40`, con `6 joints de rotacion` y `anclas al mundo corregidas: 1` en cada robot. El CR6AL tiene que verse entero, con dos tubos lisos en el brazo y el antebrazo.
- **Después:** **Play** durante 3 segundos y **Stop**. Los dos robots tienen que quedarse quietos sobre sus pedestales.
- **Si falla el reporte:** `ver("/isaac-sim/trabajo/notas/etapa2_alcances.txt")` y pegame todo, incluidas las líneas "Diagnostico de fisica".
- **Si falla el Play:** mandame una captura y decime qué hizo. Puede saltar al origen, caerse, temblar o estirarse. En ese caso no sigas con los pasos 5 y 6: necesitan la física del robot bien.

## 5 · Etapa 3: banda y estuches (esqueleto, primera prueba)

```python
correr("fase3/banda_estuches.py")
```

- **Esperado:** una ventana "Etapa 3: lista para Play" con `Divisores con colision: 4`. La escena queda guardada en `escenas/etapa3/celda_banda.usd`.
- **Después:** **Play** y esperar unos 60 s de simulación (en tiempo real puede ser más). Tienen que ir apareciendo estuches de 4 colores al principio de los canales. Viajan hacia el este y se juntan contra el final de la banda. A los 60 s se abre "Etapa 3: banda" con `Estuches generados: ~15 -> ~15 por minuto`.
- **Ritmo 20:** **Stop** y después:
  ```python
  t = open(REPO_DIR + "/fase3/banda_estuches.py", encoding="utf-8").read().replace('"ritmo_min": 15', '"ritmo_min": 20'); guardar("banda_20.py", t); correr("banda_20.py")
  ```
  Play de nuevo. El conteo tiene que dar unos 20 por minuto.
- **Si falla:** pegame el error del Script Editor (o una captura) y `ver("/isaac-sim/trabajo/notas/etapa3_banda.txt")`. Decime también qué ves:
  - los estuches no aparecen;
  - aparecen pero no avanzan (la banda no arrastra);
  - atraviesan la banda;
  - saltan por encima de los divisores.

## 6 · Etapa 4: ventosas (esqueleto, primera prueba)

```python
correr("fase4/ventosas.py")
```

- **Esperado:** una ventana "Etapa 4: lista para Play" que muestra:
  - las dos ventosas;
  - las raíces de articulación de cada robot;
  - la duración de cada ciclo: unos 10 s el CR6AL y unos 7 s el CR20A;
  - `Puntos sin solucion: ninguno`.

  Aparecen una caja marrón en el punto de toma y un estuche rojo contra el tope del canal 3.
- **Después:** **Play**. Primero cada robot va despacio, en 3 s, a su primer punto. Después el CR6AL toma el estuche y lo deja en la caja de B1, y el CR20A toma la caja y la deja en la tarima Norte. Al terminar se abre "Etapa 4: tomar y dejar" con cada paso y el estado de cada ventosa.
- **Si falla:** pegame el error o la ventana, y `ver("/isaac-sim/trabajo/notas/etapa4_ventosas.txt")`. Es la primera vez que corre: lo más probable es que falle algo de la API de la ventosa o de la articulación. Con el mensaje lo corrijo.

## 7 · Para la nota

Si todo lo anterior anduvo, anotá el tiempo real que tardó cada ciclo del paso 6. Se puede medir con el reloj de la simulación o mirando el log. Esos números reemplazan los `[PENDIENTE: medir en Isaac]` de `resultados/nota.md`.
