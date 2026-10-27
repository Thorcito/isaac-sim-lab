"""Fase 1 · Layout parametrico de la celda (una estacion).

Lee TODAS las medidas de un celda.json. Busca primero tu copia en
/isaac-sim/trabajo/scripts/celda.json (para experimentar sin que
actualizar() la pise) y si no existe usa la del repo: fase1/celda.json.
Crea /World/Celda con geometria simple (cajas y cilindros, sin fisica
todavia) y abre una ventana de VERIFICACION que mide la escena ya
construida y la compara con los datos.

Correr:   correr("fase1/layout.py")
Cambiar:  copiar celda.json a scripts/, editar la copia y volver a correr
          (borra y recrea /World/Celda)

Convencion: origen en la esquina suroeste del piso, X hacia el este,
Y hacia el norte, Z hacia arriba, metros. La zona de alimentacion queda
al oeste y la de estiba al este.

PROBADO EN LA MAQUINA: no
"""
import json, math, os
import omni.usd
from pxr import Usd, UsdGeom, Gf

RUTAS_DATOS = [MIS_SCRIPTS + "/celda.json", REPO_DIR + "/fase1/celda.json"]
RAIZ = "/World/Celda"
TOL = 0.001  # 1 mm de tolerancia para comparar medidas

COLOR = {
    "piso": (0.55, 0.55, 0.55), "zona": (0.95, 0.80, 0.10), "tarima": (0.72, 0.53, 0.30),
    "pedestal": (0.25, 0.25, 0.30), "robot": (0.90, 0.45, 0.10), "banda": (0.20, 0.20, 0.22),
    "canal_a": (0.35, 0.35, 0.40), "canal_b": (0.45, 0.45, 0.50), "divisor": (0.80, 0.80, 0.80),
    "minibanda": (0.20, 0.35, 0.60), "bahia": (0.30, 0.60, 0.35), "magazine": (0.60, 0.40, 0.70),
    "camara": (0.10, 0.10, 0.10), "campo": (0.20, 0.80, 0.90), "toma": (0.90, 0.15, 0.15),
}


def _main():
    ruta_datos = next((r for r in RUTAS_DATOS if os.path.isfile(r)), None)
    if not ruta_datos:
        return mostrar("No encontre celda.json en:\n" + "\n".join(RUTAS_DATOS) +
                       "\n\nCorre actualizar() para bajar el repo.", "Layout: faltan datos", 700, 200)
    d = json.load(open(ruta_datos, encoding="utf-8"))
    stage = omni.usd.get_context().get_stage()

    avisos = []
    if abs(UsdGeom.GetStageMetersPerUnit(stage) - 1.0) > 1e-9:
        avisos.append("AVISO: la escena no esta en metros (metersPerUnit != 1). Usa File > New.")
    if UsdGeom.GetStageUpAxis(stage) != UsdGeom.Tokens.z:
        avisos.append("AVISO: el eje arriba de la escena no es Z.")

    if stage.GetPrimAtPath(RAIZ):
        stage.RemovePrim(RAIZ)
    UsdGeom.Xform.Define(stage, RAIZ)

    # ---------- helpers de geometria ----------
    def grupo(ruta):
        return UsdGeom.Xform.Define(stage, RAIZ + ruta)

    def caja(ruta, centro, tam, color):
        """Caja con size=1 y escala = medidas reales (largo X, ancho Y, alto Z)."""
        c = UsdGeom.Cube.Define(stage, RAIZ + ruta)
        c.GetSizeAttr().Set(1.0)
        c.AddTranslateOp().Set(Gf.Vec3d(*centro))
        c.AddScaleOp().Set(Gf.Vec3f(*tam))
        c.CreateDisplayColorAttr([Gf.Vec3f(*COLOR[color])])
        return c

    def cilindro(ruta, centro, radio, alto, color):
        c = UsdGeom.Cylinder.Define(stage, RAIZ + ruta)
        c.GetRadiusAttr().Set(radio)
        c.GetHeightAttr().Set(alto)
        c.GetAxisAttr().Set(UsdGeom.Tokens.z)
        c.AddTranslateOp().Set(Gf.Vec3d(*centro))
        c.CreateDisplayColorAttr([Gf.Vec3f(*COLOR[color])])
        return c

    # ---------- datos ----------
    Lx, Wy = d["piso"]["largo_x"], d["piso"]["ancho_y"]
    ze = d["zona_estiba"]
    lado = ze["lado"]
    t = d["tarima"]
    a, b = min(t["largo"], t["ancho"]), max(t["largo"], t["ancho"])   # a = lado corto, b = lado largo
    g = d["tarimas_molinete"]["separacion"]
    ped = d["pedestal"]
    rb = d["robots"]
    mb = d["minibanda"]
    bh = d["bahias"]
    bd = d["banda"]
    mg = d["magazine"]
    cam = d["camara"]

    # Centro de la zona de estiba (= centro del CR20A), pegado al borde este
    cex, cey = Lx - ze["margen_borde"] - lado / 2, Wy / 2

    # ---------- piso y zona de estiba ----------
    caja("/Piso", (Lx / 2, Wy / 2, -0.01), (Lx, Wy, 0.02), "piso")
    grupo("/ZonaEstiba")
    e = 0.04  # ancho de la linea pintada
    caja("/ZonaEstiba/LineaN", (cex, cey + lado / 2 - e / 2, 0.002), (lado, e, 0.004), "zona")
    caja("/ZonaEstiba/LineaS", (cex, cey - lado / 2 + e / 2, 0.002), (lado, e, 0.004), "zona")
    caja("/ZonaEstiba/LineaE", (cex + lado / 2 - e / 2, cey, 0.002), (e, lado, 0.004), "zona")
    caja("/ZonaEstiba/LineaO", (cex - lado / 2 + e / 2, cey, 0.002), (e, lado, 0.004), "zona")

    # ---------- tarimas en molinete alrededor del pedestal ----------
    # Cuatro rectangulos a x b girados 90 grados entre si. Lado exterior S = a + b + g,
    # hueco central = b - a + g (ahi va el pedestal). Ver la pregunta 4 de la bitacora.
    S = a + b + g
    tarimas = {  # nombre: (centro relativo, tamano en X, tamano en Y)
        "Norte": ((-S / 2 + b / 2,  S / 2 - a / 2), b, a),
        "Oeste": ((-S / 2 + a / 2, -S / 2 + b / 2), a, b),
        "Sur":   (( S / 2 - b / 2, -S / 2 + a / 2), b, a),
        "Este":  (( S / 2 - a / 2,  S / 2 - b / 2), a, b),
    }
    grupo("/ZonaEstiba/Tarimas")
    for n, ((dx, dy), sx, sy) in tarimas.items():
        caja(f"/ZonaEstiba/Tarimas/{n}", (cex + dx, cey + dy, t["alto"] / 2), (sx, sy, t["alto"]), "tarima")

    caja("/ZonaEstiba/Pedestal", (cex, cey, ped["alto"] / 2), (ped["lado"], ped["lado"], ped["alto"]), "pedestal")
    cilindro("/ZonaEstiba/CR20A_base", (cex, cey, ped["alto"] + rb["base_alto"] / 2),
             rb["base_radio"], rb["base_alto"], "robot")

    # ---------- punto de toma, mini-banda y bahias ----------
    tomax = cex - lado / 2 - d["punto_toma"]["dist_fuera_zona"]
    grupo("/Alimentacion")
    caja("/Alimentacion/PuntoToma", (tomax - 0.05, cey, mb["alto"] + 0.005), (0.1, mb["ancho"], 0.01), "toma")
    mb_x0 = tomax - mb["largo"]
    caja("/Alimentacion/MiniBanda", ((mb_x0 + tomax) / 2, cey, mb["alto"] / 2), (mb["largo"], mb["ancho"], mb["alto"]), "minibanda")

    bah_x = mb_x0 - bh["dist_minibanda"] - bh["largo"] / 2
    paso = bh["ancho"] + bh["separacion"]
    grupo("/Alimentacion/Bahias")
    for i in range(bh["cantidad"]):
        y = cey + (i - (bh["cantidad"] - 1) / 2) * paso
        caja(f"/Alimentacion/Bahias/B{i + 1}", (bah_x, y, bh["alto"] / 2), (bh["largo"], bh["ancho"], bh["alto"]), "bahia")

    # ---------- CR6AL, banda de 5 canales, magazine ----------
    r6x = bah_x - rb["cr6al_dist_bahias"]
    cilindro("/Alimentacion/CR6AL_base", (r6x, cey, rb["base_alto"] / 2), rb["base_radio"], rb["base_alto"], "robot")

    n = bd["canales"]
    W = n * bd["ancho_canal"] + (n - 1) * bd["divisor"]
    bx = r6x - bd["dist_cr6al"]
    grupo("/Alimentacion/Banda")
    caja("/Alimentacion/Banda/Estructura", (bx, cey, bd["alto"] / 2 - 0.01), (W, bd["largo"], bd["alto"] - 0.02), "banda")
    for i in range(n):
        x = bx - W / 2 + bd["ancho_canal"] / 2 + i * (bd["ancho_canal"] + bd["divisor"])
        caja(f"/Alimentacion/Banda/Canal{i + 1}", (x, cey, bd["alto"] - 0.005), (bd["ancho_canal"], bd["largo"], 0.01),
             "canal_a" if i % 2 == 0 else "canal_b")
        if i < n - 1:
            xd = x + bd["ancho_canal"] / 2 + bd["divisor"] / 2
            caja(f"/Alimentacion/Banda/Divisor{i + 1}", (xd, cey, bd["alto"] + 0.02), (bd["divisor"], bd["largo"], 0.04), "divisor")

    caja("/Alimentacion/Magazine", (r6x, cey + mg["dist_y_cr6al"], mg["alto"] / 2), (mg["largo"], mg["ancho"], mg["alto"]), "magazine")

    # ---------- camara (solo marcador; el sensor real va en la fase 6) ----------
    camy = cey + cam["offset_y"]
    camz = bd["alto"] + cam["altura_sobre_banda"]
    grupo("/Camara")
    caja("/Camara/Cuerpo", (bx, camy, camz + 0.04), (0.06, 0.12, 0.08), "camara")
    caja("/Camara/Campo", (bx, camy, bd["alto"] + 0.012), (cam["campo_x"], cam["campo_y"], 0.002), "campo")

    # ======================= VERIFICACION =======================
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])

    def rango(ruta):
        r = cache.ComputeWorldBound(stage.GetPrimAtPath(RAIZ + ruta)).ComputeAlignedRange()
        return r.GetMin(), r.GetMax()

    def tam(ruta):
        mn, mx = rango(ruta)
        return mx - mn

    def solapan(r1, r2):  # rectangulos en planta
        (a0, a1), (b0, b1) = r1, r2
        return a0[0] < b1[0] - TOL and b0[0] < a1[0] - TOL and a0[1] < b1[1] - TOL and b0[1] < a1[1] - TOL

    chk = []
    def check(ok, texto):
        chk.append(("OK     " if ok else "REVISAR") + "  " + texto)

    s = tam("/Piso")
    check(abs(s[0] - Lx) < TOL and abs(s[1] - Wy) < TOL, f"Piso medido {s[0]:.3f} x {s[1]:.3f} m (dato {Lx} x {Wy})")

    rt = {k: rango(f"/ZonaEstiba/Tarimas/{k}") for k in tarimas}
    for k, (mn, mx) in rt.items():
        sx, sy = mx[0] - mn[0], mx[1] - mn[1]
        check(sorted([round(sx, 3), round(sy, 3)]) == sorted([round(a, 3), round(b, 3)]),
              f"Tarima {k}: {sx:.3f} x {sy:.3f} m")
    zmin = (cex - lado / 2, cey - lado / 2)
    zmax = (cex + lado / 2, cey + lado / 2)
    dentro = all(mn[0] >= zmin[0] - TOL and mn[1] >= zmin[1] - TOL and mx[0] <= zmax[0] + TOL and mx[1] <= zmax[1] + TOL
                 for mn, mx in rt.values())
    check(dentro, f"Las 4 tarimas caben en la zona de estiba de {lado} x {lado} m (conjunto: {S:.3f} x {S:.3f} m, "
                  f"margen {(lado - S) / 2:.3f} m por lado)")
    nombres = list(rt)
    choques = [f"{nombres[i]}-{nombres[j]}" for i in range(4) for j in range(i + 1, 4) if solapan(rt[nombres[i]], rt[nombres[j]])]
    check(not choques, "Las tarimas no se solapan" + (f" (solapan: {', '.join(choques)})" if choques else ""))
    rp = rango("/ZonaEstiba/Pedestal")
    holgura = (b - a + g - ped["lado"]) / 2
    check(not any(solapan(rp, r) for r in rt.values()) and holgura >= t["tolerancia"],
          f"Pedestal libre: holgura {holgura:.3f} m por lado contra las tarimas (tolerancia de posicion {t['tolerancia']} m)")

    mn, mx = rango("/Alimentacion")
    check(mn[0] >= -TOL and mn[1] >= -TOL and mx[0] <= Lx + TOL and mx[1] <= Wy + TOL,
          f"Zona de alimentacion dentro del piso (X {mn[0]:.2f} a {mx[0]:.2f}, Y {mn[1]:.2f} a {mx[1]:.2f})")
    s = tam("/Alimentacion/MiniBanda")
    check(abs(s[0] - mb["largo"]) < TOL, f"Mini-banda de {s[0]:.3f} m (dato {mb['largo']})")
    cmn, cmx = rango("/Camara/Cuerpo")
    altura = cmn[2] - bd["alto"]
    check(abs(altura - cam["altura_sobre_banda"]) < TOL, f"Camara a {altura:.3f} m sobre la banda (dato {cam['altura_sobre_banda']})")
    check(cam["campo_x"] >= W - TOL, f"El campo de la camara ({cam['campo_x']} m) cubre el ancho de los {n} canales ({W:.3f} m)")

    # ---------- distancias informativas (la verificacion 3D real es en la fase 3) ----------
    info = []
    def dist(x, y, cx, cy):
        return math.hypot(x - cx, y - cy)
    lejos20 = max(dist(x, y, cex, cey) for mn, mx in rt.values() for x in (mn[0], mx[0]) for y in (mn[1], mx[1]))
    info.append(f"CR20A -> punto de toma: {dist(tomax, cey, cex, cey):.2f} m (alcance {rb['cr20a_alcance']} m)")
    info.append(f"CR20A -> esquina mas lejana de las tarimas, en planta: {lejos20:.2f} m (alcance {rb['cr20a_alcance']} m)")
    puntos6 = {
        "banda (esquina del campo de camara mas lejana)": max(dist(bx + sx * cam["campo_x"] / 2, camy + sy * cam["campo_y"] / 2, r6x, cey)
                                                             for sx in (-1, 1) for sy in (-1, 1)),
        "bahia mas lejana (esquina)": max(dist(bah_x + sx * bh["largo"] / 2, cey + sy * ((bh["cantidad"] - 1) / 2 * paso + bh["ancho"] / 2), r6x, cey)
                                          for sx in (-1, 1) for sy in (-1, 1)),
        "magazine (esquina mas lejana)": max(dist(r6x + sx * mg["largo"] / 2, cey + mg["dist_y_cr6al"] + sy * mg["ancho"] / 2, r6x, cey)
                                             for sx in (-1, 1) for sy in (-1, 1)),
    }
    for k, v in puntos6.items():
        info.append(f"CR6AL -> {k}: {v:.2f} m (alcance {rb['cr6al_alcance']} m)")

    ok = sum(c.startswith("OK") for c in chk)
    texto = "\n".join(avisos + [f"Datos: {ruta_datos}", f"VERIFICACION: {ok} de {len(chk)} OK", ""] + chk +
                      ["", "DISTANCIAS EN PLANTA (informativas; el alcance real en 3D se verifica en la fase 3)", ""] + info +
                      ["", "Supuestos marcados en celda.json:"] + [f"  - {x}" for x in d.get("_supuestos", [])])
    return mostrar(texto, "Layout: verificacion", 900, 650)


_main()
