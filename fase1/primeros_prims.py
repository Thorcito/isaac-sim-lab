"""Fase 1 · Primeros prims en codigo.

Hace en Python lo mismo que el Bloque 1 de la guia hace a mano, para ver que
hay "debajo" de cada clic. Usa la API de USD (pxr), que es la base de todo:
las APIs de Isaac Sim se construyen encima de ella.

Correr:  correr("fase1/primeros_prims.py")
Crea:    /World/Practica  (si ya existe, la borra y la vuelve a crear)
Guarda:  /isaac-sim/trabajo/escenas/fase1/practica.usda  (version en texto)

PROBADO EN LA MAQUINA: no
"""
import os
import omni.usd
from pxr import Usd, UsdGeom, Gf

stage = omni.usd.get_context().get_stage()
RAIZ = "/World/Practica"

# 0. Empezar limpio: borrar lo que haya quedado de una corrida anterior.
#    Asi el script se puede correr muchas veces y siempre da lo mismo.
if stage.GetPrimAtPath(RAIZ):
    stage.RemovePrim(RAIZ)

# 1. Un Xform es un GRUPO: no se ve, pero tiene transformada propia
#    y todo lo que cuelga de el la hereda.
grupo = UsdGeom.Xform.Define(stage, RAIZ)
op_grupo = grupo.AddTranslateOp()          # "xformOp:translate"
op_grupo.Set(Gf.Vec3d(0.0, 0.0, 0.0))

# 2. Cubo A: la forma "honesta" de hacer una caja de 0.6 x 0.4 x 0.3 m.
#    UsdGeom.Cube tiene un atributo "size" (el lado) que vale 2.0 por defecto
#    en USD puro; lo dejamos en 1.0 y damos las medidas con la ESCALA.
#    Resultado: escala = medidas reales en metros, facil de leer.
cubo_a = UsdGeom.Cube.Define(stage, RAIZ + "/CajaA")
cubo_a.GetSizeAttr().Set(1.0)
cubo_a.AddTranslateOp().Set(Gf.Vec3d(1.0, 0.0, 0.15))   # centro: z = alto/2 para que apoye en el piso
cubo_a.AddScaleOp().Set(Gf.Vec3f(0.6, 0.4, 0.3))         # largo, ancho, alto
cubo_a.CreateDisplayColorAttr([Gf.Vec3f(0.85, 0.45, 0.15)])  # color simple, sin material

# 3. Cubo B: rotado 45 grados en Z. El ORDEN de las operaciones importa:
#    USD las aplica de derecha a izquierda segun xformOpOrder
#    (primero escala, despues rota, despues traslada).
cubo_b = UsdGeom.Cube.Define(stage, RAIZ + "/CajaB")
cubo_b.GetSizeAttr().Set(1.0)
cubo_b.AddTranslateOp().Set(Gf.Vec3d(-1.0, 0.0, 0.25))
cubo_b.AddRotateXYZOp().Set(Gf.Vec3f(0.0, 0.0, 45.0))    # grados
cubo_b.AddScaleOp().Set(Gf.Vec3f(0.5, 0.5, 0.5))
cubo_b.CreateDisplayColorAttr([Gf.Vec3f(0.2, 0.5, 0.85)])

# 4. Mover el GRUPO 2 m en Y: los dos cubos se mueven con el,
#    aunque sus propias transformadas (locales) no cambian.
op_grupo.Set(Gf.Vec3d(0.0, 2.0, 0.0))

# 5. Leer posiciones: LOCAL (relativa al padre) vs MUNDO (absoluta).
t = Usd.TimeCode.Default()
lineas = ["POSICION LOCAL vs MUNDO (el grupo esta en Y = 2.0)", ""]
for nombre, prim in (("CajaA", cubo_a), ("CajaB", cubo_b)):
    local = prim.GetLocalTransformation(t).ExtractTranslation()
    mundo = prim.ComputeLocalToWorldTransform(t).ExtractTranslation()
    orden = [str(o.GetOpName()) for o in prim.GetOrderedXformOps()]
    lineas.append(f"{nombre}")
    lineas.append(f"  local: ({local[0]:.2f}, {local[1]:.2f}, {local[2]:.2f})")
    lineas.append(f"  mundo: ({mundo[0]:.2f}, {mundo[1]:.2f}, {mundo[2]:.2f})")
    lineas.append(f"  xformOpOrder: {orden}")

# 6. Guardar una COPIA en texto (.usda) para leer como se ve USD por dentro.
#    Export() escribe el archivo sin cambiar la escena que tenes abierta.
carpeta = TRABAJO + "/escenas/fase1"
os.makedirs(carpeta, exist_ok=True)
ruta_usda = carpeta + "/practica.usda"
stage.GetRootLayer().Export(ruta_usda)
lineas += ["", f"Copia en texto: {ruta_usda}", "Se abre en otra ventana: busca 'def Xform \"Practica\"'."]

mostrar("\n".join(lineas), "Primeros prims", 750, 380)
ver(ruta_usda)
