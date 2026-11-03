"""Lectura de celda.json y de los URDF, sin Isaac Sim.

En la maquina, los adaptadores usan leer_celda() de herramientas.py (que prefiere tu copia en
scripts/). Este modulo hace lo mismo para la PC y para las pruebas: lee el archivo del repo,
o el que se le pase.
"""
import json
import os
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CELDA_JSON = os.path.join(REPO, "fase1", "celda.json")


def cargar(ruta=CELDA_JSON):
    """Devuelve (D, S): datos del ejercicio y {nombre: valor} de los supuestos.

    Igual que leer_celda() de herramientas.py: el dict completo queda en D["_todo"].
    """
    with open(ruta, encoding="utf-8") as f:
        todo = json.load(f)
    D = dict(todo["datos"], _todo=todo)
    S = {k: v["valor"] for k, v in todo["_supuestos"].items()}
    return D, S


def ruta_urdf(D, clave, carpeta):
    """Ruta al URDF original de Dobot dentro de carpeta/<clave>/; lo baja si no esta.

    Usa la misma estructura que fase2/robots.py, asi en la maquina se reutiliza lo que ya bajo.
    Para la cinematica alcanza el URDF: las mallas no hacen falta.
    """
    M = D["_todo"]["modelos"]
    destino = os.path.join(carpeta, clave, M[clave]["urdf"])
    if not os.path.isfile(destino):
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        datos = urllib.request.urlopen(f"{M['base_url']}/{M[clave]['urdf']}", timeout=60).read()
        with open(destino, "wb") as f:
            f.write(datos)
    return destino


def robot(D, S, clave, carpeta):
    """Todo lo que la cinematica necesita de un robot: cadena, base, largo hasta el TCP y eje.

    La base queda sobre su pedestal (centro y alto de _supuestos).
    """
    from celda import cinematica

    M = D["_todo"]["modelos"][clave]
    p = S[f"pedestal_{clave}"]
    return {
        "clave": clave,
        "cadena": cinematica.leer_cadena(ruta_urdf(D, clave, carpeta), M["link_final"]),
        "T_base": cinematica.base_en(p["centro"][0], p["centro"][1], p["alto"]),
        "largo": M["brida_offset"] + S["herramientas"][clave]["largo"],
        "eje_brida": M["eje_brida"],
    }
