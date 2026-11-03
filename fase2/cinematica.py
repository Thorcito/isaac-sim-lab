"""Fase 2 · Cinematica desde un URDF (solo Python y numpy, sin Isaac Sim).

Que hace:   lee la cadena de joints de un URDF y resuelve cinematica directa e
            inversa con la herramienta apuntando hacia abajo. Sirve para contestar
            "el robot llega a este punto?" con la geometria real del fabricante, no
            con un circulo. El circulo de alcance solo es una primera aproximacion:
            con la herramienta vertical, la muneca tiene que quedar ARRIBA de la caja,
            asi que el alcance util cambia con la altura.
Como usar:  no se corre solo; lo carga fase2/robots.py con correr("fase2/cinematica.py").
Que esperar: define las funciones leer_cadena, cinematica_directa, resolver_abajo y
            margen_radial. No abre ventanas.

Metodo: minimos cuadrados amortiguados (Damped Least Squares) con varios arranques.
La rotacion alrededor del eje de la herramienta queda libre, porque el joint 6 puede
girar la ventosa para alinearla con la caja. No revisa choques: eso se ve en la etapa 4.

PROBADO EN LA MAQUINA: no (probado en PC contra los URDF reales, con Python 3.12 y numpy)
"""
import math
import xml.etree.ElementTree as ET

import numpy as np

# Parametros del metodo numerico. No son medidas de la celda: por eso no viven en celda.json.
IK_PARAMS = {
    "iteraciones": 200,
    "amortiguacion": 0.02,     # alto = mas estable cerca de singularidades, pero mas lento
    "paso_maximo_rad": 0.25,   # recorte por iteracion para no saltar a otra configuracion
    "tol_posicion_m": 0.001,   # 1 mm
    "tol_angulo_rad": 0.005,   # unos 0,3 grados
    "peso_angulo": 0.3,        # cuanto pesa el error de orientacion frente al de posicion
    "abandono_iter": 40,       # si tras estas iteraciones el error sigue grande, probar otro arranque
    "abandono_m": 0.05,
}


def _matriz(xyz, rpy):
    """Transformada homogenea desde el origin de un joint URDF (rotacion fija XYZ)."""
    r, p, y = rpy
    cr, sr, cp, sp, cy, sy = math.cos(r), math.sin(r), math.cos(p), math.sin(p), math.cos(y), math.sin(y)
    T = np.eye(4)
    T[:3, :3] = [
        [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
        [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
        [-sp, cp * sr, cp * cr],
    ]
    T[:3, 3] = xyz
    return T


def _rot_eje(eje, angulo):
    """Rotacion homogenea alrededor de un eje unitario (formula de Rodrigues)."""
    x, y, z = eje
    K = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    T = np.eye(4)
    T[:3, :3] = np.eye(3) + math.sin(angulo) * K + (1 - math.cos(angulo)) * K @ K
    return T


def leer_cadena(ruta_urdf, link_final):
    """Devuelve la cadena desde la raiz hasta link_final como lista de joints, en orden."""
    raiz = ET.parse(ruta_urdf).getroot()
    por_hijo = {j.find("child").get("link"): j for j in raiz.findall("joint")}
    if link_final not in por_hijo:
        raise ValueError(f"{ruta_urdf}: no hay ningun joint que termine en el link {link_final}")
    joints, actual = [], link_final
    while actual in por_hijo:
        j = por_hijo[actual]
        org, eje, lim = j.find("origin"), j.find("axis"), j.find("limit")
        leer = lambda nodo, attr: [float(v) for v in nodo.get(attr).split()] if nodo is not None and nodo.get(attr) else [0.0, 0.0, 0.0]
        movil = j.get("type") in ("revolute", "continuous", "prismatic")
        joints.insert(0, {
            "nombre": j.get("name"),
            "movil": movil,
            "T": _matriz(leer(org, "xyz"), leer(org, "rpy")),
            "eje": np.array(leer(eje, "xyz")) if movil else None,
            "lim": (float(lim.get("lower")), float(lim.get("upper"))) if movil and lim is not None else (-math.pi * 2, math.pi * 2),
        })
        actual = j.find("parent").get("link")
    return joints


def _recorrer(cadena, q, T_base):
    """Cinematica directa: devuelve la pose final y el origen y eje de cada joint movil."""
    T, i, puntos, ejes = T_base.copy(), 0, [], []
    for j in cadena:
        T = T @ j["T"]
        if j["movil"]:
            puntos.append(T[:3, 3].copy())
            ejes.append(T[:3, :3] @ j["eje"])
            T = T @ _rot_eje(j["eje"], q[i])
            i += 1
    return T, puntos, ejes


def cinematica_directa(cadena, q, T_base=None):
    """Pose (matriz 4x4) del ultimo link para los angulos q."""
    return _recorrer(cadena, q, np.eye(4) if T_base is None else T_base)[0]


def base_en(x, y, z):
    """Transformada de la base del robot, sin rotacion, en una posicion del mundo."""
    T = np.eye(4)
    T[:3, 3] = (x, y, z)
    return T


def _iterar(cadena, q0, T_base, objetivo, largo, eje_brida):
    """DLS desde un arranque. Devuelve (q, error de posicion, error angular)."""
    p = IK_PARAMS
    abajo = np.array([0.0, 0.0, -1.0])
    q, lims = q0.copy(), [j["lim"] for j in cadena if j["movil"]]
    for it in range(p["iteraciones"]):
        T, puntos, ejes = _recorrer(cadena, q, T_base)
        eje_tcp = T[:3, :3] @ eje_brida
        tcp = T[:3, 3] + eje_tcp * largo
        e_pos, e_ang = objetivo - tcp, np.cross(eje_tcp, abajo)
        if np.linalg.norm(e_pos) < p["tol_posicion_m"] and np.linalg.norm(e_ang) < p["tol_angulo_rad"]:
            break
        if it == p["abandono_iter"] and np.linalg.norm(e_pos) > p["abandono_m"]:
            break  # este arranque no converge: no vale la pena seguir iterando
        J = np.zeros((6, len(q)))
        for k, (pt, eje) in enumerate(zip(puntos, ejes)):
            J[:3, k] = np.cross(eje, tcp - pt)
            J[3:, k] = eje * p["peso_angulo"]
        e = np.concatenate([e_pos, e_ang * p["peso_angulo"]])
        dq = J.T @ np.linalg.solve(J @ J.T + np.eye(6) * p["amortiguacion"] ** 2, e)
        dq = np.clip(dq, -p["paso_maximo_rad"], p["paso_maximo_rad"])
        q = np.array([min(max(v, a), b) for v, (a, b) in zip(q + dq, lims)])
    T = _recorrer(cadena, q, T_base)[0]
    eje_tcp = T[:3, :3] @ eje_brida
    tcp = T[:3, 3] + eje_tcp * largo
    return q, float(np.linalg.norm(objetivo - tcp)), float(np.linalg.norm(np.cross(eje_tcp, abajo)))


def resolver_abajo(cadena, T_base, objetivo, largo, eje_brida, q_inicial=None):
    """Busca angulos que dejen el TCP en objetivo con la herramienta vertical hacia abajo.

    largo: distancia desde el origen del ultimo link hasta el TCP, sobre eje_brida.
    Devuelve dict con ok, q, err_pos y err_ang.
    """
    p = IK_PARAMS
    objetivo, eje_brida = np.asarray(objetivo, float), np.asarray(eje_brida, float)
    n = sum(j["movil"] for j in cadena)
    rumbo = math.atan2(objetivo[1] - T_base[1, 3], objetivo[0] - T_base[0, 3])
    arranques = [] if q_inicial is None else [np.asarray(q_inicial, float)]
    # Barrido grueso de arranques: los dos frentes del hombro con varias posturas de codo y muneca
    for j1 in (rumbo, rumbo + math.pi):
        for j2 in (-0.8, 0.8):
            for j3 in (-1.2, 1.2):
                for j5 in (-1.57, 1.57):
                    q = np.zeros(n)
                    q[0], q[1], q[2], q[4] = j1, j2, j3, j5
                    arranques.append(q)
    mejor = None
    for q0 in arranques:
        q, e_p, e_a = _iterar(cadena, q0, T_base, objetivo, largo, eje_brida)
        if mejor is None or e_p + e_a < mejor["err_pos"] + mejor["err_ang"]:
            mejor = {"q": q, "err_pos": e_p, "err_ang": e_a}
        if e_p < p["tol_posicion_m"] and e_a < p["tol_angulo_rad"]:
            break
    mejor["ok"] = mejor["err_pos"] < p["tol_posicion_m"] and mejor["err_ang"] < p["tol_angulo_rad"]
    return mejor


def margen_radial(cadena, T_base, objetivo, largo, eje_brida, q_inicial, paso=0.01, maximo=0.60):
    """Cuanto mas lejos, en planta y alejandose de la base, sigue llegando el robot (m)."""
    objetivo = np.asarray(objetivo, float)
    d = objetivo[:2] - T_base[:2, 3]
    d = d / np.linalg.norm(d)
    margen, q = 0.0, q_inicial
    while margen + paso <= maximo:
        prueba = objetivo.copy()
        prueba[:2] += d * (margen + paso)
        r = resolver_abajo(cadena, T_base, prueba, largo, eje_brida, q)
        if not r["ok"]:
            break
        margen, q = margen + paso, r["q"]
    return margen
