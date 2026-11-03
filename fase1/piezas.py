"""Fase 1 · Geometria de la celda calculada desde celda.json (sin Isaac Sim).

Que hace:   convierte las medidas de celda.json en una lista de piezas (cajas con
            centro, tamano y color) y en algunos puntos derivados (punto de toma,
            altura de la camara, cajas de cada camada). Es el UNICO lugar donde se
            hacen esas cuentas: armar_escena.py construye estas piezas,
            verificar_escena.py las mide y fase2/robots.py usa los mismos puntos.
Como usar:  no se corre solo; los scripts lo cargan con correr("fase1/piezas.py").
Que esperar: define las funciones piezas, rect_tarima, cajas_camada, punto_toma,
            camara_z y ancho_canales. No abre ventanas.

PROBADO EN LA MAQUINA: no (probado en PC con usd-core)
"""
import math

# Colores de cada tipo de pieza (solo visual; no son medidas, por eso no estan en celda.json)
COLOR = {
    "piso": (0.55, 0.55, 0.55), "zona": (0.95, 0.80, 0.10), "paso": (0.30, 0.65, 0.35),
    "tarima": (0.72, 0.53, 0.30), "pedestal": (0.25, 0.25, 0.30), "banda": (0.20, 0.20, 0.22),
    "canal_a": (0.35, 0.35, 0.40), "canal_b": (0.45, 0.45, 0.50), "divisor": (0.80, 0.80, 0.80),
    "minibanda": (0.20, 0.35, 0.60), "toma": (0.90, 0.15, 0.15), "bahia": (0.30, 0.60, 0.35),
    "magazine": (0.60, 0.40, 0.70), "camara": (0.10, 0.10, 0.10), "campo": (0.20, 0.80, 0.90),
    "portico": (0.70, 0.70, 0.72), "tablero": (0.35, 0.37, 0.40), "tablet": (0.15, 0.15, 0.15),
    "baliza": (0.90, 0.30, 0.10),
}

# Espesores de lo que solo se pinta o marca (visual)
LINEA = 0.05        # ancho de la linea amarilla de la zona de estiba
PINTURA = 0.002     # espesor de la pintura de piso
PERFIL = 0.04       # perfil de aluminio del portico de la camara
TOPE = (0.03, 0.06) # tope neumatico de la mini-banda: largo en X y alto


def _girado(sx, sy, rot_z):
    """Tamano en planta de un rectangulo sx x sy girado rot_z grados (multiplos de 90)."""
    return (sy, sx) if round(rot_z / 90) % 2 else (sx, sy)


def rect_tarima(D, S, nombre):
    """(x_min, y_min, x_max, y_max) de una tarima en planta."""
    t = S["tarimas"][nombre]
    sx, sy = _girado(D["tarima"][0], D["tarima"][1], t["rot_z"])
    cx, cy = t["centro"]
    return (cx - sx / 2, cy - sy / 2, cx + sx / 2, cy + sy / 2)


def ancho_canales(D, S):
    """Ancho util de los canales de la banda, con sus divisores."""
    b = S["banda"]
    return D["canales"] * b["ancho_canal"] + (D["canales"] - 1) * b["divisor"]


def camara_z(D, S):
    """Altura de la cara inferior de la camara: banda + dato del ejercicio."""
    return S["banda"]["alto"] + D["camara"]["altura_sobre_banda"]


def punto_toma(D, S):
    """Centro, en planta, de la caja detenida contra el tope de la mini-banda."""
    mb = S["minibanda"]
    return (mb["x_inicio"] + D["minibanda_largo"] - S["caja"]["largo"] / 2, mb["y_centro"])


def altura_estiba_tope(D, S):
    """Z del tope de la estiba mas alta posible, segun como se lea 'estiba hasta 1,4 m'."""
    if S["estiba_max_desde"] == "tarima":
        return S["tarima_alto"] + D["estiba_max"]
    return D["estiba_max"]


def camadas_posibles(D, S):
    """Cuantas camadas de caja entran bajo el tope de estiba."""
    return int((altura_estiba_tope(D, S) - S["tarima_alto"]) / S["caja"]["alto"] + 1e-9)


def cajas_camada(D, S, nombre, camada):
    """Cajas de una camada (1 = la de abajo) en una tarima: lista de dicts con centro (x, y),
    z_arriba, giro (grados, en el mundo) y medio largo/ancho en planta."""
    t, c, tr = S["tarimas"][nombre], S["caja"], S["trabado"]
    giro_patron = 0 if camada % 2 == 1 else 180   # camadas pares: patron girado 180 grados
    a = math.radians(t["rot_z"] + giro_patron)
    cx, cy = t["centro"]
    z = S["tarima_alto"] + camada * c["alto"]
    out = []
    for px, py, g in tr["patron_A"]:
        x = cx + px * math.cos(a) - py * math.sin(a)
        y = cy + px * math.sin(a) + py * math.cos(a)
        giro = (t["rot_z"] + giro_patron + g) % 360
        hx, hy = _girado(c["largo"] / 2, c["ancho"] / 2, giro)
        out.append({"centro": (x, y), "z_arriba": z, "giro": giro, "medio": (hx, hy)})
    return out


def piezas(D, S):
    """Lista de piezas de la escena. Cada una: ruta (relativa a /World/Celda), centro, tam, color."""
    P = []

    def caja(ruta, centro, tam, color):
        P.append({"ruta": ruta, "centro": tuple(centro), "tam": tuple(tam), "color": COLOR[color]})

    def caja_suelo(ruta, cx, cy, sx, sy, alto, color):
        """Caja apoyada en el piso (z de 0 a alto)."""
        caja(ruta, (cx, cy, alto / 2), (sx, sy, alto), color)

    Lx, Wy = D["piso"]
    caja("/Piso", (Lx / 2, Wy / 2, -0.01), (Lx, Wy, 0.02), "piso")

    # Pasos de personal pintados de lado a lado del piso
    for n, (y0, y1) in S["pasos_personal"].items():
        caja(f"/Pasos/{n}", (Lx / 2, (y0 + y1) / 2, PINTURA / 2), (Lx, y1 - y0, PINTURA), "paso")

    # Zona de estiba: 4 lineas por DENTRO del borde, asi el grupo mide justo el lado del dato
    ex, ey = S["zona_estiba_centro"]
    L = D["zona_estiba_lado"]
    z = PINTURA * 1.5
    caja("/ZonaEstiba/LineaN", (ex, ey + L / 2 - LINEA / 2, z), (L, LINEA, PINTURA), "zona")
    caja("/ZonaEstiba/LineaS", (ex, ey - L / 2 + LINEA / 2, z), (L, LINEA, PINTURA), "zona")
    caja("/ZonaEstiba/LineaE", (ex + L / 2 - LINEA / 2, ey, z), (LINEA, L, PINTURA), "zona")
    caja("/ZonaEstiba/LineaO", (ex - L / 2 + LINEA / 2, ey, z), (LINEA, L, PINTURA), "zona")

    for n in S["tarimas"]:
        x0, y0, x1, y1 = rect_tarima(D, S, n)
        caja_suelo(f"/ZonaEstiba/Tarimas/{n}", (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0, S["tarima_alto"], "tarima")
    p = S["pedestal_cr20a"]
    caja_suelo("/ZonaEstiba/Pedestal_CR20A", *p["centro"], p["lado"], p["lado"], p["alto"], "pedestal")

    # Banda de 5 canales: estructura + franja de cada canal + divisores (guias) entre canales
    b = S["banda"]
    W = ancho_canales(D, S)
    bl, bx = b["x_fin"] - b["x_inicio"], (b["x_inicio"] + b["x_fin"]) / 2
    caja_suelo("/Alimentacion/Banda/Estructura", bx, b["y_centro"], bl, W + 2 * b["margen_estructura"], b["alto"] - 0.01, "banda")
    y = b["y_centro"] - W / 2
    for i in range(D["canales"]):
        caja(f"/Alimentacion/Banda/Canal{i + 1}", (bx, y + b["ancho_canal"] / 2, b["alto"] - 0.005),
             (bl, b["ancho_canal"], 0.01), "canal_a" if i % 2 == 0 else "canal_b")
        y += b["ancho_canal"]
        if i < D["canales"] - 1:
            caja(f"/Alimentacion/Banda/Divisor{i + 1}", (bx, y + b["divisor"] / 2, b["alto"] + 0.02), (bl, b["divisor"], 0.04), "divisor")
            y += b["divisor"]

    # Mini-banda, tope y punto de toma
    mb = S["minibanda"]
    x0 = mb["x_inicio"]
    x1 = x0 + D["minibanda_largo"]
    caja_suelo("/Alimentacion/MiniBanda", (x0 + x1) / 2, mb["y_centro"], x1 - x0, mb["ancho"], mb["alto"], "minibanda")
    caja("/Alimentacion/Tope", (x1 - TOPE[0] / 2, mb["y_centro"], mb["alto"] + TOPE[1] / 2), (TOPE[0], mb["ancho"], TOPE[1]), "toma")
    tx, ty = punto_toma(D, S)
    c = S["caja"]
    caja("/Alimentacion/PuntoToma", (tx, ty, mb["alto"] + PINTURA / 2), (c["largo"], c["ancho"], PINTURA), "toma")

    bh = S["bahias"]
    for n, (cx, cy) in bh["centros"].items():
        caja_suelo(f"/Alimentacion/Bahias/{n}", cx, cy, bh["largo"], bh["ancho"], bh["alto"], "bahia")
    p = S["pedestal_cr6al"]
    caja_suelo("/Alimentacion/Pedestal_CR6AL", *p["centro"], p["lado"], p["lado"], p["alto"], "pedestal")
    m = S["magazine"]
    caja_suelo("/Alimentacion/Magazine", *m["centro"], m["largo"], m["ancho"], m["alto"], "magazine")

    # Camara en un portico: el campo de 0,67 m va a traves de los canales (eje Y)
    cam = S["camara"]
    fx, fy = cam["campo_centro"]
    largo_campo, ancho_campo = D["camara"]["campo"][1], D["camara"]["campo"][0]
    zc = camara_z(D, S)
    alto_portico = zc + cam["cuerpo_alto"]
    caja("/Camara/Cuerpo", (fx, fy, zc + cam["cuerpo_alto"] / 2), (0.08, 0.12, cam["cuerpo_alto"]), "camara")
    caja("/Camara/Campo", (fx, fy, b["alto"] + PINTURA / 2), (largo_campo, ancho_campo, PINTURA), "campo")
    for n, s in (("PataN", 1), ("PataS", -1)):
        caja_suelo(f"/Camara/{n}", fx, fy + s * cam["portico_separacion"] / 2, PERFIL, PERFIL, alto_portico, "portico")
    caja("/Camara/Viga", (fx, fy, alto_portico + PERFIL / 2), (PERFIL, cam["portico_separacion"] + PERFIL, PERFIL), "portico")

    for n in ("tablero", "tablet", "baliza"):
        e = S[n]
        caja_suelo(f"/Control/{n.capitalize()}", *e["centro"], e["tam"][0], e["tam"][1], e["tam"][2], n)
    return P
