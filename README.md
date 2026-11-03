# isaac-sim-lab

Laboratorio personal de aprendizaje de **NVIDIA Isaac Sim 6.2**: herramientas, scripts de práctica por fase y notas.

## Instalación en la máquina de Isaac Sim (una sola vez)

En el Script Editor (Window → Script Editor), pegar esta línea en una pestaña vacía y darle Run:

```python
import urllib.request as u; exec(u.urlopen("https://raw.githubusercontent.com/Thorcito/isaac-sim-lab/main/herramientas.py").read()); actualizar()
```

Eso baja todo el repo a `/isaac-sim/trabajo/repo/` y carga las herramientas.

## Uso en cada sesión

Después de cada reinicio de Isaac Sim:

```python
exec(open("/isaac-sim/trabajo/repo/herramientas.py").read())
```

Para bajar cambios nuevos del repo: `actualizar()`. Para ver todas las funciones: `ayuda()`.

## Dónde va cada cosa en la máquina

| Carpeta | Qué contiene | ¿La toca `actualizar()`? |
| --- | --- | --- |
| `/isaac-sim/trabajo/repo/` | Copia de este repo | **Sí, se reemplaza entera** |
| `/isaac-sim/trabajo/scripts/` | Scripts propios o copias modificadas | No |
| `/isaac-sim/trabajo/notas/` | Resultados, inventarios, bitácora | No |
| `/isaac-sim/trabajo/escenas/` | Escenas `.usd` | No |
| `/isaac-sim/trabajo/robots/` | URDF bajados y robots convertidos a USD | No |

Para modificar un script del repo, primero copiarlo a `scripts/`. `correr("nombre.py")` busca primero en `scripts/` y después en `repo/`.

## Estructura del repo

- `PLAN.md`: las 6 etapas del ejercicio, cada una con su criterio de "lista", la estructura del código y las decisiones tomadas
- `MAÑANA.md`: lista de comandos para la próxima sesión en la máquina
- `herramientas.py`: funciones generales (`actualizar`, `correr`, `ver`, `prims`, `medir`, `leer_celda`, `usar_celda`, `dibujar_circulo`…)
- `celda/`: lógica de la celda sin Isaac (solo Python y numpy): geometría, cinemática, recetas, tiempos, orquestador, modelo de ritmo y visión
- `faseN/`: adaptadores de cada etapa, que traducen la lógica a la escena (`fase0` orientación, `fase1` escena a escala, `fase2` robots y alcances, `fase3` banda, `fase4` ventosas)
- `pruebas/`: `probar_herramientas.py` corre en la máquina; `test_*.py` son las pruebas de `celda/` en la PC (`python -m pytest pruebas`, con numpy y pytest)
- `resultados/`: tablas, gráficos y nota generados desde la lógica (`python resultados/generar.py`, además necesita matplotlib)
- `publicar.bat`: publica los cambios locales a GitHub (Windows)

Las medidas de cada fase están en archivos `.json` dentro de su carpeta. Para experimentar, copiarlos a `/isaac-sim/trabajo/scripts/` y editar la copia: los scripts la usan en lugar de la del repo.
