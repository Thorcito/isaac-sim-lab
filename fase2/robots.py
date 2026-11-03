"""Etapa 2 · Importa el CR20A y el CR6AL desde los URDF oficiales y verifica alcances.

Que hace:   1) baja con urllib los URDF y las mallas de Dobot (repo DOBOT_6Axis_ROS2_V4,
               fijado a un commit en celda.json) a /isaac-sim/trabajo/robots/;
            2) los corrige para Isaac: rutas de mallas relativas, masas e inercias
               de catalogo y esfuerzos que sostengan el brazo (ver _supuestos);
            3) los convierte a USD con el importador de URDF de Isaac Sim 6.2;
            4) abre la escena de la etapa 1 y pone cada robot sobre su pedestal;
            5) con el URDF real y la herramienta vertical, revisa si el CR20A llega
               a la caja mas lejana de la camada mas alta en las 4 tarimas (tambien
               corrida la tolerancia, y a la camada de abajo y al punto de toma), y
               si el CR6AL cubre la banda, el magazine y las 4 bahias;
            6) dibuja los circulos de 1,7 y 1,8 m y cada punto revisado (verde llega,
               rojo no llega) y guarda la escena en escenas/etapa2/celda_robots.usd.
Correr:     correr("fase2/robots.py")     (necesita la escena de la etapa 1 guardada)
Que ver:    tarda alrededor de 1 minuto y la interfaz se congela mientras calcula.
            Al final: los dos robots sobre sus pedestales, los circulos y los puntos,
            y una ventana "Etapa 2: robots y alcances" con PASA/FALLA por control.
            El reporte queda en /isaac-sim/trabajo/notas/etapa2_alcances.txt.
            Despues: Play 3 s y Stop. Los robots deben quedarse quietos en su lugar;
            si saltan, se caen o se van al origen, avisar.
Lista:      la etapa 2 esta lista cuando todo da PASA y el Play no mueve los robots.

PROBADO EN LA MAQUINA: no (en PC: descarga, correccion del URDF, conversion con
urdf-usd-converter 0.3.4 y chequeos de alcance; el importador de Isaac no)
"""
import math
import os
import urllib.request
import xml.etree.ElementTree as ET

import isaacsim.core.experimental.utils.stage as stage_utils
from pxr import Gf, Usd, UsdGeom, UsdPhysics

usar_celda()
from celda.geometria import *    # cajas_camada, punto_toma, camadas_posibles...
from celda.cinematica import *   # leer_cadena, resolver_abajo, margen_radial...

# ---------------- PARAMETROS ----------------
PARAMS = {
    "carpeta_robots": TRABAJO + "/robots",
    "escena_entrada": TRABAJO + "/escenas/etapa1/celda.usd",
    "salida": TRABAJO + "/escenas/etapa2/celda_robots.usd",
    "raiz_robots": "/World/Robots",
    "rebajar": False,          # True = volver a bajar URDF y mallas aunque ya esten
    "reimportar": False,       # True = volver a convertir a USD aunque ya exista
    "tol_alcance": 0.02,       # m: diferencia aceptada entre el alcance del URDF y el dato
    "tol_altura_reposo": 0.15, # m: alto medido del robot importado contra el calculado
    "margen_max": 0.30,        # m: hasta cuanto se busca el margen de alcance (mas = mas lento)
    "variantes": [("PhysX", "physx")],  # variante del robot importado que trae joints y fisica
    "color_cr20a": (1.0, 0.55, 0.0, 1.0),
    "color_cr6al": (0.2, 0.6, 1.0, 1.0),
    "nota": TRABAJO + "/notas/etapa2_alcances.txt",
}
ROBOTS = {"cr20a": "CR20A", "cr6al": "CR6AL"}
# Recorre tambien prims instanciados, inactivos y sin tipo: el importador puede dejar la fisica ahi
TODOS = Usd.TraverseInstanceProxies(Usd.PrimAllPrimsPredicate)
PEDESTAL = {"cr20a": "pedestal_cr20a", "cr6al": "pedestal_cr6al"}
# --------------------------------------------


def _bajar(M, clave, carpeta):
    """Baja el URDF y sus mallas, conservando la estructura meshes/<modelo>/ del repo."""
    m = M[clave]
    os.makedirs(os.path.join(carpeta, m["carpeta_mallas"]), exist_ok=True)
    archivos = [m["urdf"]] + [f"{m['carpeta_mallas']}/{n}.STL" for n in M["mallas"]]
    for rel in archivos:
        destino = os.path.join(carpeta, rel)
        if os.path.isfile(destino) and not PARAMS["rebajar"]:
            continue
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        datos = urllib.request.urlopen(f"{M['base_url']}/{rel}", timeout=60).read()
        open(destino, "wb").write(datos)
    return os.path.join(carpeta, m["urdf"])


def _corregir(M, S, clave, urdf_original, carpeta):
    """Escribe <clave>_isaac.urdf: mallas relativas, masas/inercias y esfuerzos de _supuestos."""
    texto = open(urdf_original, encoding="utf-8").read()
    # package://dobot_rviz/meshes/... -> meshes/...  (relativo a la carpeta del URDF corregido)
    texto = texto.replace(f"package://{M['paquete_ros']}/", "")
    raiz = ET.fromstring(texto)
    total, k = S["robots_masa_kg"][clave], S["robots_radio_giro"]
    for nombre, frac in zip(M["mallas"], S["robots_reparto_masa"]):
        link = raiz.find(f"link[@name='{nombre}']")
        masa = total * frac
        link.find("inertial/mass").set("value", f"{masa:.4f}")
        ine = link.find("inertial/inertia")
        for eje in ("ixx", "iyy", "izz"):
            ine.set(eje, f"{masa * k * k:.6f}")
        for eje in ("ixy", "ixz", "iyz"):
            ine.set(eje, "0")
    for i, esfuerzo in enumerate(S["robots_esfuerzo_nm"][clave]):
        raiz.find(f"joint[@name='joint{i + 1}']/limit").set("effort", str(esfuerzo))
    # Mallas que no corresponden a sus joints: cilindro desde el origen del link hasta el joint siguiente
    for nombre, radio in M[clave].get("mallas_a_cilindro", {}).items():
        hijo = next(j for j in raiz.findall("joint") if j.find("parent").get("link") == nombre)
        x, y, z = [float(v) for v in hijo.find("origin").get("xyz").split()]
        largo = math.sqrt(x * x + y * y + z * z)
        if abs(z) < 0.9 * largo:
            raise ValueError(f"{nombre}: el joint siguiente no esta sobre Z; el cilindro quedaria mal orientado")
        for parte in ("visual", "collision"):
            nodo = raiz.find(f"link[@name='{nombre}']/{parte}")
            nodo.find("origin").attrib.update({"xyz": f"{x / 2} {y / 2} {z / 2}", "rpy": "0 0 0"})
            geo = nodo.find("geometry")
            geo.clear()
            ET.SubElement(geo, "cylinder", {"radius": str(radio), "length": f"{largo:.4f}"})
    salida = os.path.join(carpeta, f"{clave}_isaac.urdf")
    ET.ElementTree(raiz).write(salida, encoding="utf-8", xml_declaration=True)
    return salida


def _importar(S, urdf, carpeta_usd):
    """Convierte el URDF a USD con el importador de Isaac Sim 6.2 y devuelve la ruta del .usd."""
    existentes = [os.path.join(r, f) for r, _, fs in os.walk(carpeta_usd) for f in fs if f.endswith((".usd", ".usda"))] \
        if os.path.isdir(carpeta_usd) else []
    nombre = os.path.splitext(os.path.basename(urdf))[0]
    previo = next((p for p in existentes if os.path.splitext(os.path.basename(p))[0] == nombre), None)
    # se reutiliza el USD solo si es mas nuevo que el URDF corregido (si cambio celda.json, se reimporta)
    if previo and not PARAMS["reimportar"] and os.path.getmtime(previo) > os.path.getmtime(urdf):
        return previo
    from isaacsim.asset.importer.urdf import URDFImporter, URDFImporterConfig
    drive = S["robots_drive"]
    config = URDFImporterConfig(
        urdf_path=urdf,
        usd_path=carpeta_usd,           # carpeta de salida (no un archivo)
        fix_base=True,                  # base fija al mundo: el robot va atornillado al pedestal
        merge_fixed_joints=True,        # une dummy_link con base_link (el URDF trae un link vacio)
        collision_from_visuals=False,   # el URDF ya trae mallas de colision
        joint_drive_type="force",
        joint_target_type="position",   # control de posicion: el brazo se queda donde se le manda
        override_joint_stiffness=drive["rigidez"],
        override_joint_damping=drive["amortiguacion"],
    )
    return URDFImporter(config).import_urdf()


def _anclar_al_mundo(stage, ruta_robot, pos):
    """El joint fijo que agrega el importador ancla el robot al ORIGEN del mundo. Si no se corrige,
    al dar Play el robot salta al origen. Se pone el ancla en la posicion del pedestal."""
    corregidos = 0
    for p in Usd.PrimRange(stage.GetPrimAtPath(ruta_robot), TODOS):
        if p.IsInstanceProxy():
            continue  # un prim instanciado no se puede editar desde la escena
        if p.IsA(UsdPhysics.FixedJoint) and not UsdPhysics.FixedJoint(p).GetBody0Rel().GetTargets():
            j = UsdPhysics.FixedJoint(p)
            j.CreateLocalPos0Attr().Set(Gf.Vec3f(*pos))
            j.CreateLocalRot0Attr().Set(Gf.Quatf(1.0))
            corregidos += 1
    return corregidos


def _diagnostico_fisica(stage, ruta_robot, usd):
    """Si no aparecen joints: donde quedo la fisica del robot importado (variantes, capas, payloads)."""
    out = []
    asset = Usd.Stage.Open(usd)
    dp = asset.GetDefaultPrim()
    out.append(f"  archivo {usd}: default prim {dp.GetPath() if dp else '(ninguno)'}")
    for vs in (dp.GetVariantSets().GetNames() if dp else []):
        v = dp.GetVariantSets().GetVariantSet(vs)
        out.append(f"  variante '{vs}': opciones {v.GetVariantNames()}, elegida '{v.GetVariantSelection()}'")
    out.append("  capas: " + ", ".join(os.path.basename(l.identifier) for l in asset.GetLayerStack()))
    tipos = {}
    for p in Usd.PrimRange(asset.GetPseudoRoot(), TODOS):
        t = p.GetTypeName()
        if "Joint" in t:
            tipos[t] = tipos.get(t, 0) + 1
    out.append(f"  joints dentro del archivo, abierto solo: {tipos or 'ninguno'}")
    modelo = stage.GetPrimAtPath(ruta_robot + "/modelo")
    out.append(f"  en la escena: payload cargado={modelo.IsLoaded()}, instanciado={modelo.IsInstance()}, "
               f"hijos={[c.GetName() for c in modelo.GetChildren()][:10]}")
    return out


def _objetivos_cr20a(D, S, ex, ey):
    """Puntos que tiene que alcanzar el TCP del CR20A: (nombre, (x, y, z), es_tope)."""
    top, aprox, tol = camadas_posibles(D, S), S["aproximacion_z"], D["tarima_tolerancia"]
    lejos = lambda cajas: max(cajas, key=lambda c: math.hypot(c["centro"][0] - ex, c["centro"][1] - ey))
    cerca = lambda cajas: min(cajas, key=lambda c: math.hypot(c["centro"][0] - ex, c["centro"][1] - ey))
    obj = []
    for n in S["tarimas"]:
        c = lejos(cajas_camada(D, S, n, top))
        x, y = c["centro"]
        d = math.hypot(x - ex, y - ey)
        ux, uy = (x - ex) / d, (y - ey) / d
        obj.append((f"{n}: caja mas lejana, camada {top} (la mas alta), con aproximacion", (x, y, c["z_arriba"] + aprox), True))
        obj.append((f"{n}: la misma, con la tarima corrida {tol} m hacia afuera", (x + ux * tol, y + uy * tol, c["z_arriba"]), False))
        b = lejos(cajas_camada(D, S, n, 1))
        obj.append((f"{n}: caja mas lejana, camada 1", (*b["centro"], b["z_arriba"]), False))
        b = cerca(cajas_camada(D, S, n, 1))
        obj.append((f"{n}: caja mas cercana, camada 1", (*b["centro"], b["z_arriba"]), False))
    tx, ty = punto_toma(D, S)
    zt = S["minibanda"]["alto"] + S["caja"]["alto"]
    obj.append(("Punto de toma en la mini-banda", (tx, ty, zt), False))
    obj.append(("Punto de toma, con aproximacion", (tx, ty, zt + aprox), False))
    return obj


def _objetivos_cr6al(D, S, rx, ry):
    """Puntos que tiene que alcanzar el TCP del CR6AL."""
    aprox, e, cj, rec = S["aproximacion_z"], S["estuche"], S["caja"], S["receta_encajado"]
    b, cam, bh, mg = S["banda"], S["camara"], S["bahias"], S["magazine"]
    obj = []
    # Banda: las 4 esquinas del campo de la camara, sobre un estuche
    fx, fy = cam["campo_centro"]
    lx, ly = D["camara"]["campo"][1] / 2 - e["largo"] / 2, D["camara"]["campo"][0] / 2 - e["ancho"] / 2
    zb = b["alto"] + e["alto"]
    for sx in (-1, 1):
        for sy in (-1, 1):
            obj.append((f"Banda: estuche en la esquina ({'O' if sx < 0 else 'E'}{'S' if sy < 0 else 'N'}) del campo",
                        (fx + sx * lx, fy + sy * ly, zb + aprox), True))
    obj.append(("Magazine: caja plana de arriba", (*mg["centro"], mg["alto"]), True))
    obj.append(("Magazine: con aproximacion", (*mg["centro"], mg["alto"] + aprox), False))
    # Bahias: el estuche mas lejano de la capa de abajo, y la entrada por arriba de la caja
    for n, (cx, cy) in bh["centros"].items():
        pos = [(cx + (i - (rec["a_lo_largo"] - 1) / 2) * e["largo"], cy + (j - (rec["a_lo_ancho"] - 1) / 2) * e["ancho"])
               for i in range(rec["a_lo_largo"]) for j in range(rec["a_lo_ancho"])]
        x, y = max(pos, key=lambda p: math.hypot(p[0] - rx, p[1] - ry))
        obj.append((f"{n}: estuche mas lejano, capa de abajo", (x, y, bh["alto"] + e["alto"]), True))
        obj.append((f"{n}: entrada a la caja, con aproximacion", (cx, cy, bh["alto"] + cj["alto"] + aprox), False))
    return obj


def _robots():
    D, S, ruta_datos = leer_celda()
    M = D["_todo"]["modelos"]
    filas, info = [], []

    def control(ok, texto):
        filas.append(("PASA " if ok else "FALLA") + "  " + texto)
        return ok

    if not os.path.isfile(PARAMS["escena_entrada"]):
        return mostrar(f"No existe {PARAMS['escena_entrada']}.\nCorre primero correr(\"fase1/armar_escena.py\").",
                       "Etapa 2: falta la escena", 700, 150)

    # 1-3. Bajar, corregir e importar (antes de abrir la escena: el importador puede tocar el stage)
    modelos = {}
    for clave in ROBOTS:
        carpeta = os.path.join(PARAMS["carpeta_robots"], clave)
        urdf = _bajar(M, clave, carpeta)
        urdf_isaac = _corregir(M, S, clave, urdf, carpeta)
        usd = _importar(S, urdf_isaac, os.path.join(carpeta, "usd"))
        modelos[clave] = {"urdf": urdf, "usd": usd, "cadena": leer_cadena(urdf, M[clave]["link_final"])}
        control(os.path.isfile(usd), f"{ROBOTS[clave]} importado: {usd}")

    # 4. Escena de la etapa 1 + robots sobre sus pedestales
    stage_utils.open_stage(PARAMS["escena_entrada"])
    stage = stage_utils.get_current_stage()
    if stage.GetPrimAtPath(PARAMS["raiz_robots"]):
        stage.RemovePrim(PARAMS["raiz_robots"])
    UsdGeom.Xform.Define(stage, PARAMS["raiz_robots"])
    for clave, nombre in ROBOTS.items():
        p = S[PEDESTAL[clave]]
        pos = (p["centro"][0], p["centro"][1], p["alto"])
        ruta = f"{PARAMS['raiz_robots']}/{nombre}"
        UsdGeom.Xform.Define(stage, ruta).AddTranslateOp().Set(Gf.Vec3d(*pos))
        # el importador 6.2 guarda la fisica en la variante PhysX: sin elegirla no hay joints
        stage_utils.add_reference_to_stage(modelos[clave]["usd"], ruta + "/modelo", variants=PARAMS["variantes"])
        n_fix = _anclar_al_mundo(stage, ruta, pos)
        revol = [q for q in Usd.PrimRange(stage.GetPrimAtPath(ruta), TODOS) if q.IsA(UsdPhysics.RevoluteJoint)]
        if not control(len(revol) == 6, f"{nombre}: {len(revol)} joints de rotacion (esperado 6); anclas al mundo corregidas: {n_fix}"):
            info.append(f"Diagnostico de fisica de {nombre}:")
            info.extend(_diagnostico_fisica(stage, ruta, modelos[clave]["usd"]))
        modelos[clave]["pos"], modelos[clave]["ruta"] = pos, ruta

    # Escala: el alto medido del robot en reposo contra la cinematica directa del URDF
    for clave, m in modelos.items():
        mm = medidas(m["ruta"])[m["ruta"]]
        z_fk = cinematica_directa(m["cadena"], [0.0] * 6, base_en(*m["pos"]))[2, 3]
        alto = mm["max"][2] if mm else float("nan")
        control(mm is not None and abs(alto - z_fk) <= PARAMS["tol_altura_reposo"],
                f"{ROBOTS[clave]} a escala: punta en reposo a {alto:.3f} m medida, {z_fk:.3f} m calculada (unidades en metros)")

    # 5a. El modelo tiene el alcance del dato: radio maximo de la brida con la herramienta hacia abajo
    for clave, m in modelos.items():
        cad, eje = m["cadena"], M[clave]["eje_brida"]
        T0 = base_en(0.0, 0.0, 0.0)
        r0 = resolver_abajo(cad, T0, (1.0, 0.0, 0.0), M[clave]["brida_offset"], eje)
        alcance = 1.0 + margen_radial(cad, T0, (1.0, 0.0, 0.0), M[clave]["brida_offset"], eje, r0["q"], paso=0.005, maximo=1.0)
        dato = D[clave]["alcance"]
        control(abs(alcance - dato) <= PARAMS["tol_alcance"], f"{ROBOTS[clave]}: alcance del URDF {alcance:.3f} m (dato {dato} m)")

    # 5b. Alcance a los puntos de trabajo, con la herramienta vertical
    verdes, rojos = [], []
    for clave, obj in (("cr20a", _objetivos_cr20a(D, S, *modelos["cr20a"]["pos"][:2])),
                       ("cr6al", _objetivos_cr6al(D, S, *modelos["cr6al"]["pos"][:2]))):
        m = modelos[clave]
        T = base_en(*m["pos"])
        largo = M[clave]["brida_offset"] + S["herramientas"][clave]["largo"]
        eje = M[clave]["eje_brida"]
        for texto, punto, con_margen in obj:
            r = resolver_abajo(m["cadena"], T, punto, largo, eje)
            extra = ""
            if r["ok"] and con_margen:
                sobra = margen_radial(m["cadena"], T, punto, largo, eje, r["q"], maximo=PARAMS["margen_max"])
                extra = f", sobran {'mas de ' if sobra >= PARAMS['margen_max'] - 0.01 else ''}{sobra:.2f} m"
            elif not r["ok"]:
                extra = f", le faltan unos {r['err_pos'] * 100:.0f} cm"
            d = math.hypot(punto[0] - m["pos"][0], punto[1] - m["pos"][1])
            control(r["ok"], f"{ROBOTS[clave]} -> {texto}: {d:.2f} m en planta, z {punto[2]:.2f}{extra}")
            (verdes if r["ok"] else rojos).append(punto)

    # 6. Dibujo y guardado
    try:
        limpiar_dibujos()
        for clave, m in modelos.items():
            dibujar_circulo((m["pos"][0], m["pos"][1], 0.01), D[clave]["alcance"], PARAMS[f"color_{clave}"])
        if verdes:
            dibujar_puntos(verdes, (0.0, 1.0, 0.0, 1.0))
        if rojos:
            dibujar_puntos(rojos, (1.0, 0.0, 0.0, 1.0))
        info.append("Dibujo: circulos naranja (CR20A) y azul (CR6AL); puntos verdes llegan, rojos no.")
    except Exception as e:
        info.append(f"No se pudo dibujar: {e}")
    info.append(f"Estiba: tope a {altura_estiba_tope(D, S):.3f} m ('estiba_max_desde' = {S['estiba_max_desde']}), {camadas_posibles(D, S)} camadas")
    info.append("No se revisan choques del brazo con las pilas ni entre robots: eso es la etapa 4.")
    os.makedirs(os.path.dirname(PARAMS["salida"]), exist_ok=True)
    ok = stage_utils.save_stage(PARAMS["salida"])
    info.append(f"Escena guardada: {PARAMS['salida'] if ok else 'NO SE PUDO GUARDAR'}")

    pasa = sum(f.startswith("PASA") for f in filas)
    estado = "ETAPA 2 LISTA (falta probar Play)" if pasa == len(filas) else "ETAPA 2 NO ESTA LISTA"
    texto = "\n".join([f"{estado}: {pasa} de {len(filas)} controles PASA", f"Datos: {ruta_datos}", ""] + filas +
                      ["", "INFORMATIVO"] + [f"  {i}" for i in info])
    os.makedirs(os.path.dirname(PARAMS["nota"]), exist_ok=True)
    open(PARAMS["nota"], "w", encoding="utf-8").write(texto)
    mostrar(texto + f"\n\nGuardado en {PARAMS['nota']}", "Etapa 2: robots y alcances", 1100, 750)


_robots()
