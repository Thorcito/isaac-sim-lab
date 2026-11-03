"""Etapa 3 · Banda de 5 canales con fisica y generador de estuches a ritmo configurable.

QUE VAS A VER
    La escena de la etapa 2 (celda + robots). Sobre la banda aparece una superficie fisica
    que arrastra todo hacia el este a banda.velocidad_m_s (0,10 m/s), los divisores de los
    canales pasan a tener colision y al final de la banda hay un tope transparente.
    Al dar Play empiezan a caer estuches de 4 colores al principio de los canales, a
    PARAMS["ritmo_min"] por minuto, con variedad y canal al azar (semilla fija). Viajan unos
    23 s hasta el tope y se acumulan en fila. A los PARAMS["medir_s"] segundos de simulacion
    se abre la ventana "Etapa 3: banda" con los estuches generados y los que llegaron a la
    zona de la camara, por minuto. La escena queda en escenas/etapa3/celda_banda.usd.

Correr:     correr("fase3/banda_estuches.py")    y despues Play (no hace falta Stop para medir).
            Para cambiar el ritmo: copiar este archivo a scripts/, cambiar PARAMS["ritmo_min"]
            de 15 a 20 y volver a correrlo.
Lista:      la etapa 3 esta lista cuando la banda corre sola y el conteo da el ritmo pedido
            (15 o 20 por minuto, +/- 2 por el azar de las llegadas).
Logica:     el ritmo, la variedad y el canal salen de celda/llegadas.py (lo mismo que usa el
            modelo de ritmo). Este archivo solo traduce eso a la escena.

APIs 6.2 (verificadas en la documentacion 6.2):
    isaacsim.asset.gen.conveyor.create_conveyor_belt(stage, conveyor_prim, prim_name)
    nodo IsaacConveyor: inputs:velocity, inputs:direction
    isaacsim.core.experimental.objects.Cube(path, positions=, scales=, colors=)
    isaacsim.core.experimental.prims.RigidPrim(paths, masses=), GeomPrim(paths, apply_collision_apis=True)
    isaacsim.core.simulation_manager.SimulationManager.register_callback(fn, event=SimulationEvent.PHYSICS_POST_STEP)

PROBADO EN LA MAQUINA: no
"""
import os

import numpy as np
import isaacsim.core.experimental.utils.stage as stage_utils
from isaacsim.core.experimental.objects import Cube
from isaacsim.core.experimental.prims import GeomPrim, RigidPrim
from isaacsim.core.simulation_manager import SimulationEvent, SimulationManager
from pxr import Gf, UsdGeom, UsdPhysics

usar_celda()
from celda import geometria, llegadas, vision

# ---------------- PARAMETROS ----------------
PARAMS = {
    "ritmo_min": 15,                      # estuches por minuto: probar 15 y 20
    "canales": "mezclado",                # "mezclado" o "por_canal"
    "semilla": 1,
    "medir_s": 60.0,                      # segundos de simulacion para contar
    "escena_entrada": TRABAJO + "/escenas/etapa2/celda_robots.usd",
    "salida": TRABAJO + "/escenas/etapa3/celda_banda.usd",
    "raiz": "/World/Etapa3",
    "max_estuches": 120,                  # tope de seguridad: no crear mas cuerpos que esto
}
# --------------------------------------------


def _armar(D, S, stage):
    """Banda fisica, divisores con colision y tope al final. Devuelve la ruta del nodo de la banda."""
    from isaacsim.asset.gen.conveyor import create_conveyor_belt

    b, R = S["banda"], PARAMS["raiz"]
    if stage.GetPrimAtPath(R):
        stage.RemovePrim(R)
    UsdGeom.Xform.Define(stage, R)
    if not any(p.IsA(UsdPhysics.Scene) for p in stage.Traverse()):
        UsdPhysics.Scene.Define(stage, "/World/Fisica")   # sin escena de fisica no hay Play que valga

    # Superficie de la banda: un cubo cinematico; la banda "mueve" lo que toca sin moverse ella
    W = geometria.ancho_canales(D, S)
    largo = b["x_fin"] - b["x_inicio"]
    banda = UsdGeom.Cube.Define(stage, R + "/Banda")
    banda.GetSizeAttr().Set(1.0)
    banda.AddTranslateOp().Set(Gf.Vec3d((b["x_inicio"] + b["x_fin"]) / 2, b["y_centro"], b["alto"] - 0.01))
    banda.AddScaleOp().Set(Gf.Vec3f(largo, W, 0.02))
    banda.CreatePurposeAttr().Set(UsdGeom.Tokens.guide)   # no se ve: los canales de la etapa 1 siguen a la vista
    prim = banda.GetPrim()
    UsdPhysics.CollisionAPI.Apply(prim)
    UsdPhysics.RigidBodyAPI.Apply(prim).CreateKinematicEnabledAttr().Set(True)
    nodo = create_conveyor_belt(stage, prim, prim_name="BandaGrafo")
    nodo.GetAttribute("inputs:velocity").Set(float(b["velocidad_m_s"]))
    nodo.GetAttribute("inputs:direction").Set(Gf.Vec3f(1.0, 0.0, 0.0))

    # Divisores de la etapa 1: que choquen (estaticos)
    divisores = [p.GetPath().pathString for p in stage.Traverse() if p.GetName().startswith("Divisor")]
    if divisores:
        GeomPrim(divisores, apply_collision_apis=True)

    # Tope al final de la banda (pared delgada, invisible, estatica)
    tope = UsdGeom.Cube.Define(stage, R + "/Tope")
    tope.GetSizeAttr().Set(1.0)
    tope.AddTranslateOp().Set(Gf.Vec3d(b["x_fin"] + 0.01, b["y_centro"], b["alto"] + 0.05))
    tope.AddScaleOp().Set(Gf.Vec3f(0.02, W, 0.10))
    tope.CreatePurposeAttr().Set(UsdGeom.Tokens.guide)
    UsdPhysics.CollisionAPI.Apply(tope.GetPrim())
    return nodo.GetPath().pathString, divisores


class Generador:
    """Crea estuches como cuerpos rigidos al ritmo de celda/llegadas.py, desde el callback de fisica."""

    def __init__(self, D, S):
        self.D, self.S = D, S
        mezcla = {k: 1.0 for k in S["variedades"]}
        self.gen = llegadas.Generador(D, S, PARAMS["ritmo_min"], mezcla, PARAMS["canales"], PARAMS["semilla"])
        self.y = vision.canales_y(D, S)
        self.t, self.n = 0.0, 0
        self.proxima = self.gen.intervalo_siguiente()   # el primero no cae en t = 0: no infla el conteo
        self.creados, self.rutas = [], []
        self.reportado = False

    def paso(self, dt, contexto=None):
        self.t += dt
        if self.t >= self.proxima and self.n < PARAMS["max_estuches"]:
            dt_sig, variedad, canal = self.gen.siguiente()
            self._crear(variedad, canal)
            self.proxima = self.t + dt_sig
        if self.t >= PARAMS["medir_s"] and not self.reportado:
            self.reportado = True
            self._reporte()

    def _crear(self, variedad, canal):
        e, b = self.S["estuche"], self.S["banda"]
        self.n += 1
        ruta = f"{PARAMS['raiz']}/Estuches/E{self.n:04d}"
        pos = np.array([b["x_inicio"] + e["largo"], self.y[canal], b["alto"] + e["alto"] / 2 + 0.003])
        cubo = Cube(ruta, positions=pos, scales=np.array([e["largo"], e["ancho"], e["alto"]]),
                    colors=np.array(self.S["variedades"][variedad]["color"]))
        RigidPrim(cubo.paths, masses=[e["masa_kg"]])
        GeomPrim(cubo.paths, apply_collision_apis=True)
        self.creados.append((self.t, variedad, canal))
        self.rutas.append(ruta)

    def _reporte(self):
        """Cuenta los estuches generados y cuantos estan ya dentro del campo de la camara."""
        x0 = self.S["camara"]["campo_centro"][0] - self.D["camara"]["campo"][1] / 2
        en_campo = None
        try:
            pos, _ = RigidPrim(self.rutas).get_world_poses()
            en_campo = int((np.asarray(pos)[:, 0] >= x0).sum())
        except Exception as ex:   # la lectura de poses es lo que mas puede cambiar entre versiones
            en_campo = f"no se pudo leer ({ex})"
        minutos = self.t / 60.0
        por_var = {v: sum(1 for _, x, _ in self.creados if x == v) for v in self.S["variedades"]}
        texto = "\n".join([
            f"Ritmo pedido: {PARAMS['ritmo_min']} por minuto ({PARAMS['canales']}, semilla {PARAMS['semilla']})",
            f"Tiempo simulado: {self.t:.1f} s",
            f"Estuches generados: {self.n} -> {self.n / minutos:.1f} por minuto",
            f"Por variedad: {por_var}",
            f"Dentro del campo de la camara o mas adelante: {en_campo}",
            "",
            "Esperado: unos 23 s de viaje hasta el tope (2,3 m a 0,10 m/s); despues se acumulan en fila.",
            "Si los estuches no avanzan: la banda no arrastra (revisar el nodo BandaGrafo, inputs:velocity).",
            "Si atraviesan la banda: falta la colision de la superficie o la escena de fisica.",
        ])
        os.makedirs(TRABAJO + "/notas", exist_ok=True)
        open(TRABAJO + "/notas/etapa3_banda.txt", "w", encoding="utf-8").write(texto)
        mostrar(texto, "Etapa 3: banda", 800, 300)


def _etapa3():
    D, S, ruta_datos = leer_celda()
    entrada = PARAMS["escena_entrada"]
    if not os.path.isfile(entrada):
        entrada = TRABAJO + "/escenas/etapa1/celda.usd"   # sin robots tambien sirve para la banda
    stage_utils.open_stage(entrada)
    stage = stage_utils.get_current_stage()
    nodo, divisores = _armar(D, S, stage)
    os.makedirs(os.path.dirname(PARAMS["salida"]), exist_ok=True)
    stage_utils.save_stage(PARAMS["salida"])

    global _GEN_ETAPA3, _CB_ETAPA3
    try:   # si se corre dos veces, sacar el callback anterior
        SimulationManager.deregister_callback(_CB_ETAPA3)
    except Exception:
        pass
    _GEN_ETAPA3 = Generador(D, S)
    _CB_ETAPA3 = SimulationManager.register_callback(_GEN_ETAPA3.paso, event=SimulationEvent.PHYSICS_POST_STEP)
    mostrar("\n".join([f"Datos: {ruta_datos}", f"Escena de partida: {entrada}", f"Banda: {nodo}",
                       f"Divisores con colision: {len(divisores)}", f"Guardada: {PARAMS['salida']}", "",
                       f"Dale Play: a los {PARAMS['medir_s']:.0f} s de simulacion aparece el conteo.",
                       "Para sacar el generador sin reiniciar: SimulationManager.deregister_callback(_CB_ETAPA3)"]),
            "Etapa 3: lista para Play", 800, 260)


_etapa3()
