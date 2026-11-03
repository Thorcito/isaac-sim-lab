"""Recetas: patron de estuches dentro de la caja y trabado de camadas en la tarima.

Que hace:   1) patron_caja: donde va cada estuche dentro de la caja, segun la receta de
               celda.json (3 x 3 x 4), descontando el espesor del carton.
            2) trabado: busca el patron de camada que mejor traba en la tarima de 1,2 x 1,0 m
               con la caja de _supuestos. Prueba patrones de bloques (todas las cajas con el
               mismo giro, o dos bloques con giros distintos), se queda con los que meten mas
               cajas, y elige la pareja camada impar / camada par que mas cajas "puentea"
               (cada caja de arriba apoyada en dos o mas de abajo) y menos juntas repite.
            3) orden_estiba: en que orden deja el CR20A las cajas de una camada.
Como usar:  from celda import recetas
            recetas.trabado(D, S)          -> patrones, puntaje y descripcion
            recetas.patron_caja(S)         -> 36 posiciones de estuche
Sin Isaac Sim: solo Python y numpy. Pruebas: pruebas/test_recetas.py.

Sistema de la tarima: origen en su centro, X sobre el lado de 1,2 m, Y sobre el de 1,0 m.
Cada caja de un patron es [x, y, giro]: giro 0 = largo de la caja en X, 90 = largo en Y.
"""
import itertools
import math

from celda import geometria

TOL = 1e-6          # m: comparaciones de punto flotante
_CACHE = {}         # el trabado se calcula una vez por combinacion de medidas


# ---------------- Estuches dentro de la caja ----------------

def interior_caja(S):
    """Medidas utiles dentro de la caja (largo, ancho, alto), descontando el carton."""
    c = S["caja"]
    e = c["espesor_pared"]
    # paredes a los dos lados; abajo, las dos solapas del fondo encimadas
    return c["largo"] - 2 * e, c["ancho"] - 2 * e, c["alto"] - 2 * e


def _orientaciones(estuche):
    """Las 6 formas de poner el estuche en la caja: (medida en X, en Y, en Z, nombre)."""
    l, w, h = estuche["largo"], estuche["ancho"], estuche["alto"]
    nombres = {"largo": l, "ancho": w, "alto": h}
    out = []
    for a, b, c in itertools.permutations(nombres):
        out.append((nombres[a], nombres[b], nombres[c], f"{a} en X, {b} en Y, {c} en Z"))
    return out


def mejor_receta_caja(S):
    """La orientacion que mas estuches mete en la caja (solo informativo: compara con la receta)."""
    L, W, H = interior_caja(S)
    mejor = None
    for dx, dy, dz, nombre in _orientaciones(S["estuche"]):
        n = (int(L / dx + TOL), int(W / dy + TOL), int(H / dz + TOL))
        total = n[0] * n[1] * n[2]
        if mejor is None or total > mejor["total"]:
            mejor = {"total": total, "grilla": n, "orientacion": nombre}
    return mejor


def patron_caja(S):
    """Posiciones de los estuches de la receta, en orden de llenado (capa de abajo primero).

    Cada una: {"i", "capa", "centro": (x, y, z)}. Origen en el centro del fondo interior de la caja,
    X sobre el largo de la caja; z es la cara de ARRIBA del estuche (donde apoya la ventosa).
    El estuche va acostado, con su largo sobre el largo de la caja (como llega por la banda).
    """
    r, e = S["receta_encajado"], S["estuche"]
    L, W, H = interior_caja(S)
    nx, ny, nz = r["a_lo_largo"], r["a_lo_ancho"], r["capas"]
    lx, ly, lz = e["largo"], e["ancho"], e["alto"]
    if nx * lx > L + TOL or ny * ly > W + TOL or nz * lz > H + TOL:
        raise ValueError(f"La receta {nx} x {ny} x {nz} no entra en la caja: necesita "
                         f"{nx * lx:.3f} x {ny * ly:.3f} x {nz * lz:.3f} m y hay {L:.3f} x {W:.3f} x {H:.3f} m")
    out = []
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                x = (i - (nx - 1) / 2) * lx
                y = (j - (ny - 1) / 2) * ly
                out.append({"i": len(out), "capa": k + 1, "centro": (x, y, (k + 1) * lz)})
    return out


def masa_caja_llena(S):
    """kg de una caja llena: estuches de la receta + caja vacia."""
    r = S["receta_encajado"]
    return r["a_lo_largo"] * r["a_lo_ancho"] * r["capas"] * S["estuche"]["masa_kg"] + S["caja"]["masa_vacia_kg"]


# ---------------- Trabado de camadas ----------------

def _rect(x, y, giro, l, w):
    """(x0, y0, x1, y1) de una caja centrada en (x, y)."""
    hx, hy = (l / 2, w / 2) if giro % 180 == 0 else (w / 2, l / 2)
    return (x - hx, y - hy, x + hx, y + hy)


def rects(patron, caja):
    return [_rect(x, y, g, caja["largo"], caja["ancho"]) for x, y, g in patron]


def _area_comun(a, b):
    dx = min(a[2], b[2]) - max(a[0], b[0])
    dy = min(a[3], b[3]) - max(a[1], b[1])
    return dx * dy if dx > TOL and dy > TOL else 0.0


def _bloque(nx, ny, dx, dy, giro, x0, y0):
    """Grilla de nx x ny cajas que empieza en la esquina (x0, y0)."""
    return [[x0 + (i + 0.5) * dx, y0 + (j + 0.5) * dy, giro] for i in range(nx) for j in range(ny)]


def candidatos(Lp, Wp, l, w, voladizo):
    """Patrones de bloques que entran en Lp x Wp con hasta 'voladizo' por lado.

    Familias: un bloque con todas las cajas iguales, o dos bloques (cortando a lo largo de X o
    de Y) con giros distintos. Cada patron queda centrado en la tarima.
    """
    Lt, Wt = Lp + 2 * voladizo, Wp + 2 * voladizo
    giros = {0: (l, w), 90: (w, l)}
    out = []
    for g1, (dx1, dy1) in giros.items():
        # Un bloque
        nx, ny = int(Lt / dx1 + TOL), int(Wt / dy1 + TOL)
        out.append(_bloque(nx, ny, dx1, dy1, g1, -nx * dx1 / 2, -ny * dy1 / 2))
        for g2, (dx2, dy2) in giros.items():
            if g2 == g1:
                continue
            # Dos bloques apilados en Y: k filas del primero y lo que entre del segundo
            for k in range(1, int(Wt / dy1 + TOL)):
                k2 = int((Wt - k * dy1) / dy2 + TOL)
                n1, n2 = int(Lt / dx1 + TOL), int(Lt / dx2 + TOL)
                if k2 < 1:
                    continue
                alto = k * dy1 + k2 * dy2
                y0 = -alto / 2
                out.append(_bloque(n1, k, dx1, dy1, g1, -n1 * dx1 / 2, y0) +
                           _bloque(n2, k2, dx2, dy2, g2, -n2 * dx2 / 2, y0 + k * dy1))
            # Dos bloques lado a lado en X
            for k in range(1, int(Lt / dx1 + TOL)):
                k2 = int((Lt - k * dx1) / dx2 + TOL)
                m1, m2 = int(Wt / dy1 + TOL), int(Wt / dy2 + TOL)
                if k2 < 1:
                    continue
                ancho = k * dx1 + k2 * dx2
                x0 = -ancho / 2
                out.append(_bloque(k, m1, dx1, dy1, g1, x0, -m1 * dy1 / 2) +
                           _bloque(k2, m2, dx2, dy2, g2, x0 + k * dx1, -m2 * dy2 / 2))
    # sin repetidos
    unicos, vistos = [], set()
    for p in out:
        clave = tuple(sorted((round(x, 4), round(y, 4), g % 180) for x, y, g in p))
        if p and clave not in vistos:
            vistos.add(clave)
            unicos.append([[x, y, g % 180] for x, y, g in p])
    return unicos


def transformar(patron, como):
    """Patron girado 180 grados o reflejado. Las cajas son simetricas: el giro queda en 0 o 90."""
    f = {"igual": (1, 1), "giro_180": (-1, -1), "espejo_x": (-1, 1), "espejo_y": (1, -1)}[como]
    return [[f[0] * x, f[1] * y, g] for x, y, g in patron]


def _unir(intervalos):
    """Une intervalos [a, b] que se tocan o se pisan."""
    out = []
    for a, b in sorted(intervalos):
        if out and a <= out[-1][1] + TOL:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def _juntas(rs):
    """Juntas de una camada (lados de caja que no estan en su borde exterior).

    Devuelve {(eje, coordenada): [intervalos unidos]}: eje "x" = junta vertical en x = coordenada.
    """
    x0, y0 = min(r[0] for r in rs), min(r[1] for r in rs)
    x1, y1 = max(r[2] for r in rs), max(r[3] for r in rs)
    crudo = {}
    for r in rs:
        for c in (r[0], r[2]):
            if abs(c - x0) > TOL and abs(c - x1) > TOL:
                crudo.setdefault(("x", round(c, 4)), []).append((r[1], r[3]))
        for c in (r[1], r[3]):
            if abs(c - y0) > TOL and abs(c - y1) > TOL:
                crudo.setdefault(("y", round(c, 4)), []).append((r[0], r[2]))
    return {k: _unir(v) for k, v in crudo.items()}


def puntaje_traba(abajo, arriba, caja, frac_minima):
    """Que tan bien traba 'arriba' sobre 'abajo'.

    puentes: fraccion de cajas de arriba apoyadas en 2 o mas cajas de abajo (cada apoyo con al menos
             frac_minima del area de la caja). 1.0 = todas puentean.
    juntas_m: metros de junta de arriba que caen justo sobre una junta de abajo (0 = ninguna).
    apoyo_min: la menor fraccion de area apoyada de una caja de arriba (1.0 = ninguna en el aire).
    """
    ra, rb = rects(abajo, caja), rects(arriba, caja)
    area = caja["largo"] * caja["ancho"]
    puentes, apoyo_min = 0, 1.0
    for r in rb:
        comunes = [_area_comun(r, s) for s in ra]
        if sum(1 for a in comunes if a >= frac_minima * area) >= 2:
            puentes += 1
        apoyo_min = min(apoyo_min, sum(comunes) / area)
    ja, jb = _juntas(ra), _juntas(rb)
    largo = 0.0
    for k in set(ja) & set(jb):
        for a1, b1 in ja[k]:
            for a2, b2 in jb[k]:
                largo += max(0.0, min(b1, b2) - max(a1, a2))
    return {"puentes": puentes / len(rb), "juntas_m": largo, "apoyo_min": apoyo_min}


def voladizo(patron, caja, Lp, Wp):
    """Lo maximo que una caja sale del borde de la tarima (m, 0 si ninguna sale)."""
    v = 0.0
    for x0, y0, x1, y1 in rects(patron, caja):
        v = max(v, -Lp / 2 - x0, x1 - Lp / 2, -Wp / 2 - y0, y1 - Wp / 2)
    return max(v, 0.0)


def trabado(D, S):
    """Elige el patron de camada impar y el de camada par.

    Devuelve dict: impar, par (listas [x, y, giro]), cajas, ocupacion (area de cajas / area de
    tarima), voladizo, puentes, juntas_m, apoyo_min, transformacion (como se obtiene la camada par)
    y descripcion. Criterio: mas cajas; despues mas puentes; despues menos juntas repetidas;
    despues preferir que la camada par sea la impar girada o reflejada (mas facil de explicar).
    """
    tr, caja = S["trabado"], S["caja"]
    Lp, Wp = D["tarima"]
    clave = (Lp, Wp, caja["largo"], caja["ancho"], tr["voladizo_max"], tr["frac_apoyo_puente"])
    if clave in _CACHE:
        return _CACHE[clave]
    cands = candidatos(Lp, Wp, caja["largo"], caja["ancho"], tr["voladizo_max"])
    n_max = max(len(p) for p in cands)
    mejores = [p for p in cands if len(p) == n_max]
    opciones = []
    for ip, P in enumerate(mejores):
        variantes = [(t, transformar(P, t)) for t in ("giro_180", "espejo_x", "espejo_y")]
        variantes += [(f"patron {iq + 1}", Q) for iq, Q in enumerate(mejores) if iq != ip]
        for nombre, Q in variantes:
            s = puntaje_traba(P, Q, caja, tr["frac_apoyo_puente"])
            s2 = puntaje_traba(Q, P, caja, tr["frac_apoyo_puente"])  # la impar sobre la par
            puentes = min(s["puentes"], s2["puentes"])
            juntas = max(s["juntas_m"], s2["juntas_m"])
            simple = 0 if nombre.startswith(("giro", "espejo")) else 1
            opciones.append(((-puentes, round(juntas, 4), simple, ip), P, Q, nombre,
                             {"puentes": puentes, "juntas_m": juntas, "apoyo_min": min(s["apoyo_min"], s2["apoyo_min"])}))
    opciones.sort(key=lambda o: o[0])
    _, P, Q, nombre, s = opciones[0]
    area = n_max * caja["largo"] * caja["ancho"]
    gir = sum(1 for _, _, g in P if g == 90)
    res = {
        "impar": P, "par": Q, "cajas": n_max, "ocupacion": area / (Lp * Wp),
        "voladizo": max(voladizo(P, caja, Lp, Wp), voladizo(Q, caja, Lp, Wp)),
        "transformacion": nombre, "candidatos": len(cands), **s,
        "descripcion": (f"{n_max} cajas por camada ({n_max - gir} con el largo en X, {gir} con el largo en Y), "
                        f"{area / (Lp * Wp) * 100:.0f} % de la tarima. Camada par = impar con {nombre.replace('_', ' ')}: "
                        f"{s['puentes'] * 100:.0f} % de las cajas puentean, {s['juntas_m']:.2f} m de juntas repetidas."),
    }
    _CACHE[clave] = res
    return res


def orden_estiba(D, S, nombre, camada):
    """Cajas de una camada en el orden en que las deja el CR20A: de la mas lejana a la mas cercana.

    Asi el brazo nunca pasa bajo por encima de una caja recien puesta de la misma camada.
    """
    ex, ey = S["pedestal_cr20a"]["centro"]
    cajas = geometria.cajas_camada(D, S, nombre, camada)
    return sorted(cajas, key=lambda c: -math.hypot(c["centro"][0] - ex, c["centro"][1] - ey))


def altura_estiba(D, S):
    """Z del tope de la estiba completa (desde el piso) y el limite que pide el ejercicio."""
    n = geometria.camadas_posibles(D, S)
    return S["tarima_alto"] + n * S["caja"]["alto"], geometria.altura_estiba_tope(D, S), n


def puntos_estiba(D, S):
    """Todos los puntos donde el CR20A deja una caja, en orden de estiba.

    Lista de dicts: tarima, camada, orden (1 = la primera de la camada), punto (x, y, z) con z en
    la cara de arriba de la caja recien puesta (donde apoya la ventosa) y giro en el mundo.
    """
    out = []
    for nombre in S["tarimas"]:
        for camada in range(1, geometria.camadas_posibles(D, S) + 1):
            for k, c in enumerate(orden_estiba(D, S, nombre, camada)):
                out.append({"tarima": nombre, "camada": camada, "orden": k + 1,
                            "punto": (c["centro"][0], c["centro"][1], c["z_arriba"]), "giro": c["giro"]})
    return out


def puntos_encaje(D, S, bahia):
    """Puntos donde el CR6AL deja cada estuche en la caja de una bahia, en orden de llenado.

    La caja queda centrada en la bahia con su largo en X (la bahia es mas larga en X). z es la cara
    de arriba del estuche recien puesto. Devuelve lista de dicts: i, capa, punto (x, y, z).
    """
    cx, cy = S["bahias"]["centros"][bahia]
    fondo = S["bahias"]["alto"] + 2 * S["caja"]["espesor_pared"]
    return [{"i": p["i"], "capa": p["capa"], "punto": (cx + p["centro"][0], cy + p["centro"][1], fondo + p["centro"][2])}
            for p in patron_caja(S)]
