"""Etapa 4 · Ventosas (Surface Gripper) en los dos robots y una prueba de tomar y dejar.

QUE VAS A VER
    La escena de la etapa 3 (o la 2) con dos ventosas nuevas en /World/Etapa4: una en la brida
    del CR6AL (copas para estuches) y otra en la del CR20A (ventosa de area para cajas), al
    largo de herramienta de celda.json. Aparecen una caja llena en el punto de toma de la
    mini-banda y un estuche contra el tope del canal 3.
    Al dar Play, cada robot hace UN ciclo con los angulos de celda/cinematica.py y los tiempos
    de celda/tiempos.py:
      - CR6AL: sube sobre el canal 3, baja, cierra la ventosa, sube, va a la bahia B1, baja
        hasta la posicion 1 de la caja, abre y sube;
      - CR20A: baja al punto de toma, cierra, sube, va a la tarima Norte (camada 1, caja 1),
        baja, abre y sube.
    Al final se abre la ventana "Etapa 4: tomar y dejar" con el estado de cada ventosa en cada
    paso (Open / Closed / Closing) y donde quedaron la caja y el estuche.

Correr:     correr("fase4/ventosas.py")    y despues Play. Esperar unos 20 s simulados.
Lista:      (parcial) la caja termina sobre la tarima Norte y el estuche dentro de la caja de
            B1, sin caerse. La etapa 4 completa pide llenar una caja (36) y una camada (10).
Logica:     angulos y tiempos: celda/cinematica.py y celda/tiempos.py. La secuencia de pasos es
            la misma que usa el modelo de ritmo; aca se ejecuta sobre la fisica.

APIs 6.2 (verificadas en la documentacion 6.2):
    usd.schema.isaac.robot_schema: CreateSurfaceGripper, ApplyAttachmentPointAPI,
        Attributes.MAX_GRIP_DISTANCE / COAXIAL_FORCE_LIMIT / SHEAR_FORCE_LIMIT / RETRY_INTERVAL /
        CLEARANCE_OFFSET / FORWARD_AXIS, Relations.ATTACHMENT_POINTS
    isaacsim.robot.surface_gripper._surface_gripper.acquire_surface_gripper_interface():
        open_gripper(ruta), close_gripper(ruta), get_gripper_status(ruta)
    isaacsim.core.experimental.prims.Articulation(ruta): dof_names, set_dof_position_targets(positions, dof_indices=)
    Punto de enganche: joint D6 (UsdPhysics.Joint) con body0 = brida, los 6 grados bloqueados,
        excludeFromArticulation = True.

Riesgos conocidos: si el importador dejo los links como instancias, el joint del enganche no
puede apuntar adentro (avisa en la ventana). Las ganancias de los joints (robots_drive) pueden
quedar cortas para el CR20A con caja; se ajustan aca.

PROBADO EN LA MAQUINA: no
"""
import math
import os

import numpy as np
import isaacsim.core.experimental.utils.stage as stage_utils
import usd.schema.isaac.robot_schema as robot_schema
from isaacsim.core.experimental.objects import Cube
from isaacsim.core.experimental.prims import Articulation, GeomPrim, RigidPrim
from isaacsim.core.simulation_manager import SimulationEvent, SimulationManager
from isaacsim.robot.surface_gripper import _surface_gripper as surface_gripper
from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics

usar_celda()
from celda import datos, geometria, recetas, tiempos

# ---------------- PARAMETROS ----------------
PARAMS = {
    "escenas_entrada": [TRABAJO + "/escenas/etapa3/celda_banda.usd", TRABAJO + "/escenas/etapa2/celda_robots.usd"],
    "salida": TRABAJO + "/escenas/etapa4/celda_ventosas.usd",
    "carpeta_robots": TRABAJO + "/robots",   # donde fase2/robots.py bajo los URDF
    "raiz": "/World/Etapa4",
    "robots": {"cr20a": "/World/Robots/CR20A", "cr6al": "/World/Robots/CR6AL"},
    "distancia_agarre": 0.01,      # m: a cuanto tiene que estar la pieza para que la ventosa la tome
    "fuerza_axial_n": 300.0,       # N: limite antes de que la pieza se suelte (tirando)
    "fuerza_corte_n": 200.0,       # N: limite de corte (pieza deslizando)
    "canal": 3,                    # canal del estuche de prueba (1..5)
    "bahia": "B1",
    "tarima": "Norte",
    "llegada_inicial_s": 3.0,      # s: desde la postura de reposo hasta el primer punto, sin saltos
}
# --------------------------------------------
TODOS = Usd.TraverseInstanceProxies(Usd.PrimAllPrimsPredicate)


def _buscar(stage, raiz, condicion):
    return next((p for p in Usd.PrimRange(stage.GetPrimAtPath(raiz), TODOS) if condicion(p)), None)


def _ventosa(stage, clave, M, S, avisos):
    """Crea el Surface Gripper con su punto de enganche en la brida del robot. Devuelve la ruta."""
    brida = _buscar(stage, PARAMS["robots"][clave], lambda p: p.GetName() == M[clave]["link_final"])
    if brida is None:
        raise RuntimeError(f"No encontre {M[clave]['link_final']} bajo {PARAMS['robots'][clave]}: corre fase2/robots.py")
    if brida.IsInstanceProxy():
        avisos.append(f"{clave}: la brida es un prim instanciado; el enganche puede no funcionar")
    ruta = f"{PARAMS['raiz']}/Ventosa_{clave.upper()}"
    robot_schema.CreateSurfaceGripper(stage, ruta)
    g = stage.GetPrimAtPath(ruta)
    g.GetAttribute(robot_schema.Attributes.MAX_GRIP_DISTANCE.name).Set(PARAMS["distancia_agarre"])
    g.GetAttribute(robot_schema.Attributes.COAXIAL_FORCE_LIMIT.name).Set(PARAMS["fuerza_axial_n"])
    g.GetAttribute(robot_schema.Attributes.SHEAR_FORCE_LIMIT.name).Set(PARAMS["fuerza_corte_n"])
    g.GetAttribute(robot_schema.Attributes.RETRY_INTERVAL.name).Set(0.5)
    # Punto de enganche: en la cara de la ventosa, sobre el eje de la brida
    largo = M[clave]["brida_offset"] + S["herramientas"][clave]["largo"]
    eje = np.array(M[clave]["eje_brida"], float)
    j = UsdPhysics.Joint.Define(stage, ruta + "/Enganche")
    j.CreateBody0Rel().SetTargets([brida.GetPath()])
    j.CreateLocalPos0Attr().Set(Gf.Vec3f(*(eje * largo)))
    j.CreateExcludeFromArticulationAttr().Set(True)
    for gdl in ("transX", "transY", "transZ", "rotX", "rotY", "rotZ"):
        lim = UsdPhysics.LimitAPI.Apply(j.GetPrim(), gdl)
        lim.CreateLowAttr(1.0)
        lim.CreateHighAttr(-1.0)    # bajo > alto = grado bloqueado
    robot_schema.ApplyAttachmentPointAPI(j.GetPrim())
    j.GetPrim().CreateAttribute(robot_schema.Attributes.FORWARD_AXIS.name, Sdf.ValueTypeNames.Token).Set(
        "XYZ"[int(np.argmax(np.abs(eje)))])
    j.GetPrim().CreateAttribute(robot_schema.Attributes.CLEARANCE_OFFSET.name, Sdf.ValueTypeNames.Float).Set(0.005)
    g.GetRelationship(robot_schema.Relations.ATTACHMENT_POINTS.name).AddTarget(j.GetPath())
    return ruta


def _pieza(ruta, centro, tam, masa, color):
    cubo = Cube(ruta, positions=np.array(centro), scales=np.array(tam), colors=np.array(color))
    RigidPrim(cubo.paths, masses=[masa])
    GeomPrim(cubo.paths, apply_collision_apis=True)
    return ruta


def _plan(T, clave, pasos):
    """Convierte una lista de pasos ('mover', a, b) / ('bajar'|'subir', punto) / ('vacio', on|off) en
    tramos (duracion, q_inicio, q_fin, accion_al_terminar) que el callback ejecuta."""
    out = []
    for p in pasos:
        if p[0] == "mover":
            out.append((T.mover(clave, p[1], p[2]), T.q[clave][p[1]], T.q[clave][p[2]], None))
        elif p[0] in ("bajar", "subir"):
            # el punto bajo se resuelve en el momento con la IK, partiendo del punto alto
            alto = T.q[clave][p[1]]
            bajo = _q_bajo(T, clave, p[1])
            a, b = (alto, bajo) if p[0] == "bajar" else (bajo, alto)
            out.append((T.vertical(T.bajada[clave][p[1]]), a, b, None))
        elif p[0] == "vacio":
            dur = T.S["vacio"]["toma_s" if p[1] == "on" else "soltura_s"]
            out.append((dur, None, None, p[1]))
    # el robot arranca en reposo (todos los joints en 0): primero va despacio al primer punto
    out.insert(0, (PARAMS["llegada_inicial_s"], np.zeros(6), out[0][1], None))
    return out


def _q_bajo(T, clave, punto):
    from celda import cinematica
    R = T.R[clave]
    x, y, z = T.p[clave][punto]
    r = cinematica.resolver_abajo(R["cadena"], R["T_base"], (x, y, z - T.bajada[clave][punto]), R["largo"],
                                  R["eje_brida"], T.q[clave][punto])
    return r["q"]


class Ejecutor:
    """Recorre los tramos de cada robot en el callback de fisica, interpolando los angulos."""

    def __init__(self, robots, planes, ventosas):
        self.robots, self.planes, self.ventosas = robots, planes, ventosas
        self.gi = surface_gripper.acquire_surface_gripper_interface()
        self.estado = {k: {"i": 0, "t": 0.0} for k in planes}
        self.articulaciones, self.indices = {}, {}
        self.log, self.listo = [], False

    def _iniciar(self, clave):
        # la vista de la articulacion se crea con la simulacion corriendo (backend de tensores)
        raiz = self.robots[clave]
        art = Articulation(raiz)
        nombres = list(art.dof_names)
        self.indices[clave] = [nombres.index(f"joint{i + 1}") for i in range(6)]
        self.articulaciones[clave] = art

    def paso(self, dt, contexto=None):
        if self.listo:
            return
        for clave, plan in self.planes.items():
            if clave not in self.articulaciones:
                self._iniciar(clave)
            e = self.estado[clave]
            if e["i"] >= len(plan):
                continue
            dur, qa, qb, accion = plan[e["i"]]
            e["t"] += dt
            f = min(1.0, e["t"] / max(dur, 1e-6))
            if qa is not None:
                s = f * f * (3 - 2 * f)   # arranque y frenado suaves
                q = np.asarray(qa) + (np.asarray(qb) - np.asarray(qa)) * s
                self.articulaciones[clave].set_dof_position_targets(q.reshape(1, -1), dof_indices=self.indices[clave])
            if f >= 1.0:
                if accion == "on":
                    self.gi.close_gripper(self.ventosas[clave])
                elif accion == "off":
                    self.gi.open_gripper(self.ventosas[clave])
                self.log.append(f"{clave}: paso {e['i'] + 1}/{len(plan)} ({dur:.2f} s), ventosa "
                                f"{self.gi.get_gripper_status(self.ventosas[clave])}")
                e["i"], e["t"] = e["i"] + 1, 0.0
        if all(self.estado[k]["i"] >= len(p) for k, p in self.planes.items()):
            self.listo = True
            self._reporte()

    def _reporte(self):
        texto = ["Pasos ejecutados:"] + [f"  {l}" for l in self.log]
        try:
            for nombre, ruta in PIEZAS_ETAPA4.items():
                pos, _ = RigidPrim(ruta).get_world_poses()
                texto.append(f"{nombre} termino en {np.round(np.asarray(pos)[0], 3).tolist()}")
        except Exception as ex:
            texto.append(f"No se pudieron leer las piezas: {ex}")
        texto += ["", "Esperado: la caja sobre la tarima Norte y el estuche dentro de la caja de B1.",
                  "Si la ventosa queda en Open al cerrar: la pieza esta lejos (distancia_agarre) o el",
                  "punto de enganche quedo mal orientado (FORWARD_AXIS / eje_brida)."]
        os.makedirs(TRABAJO + "/notas", exist_ok=True)
        open(TRABAJO + "/notas/etapa4_ventosas.txt", "w", encoding="utf-8").write("\n".join(texto))
        mostrar("\n".join(texto), "Etapa 4: tomar y dejar", 900, 500)


def _etapa4():
    global PIEZAS_ETAPA4, _EJ_ETAPA4, _CB_ETAPA4
    D, S, ruta_datos = leer_celda()
    M = D["_todo"]["modelos"]
    entrada = next((r for r in PARAMS["escenas_entrada"] if os.path.isfile(r)), None)
    if entrada is None:
        return mostrar("Falta la escena de la etapa 2 o 3: corre fase2/robots.py", "Etapa 4", 600, 120)
    stage_utils.open_stage(entrada)
    stage = stage_utils.get_current_stage()
    if stage.GetPrimAtPath(PARAMS["raiz"]):
        stage.RemovePrim(PARAMS["raiz"])
    UsdGeom.Xform.Define(stage, PARAMS["raiz"])
    avisos = []
    ventosas = {c: _ventosa(stage, c, M, S, avisos) for c in PARAMS["robots"]}

    # Piezas de prueba: caja llena en el punto de toma y estuche contra el tope del canal
    c, e, b = S["caja"], S["estuche"], S["banda"]
    tx, ty = geometria.punto_toma(D, S)
    W = geometria.ancho_canales(D, S)
    y_canal = b["y_centro"] - W / 2 + b["ancho_canal"] / 2 + (PARAMS["canal"] - 1) * (b["ancho_canal"] + b["divisor"])
    PIEZAS_ETAPA4 = {
        "Caja": _pieza(PARAMS["raiz"] + "/Caja", (tx, ty, S["minibanda"]["alto"] + c["alto"] / 2 + 0.002),
                       (c["largo"], c["ancho"], c["alto"]), recetas.masa_caja_llena(S), (0.72, 0.55, 0.35)),
        "Estuche": _pieza(PARAMS["raiz"] + "/Estuche", (b["x_fin"] - e["largo"] / 2, y_canal, b["alto"] + e["alto"] / 2 + 0.002),
                          (e["largo"], e["ancho"], e["alto"]), e["masa_kg"], S["variedades"]["A"]["color"]),
    }

    # Planes: los mismos puntos y tiempos que el modelo de ritmo
    robots = {k: datos.robot(D, S, k, PARAMS["carpeta_robots"]) for k in PARAMS["robots"]}
    T = tiempos.Tiempos(D, S, robots)
    canal, bahia = f"canal{PARAMS['canal']}", PARAMS["bahia"]
    destino = T.nombre_estiba(PARAMS["tarima"], 1, 1)
    planes = {
        "cr6al": _plan(T, "cr6al", [("mover", "reposo", canal), ("bajar", canal), ("vacio", "on"), ("subir", canal),
                                    ("mover", canal, f"{bahia}/0"), ("bajar", f"{bahia}/0"), ("vacio", "off"),
                                    ("subir", f"{bahia}/0"), ("mover", f"{bahia}/0", "reposo")]),
        "cr20a": _plan(T, "cr20a", [("mover", destino, "toma"), ("bajar", "toma"), ("vacio", "on"), ("subir", "toma"),
                                    ("mover", "toma", destino), ("bajar", destino), ("vacio", "off"), ("subir", destino)]),
    }
    raices = {}
    for k, ruta in PARAMS["robots"].items():
        p = _buscar(stage, ruta, lambda q: q.HasAPI(UsdPhysics.ArticulationRootAPI))
        raices[k] = p.GetPath().pathString if p else ruta
    os.makedirs(os.path.dirname(PARAMS["salida"]), exist_ok=True)
    stage_utils.save_stage(PARAMS["salida"])

    try:
        SimulationManager.deregister_callback(_CB_ETAPA4)
    except Exception:
        pass
    _EJ_ETAPA4 = Ejecutor(raices, planes, ventosas)
    _CB_ETAPA4 = SimulationManager.register_callback(_EJ_ETAPA4.paso, event=SimulationEvent.PHYSICS_POST_STEP)
    dur = {k: sum(t[0] for t in p) for k, p in planes.items()}
    mostrar("\n".join([f"Datos: {ruta_datos}", f"Escena: {entrada}", f"Ventosas: {ventosas}",
                       f"Raices de articulacion: {raices}",
                       f"Duracion del ciclo: CR6AL {dur['cr6al']:.1f} s, CR20A {dur['cr20a']:.1f} s",
                       f"Puntos sin solucion: {T.sin_solucion or 'ninguno'}"] + avisos +
                      ["", "Dale Play. Al terminar los dos ciclos se abre 'Etapa 4: tomar y dejar'."]),
            "Etapa 4: lista para Play", 900, 300)


_etapa4()
