"""Prueba todas las funciones de herramientas.py y muestra un resumen.

Uso (con las herramientas ya cargadas):
    correr("pruebas/probar_herramientas.py")

Abre y cierra varias ventanas; al final queda solo "Prueba de herramientas".
No modifica la escena: prims() solo la lee. Crea y borra un archivo temporal en scripts/.
"""
import os, traceback

resultados = []


def probar(nombre, fn, verificar=None):
    """Corre fn(); si devuelve una ventana la cierra. verificar(resultado) -> texto de detalle o error."""
    try:
        r = fn()
        detalle = verificar(r) if verificar else ""
        resultados.append(f"OK    {nombre}  {detalle}")
    except Exception as e:
        resultados.append(f"FALLA {nombre}: {e}\n      " + traceback.format_exc().strip().splitlines()[-1])


def ventana_ok(w):
    if w is None or not hasattr(w, "visible"):
        raise RuntimeError("no devolvio una ventana")
    w.visible = False   # se cierra para no llenar la pantalla
    return "(ventana creada)"


# 1. mostrar
probar("mostrar", lambda: mostrar("prueba", "_prueba_mostrar"), ventana_ok)

# 2. ver: lee el README del repo
probar("ver", lambda: ver(REPO_DIR + "/README.md"), ventana_ok)

# 3. archivos
probar("archivos", lambda: archivos(TRABAJO), ventana_ok)

# 4. guardar: escribe un script temporal en scripts/
TMP = "_prueba_tmp.py"
def _guardar():
    w = guardar(TMP, "RESULTADO_PRUEBA_CORRER = 42\n")
    if not os.path.isfile(os.path.join(MIS_SCRIPTS, TMP)):
        raise RuntimeError("el archivo no se creo")
    return w
probar("guardar", _guardar, ventana_ok)

# 5. correr: ejecuta el script temporal y revisa que haya definido la variable
def _correr():
    correr(TMP)
    if globals().get("RESULTADO_PRUEBA_CORRER") != 42:
        raise RuntimeError("el script corrio pero no definio la variable")
    os.remove(os.path.join(MIS_SCRIPTS, TMP))
    return "(script temporal corrido y borrado)"
probar("correr", _correr)

# 6. diagnostico
probar("diagnostico", diagnostico, ventana_ok)

# 7. inventario_ejemplos (sin reescribir el txt)
probar("inventario_ejemplos", lambda: inventario_ejemplos(guardar_txt=False), ventana_ok)

# 8. inspeccionar
import omni.ui as _ui
probar("inspeccionar", lambda: inspeccionar(_ui.Window, "_prueba_insp"), ventana_ok)

# 9. prims: escena actual, desde la raiz
probar("prims", prims, ventana_ok)

# 10. prims con una ruta que no existe (debe avisar, no romperse)
probar("prims(ruta inexistente)", lambda: prims("/NoExiste/123"), ventana_ok)

# 11. ayuda
probar("ayuda", ayuda, ventana_ok)

ok = sum(r.startswith("OK") for r in resultados)
resumen = f"{ok} de {len(resultados)} pruebas OK\n\n" + "\n".join(resultados)
mostrar(resumen, "Prueba de herramientas", 800, 450)
