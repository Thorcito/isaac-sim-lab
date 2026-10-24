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

Para modificar un script del repo, primero copiarlo a `scripts/`. `correr("nombre.py")` busca primero en `scripts/` y después en `repo/`.

## Estructura del repo

- `herramientas.py`: funciones generales (`actualizar`, `correr`, `ver`, `prims`, `diagnostico`…)
- `faseN/`: scripts de práctica de cada fase del plan de aprendizaje
- `publicar.bat`: publica los cambios locales a GitHub (Windows)

Los datos de proyectos de clientes no se suben a este repo: los scripts los leen de archivos que viven solo en la máquina.
