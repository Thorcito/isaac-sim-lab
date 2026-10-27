# Contexto para Claude

Repo de aprendizaje de **Isaac Sim 6.2** de Thorcito (ingeniero mecatrónico, controles y automatización). Público.

## Cómo se usa

- Los scripts corren dentro del **Script Editor** de Isaac Sim, en una máquina remota que se ve por streaming web. No hay terminal interactiva, git ni pip. Sí hay internet, bash, curl y `subprocess`.
- La máquina baja este repo con `actualizar()` (tarball de GitHub) a `/isaac-sim/trabajo/repo/`. Nada sube de la máquina al repo.
- Los resultados se ven con `mostrar(texto)`: una ventana con un `ui.StringField` copiable. La salida del Script Editor no se puede copiar.
- Python 3.12.

## Reglas para escribir código aquí

- Usar la API nueva: `isaacsim.core.experimental.*`, `isaacsim.core.simulation_manager.SimulationManager`. `isaacsim.core.api` y `World` están deprecados desde la 6.0.
- Los scripts de práctica son **didácticos**: comentarios en español que expliquen el porqué, parámetros arriba en un diccionario, y un resultado visible con `mostrar()`.
- Las medidas genéricas del ejercicio van en el repo, en archivos `.json` por fase (por ejemplo `fase1/celda.json`). Los scripts buscan primero una copia en `/isaac-sim/trabajo/scripts/` para que el usuario pueda experimentar sin que `actualizar()` la pise.
- Datos que podrían ser sensibles (recetas, nombres del cliente, resultados de rendimiento): preguntar antes de subirlos. La carpeta `privado/` está bloqueada en `.gitignore` para eso.
- No desactivar ni reactivar extensiones desde scripts: congeló Isaac Sim una vez.
- Cada script nuevo debe probarse en la máquina antes de darse por bueno; marcar en su docstring si está probado.
