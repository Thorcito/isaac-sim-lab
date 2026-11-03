"""Etapa 1 · Arma la escena a escala de la celda desde celda.json y la guarda.

Que hace:   abre una escena NUEVA en metros con Z arriba, crea /World/Celda con
            cajas simples (piso, pasos de personal, zona de estiba, 4 tarimas en
            molinete, pedestal del CR20A, banda de 5 canales, mini-banda con tope y
            punto de toma, bahias B1 a B4, pedestal del CR6AL, magazine, portico
            con camara y su campo, tablero, tablet y baliza) y la guarda en
            /isaac-sim/trabajo/escenas/etapa1/celda.usd. Todavia sin fisica: eso
            llega en la etapa 3.
Correr:     correr("fase1/armar_escena.py")
Que ver:    la celda en el viewport y una ventana "Etapa 1: escena armada" con la
            cantidad de piezas, el archivo de datos usado y donde se guardo.
            Despues correr la verificacion: correr("fase1/verificar_escena.py")
Cuidado:    abre una escena nueva; guarda antes lo que tengas abierto.

PROBADO EN LA MAQUINA: no (probado en PC con usd-core: construye y guarda sin errores)
"""
import os

import isaacsim.core.experimental.utils.stage as stage_utils
from pxr import Gf, Sdf, UsdGeom, UsdLux

usar_celda()
from celda.geometria import *   # piezas() y las funciones de geometria (logica sin Isaac)

# ---------------- PARAMETROS ----------------
PARAMS = {
    "salida": TRABAJO + "/escenas/etapa1/celda.usd",
    "raiz": "/World/Celda",
    "luz_domo": 1000.0,      # intensidad de la luz ambiente
    "luz_sol": 2500.0,       # intensidad de la luz direccional
}
# --------------------------------------------


def _armar():
    D, S, ruta_datos = leer_celda()

    # 1. Escena nueva en metros y con Z arriba: asi 1 unidad = 1 m y las medidas son las reales
    stage_utils.create_new_stage()
    stage_utils.set_stage_units(meters_per_unit=1.0)
    stage_utils.set_stage_up_axis("Z")
    stage = stage_utils.get_current_stage()
    mundo = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(mundo.GetPrim())

    # 2. Luces: la escena nueva puede venir sin luz y se veria negra
    UsdLux.DomeLight.Define(stage, "/World/Luces/Domo").CreateIntensityAttr(PARAMS["luz_domo"])
    sol = UsdLux.DistantLight.Define(stage, "/World/Luces/Sol")
    sol.CreateIntensityAttr(PARAMS["luz_sol"])
    sol.AddRotateXYZOp().Set(Gf.Vec3f(40.0, 0.0, 30.0))

    # 3. Piezas: cubo de lado 1 escalado a las medidas reales (la escala "dice" las medidas)
    lista = piezas(D, S)
    for p in lista:
        ruta = PARAMS["raiz"] + p["ruta"]
        # crear los grupos intermedios como Xform (sin transformada, no mueven nada)
        padre = Sdf.Path(ruta).GetParentPath()
        while str(padre) != "/World" and not stage.GetPrimAtPath(padre):
            UsdGeom.Xform.Define(stage, padre)
            padre = padre.GetParentPath()
        cubo = UsdGeom.Cube.Define(stage, ruta)
        cubo.GetSizeAttr().Set(1.0)
        cubo.AddTranslateOp().Set(Gf.Vec3d(*p["centro"]))
        cubo.AddScaleOp().Set(Gf.Vec3f(*p["tam"]))
        cubo.CreateDisplayColorAttr([Gf.Vec3f(*p["color"])])

    # 4. Guardar
    os.makedirs(os.path.dirname(PARAMS["salida"]), exist_ok=True)
    ok = stage_utils.save_stage(PARAMS["salida"])
    texto = [
        f"Datos: {ruta_datos}",
        f"Piezas creadas: {len(lista)} bajo {PARAMS['raiz']}",
        f"Guardada: {PARAMS['salida'] if ok else 'NO SE PUDO GUARDAR'}",
        "",
        "Siguiente paso:  correr(\"fase1/verificar_escena.py\")",
    ]
    mostrar("\n".join(texto), "Etapa 1: escena armada", 800, 220)


_armar()
