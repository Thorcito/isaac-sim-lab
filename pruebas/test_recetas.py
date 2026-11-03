"""Pruebas de celda/recetas.py: estuches en la caja y trabado de camadas en la tarima."""
import copy

import pytest

from celda import cinematica, geometria, recetas

TOL = 1e-6


def _solapan(a, b):
    return a[0] < b[2] - TOL and b[0] < a[2] - TOL and a[1] < b[3] - TOL and b[1] < a[3] - TOL


# ---------------- Estuches en la caja ----------------

def test_receta_entra_en_la_caja(celda):
    D, S = celda
    pos = recetas.patron_caja(S)
    r = S["receta_encajado"]
    assert len(pos) == r["a_lo_largo"] * r["a_lo_ancho"] * r["capas"]
    L, W, H = recetas.interior_caja(S)
    e = S["estuche"]
    for p in pos:
        x, y, z = p["centro"]
        assert abs(x) + e["largo"] / 2 <= L / 2 + TOL
        assert abs(y) + e["ancho"] / 2 <= W / 2 + TOL
        assert z <= H + TOL


def test_estuches_sin_solapes(celda):
    D, S = celda
    e = S["estuche"]
    cajas = [(p["centro"][0] - e["largo"] / 2, p["centro"][1] - e["ancho"] / 2,
              p["centro"][0] + e["largo"] / 2, p["centro"][1] + e["ancho"] / 2, p["capa"]) for p in recetas.patron_caja(S)]
    for i, a in enumerate(cajas):
        for b in cajas[i + 1:]:
            assert not (a[4] == b[4] and _solapan(a, b)), f"estuches {a} y {b} se pisan"


def test_receta_es_la_que_mas_mete(celda):
    """La receta de celda.json aprovecha la caja tanto como la mejor orientacion posible."""
    D, S = celda
    r = S["receta_encajado"]
    assert recetas.mejor_receta_caja(S)["total"] == r["a_lo_largo"] * r["a_lo_ancho"] * r["capas"]


def test_receta_que_no_entra_da_error(celda):
    D, S = celda
    S2 = copy.deepcopy(S)
    S2["receta_encajado"]["capas"] = 5
    with pytest.raises(ValueError, match="no entra"):
        recetas.patron_caja(S2)


def test_caja_llena_bajo_la_carga_de_los_robots(celda):
    D, S = celda
    m = recetas.masa_caja_llena(S)
    assert m + S["herramientas"]["cr20a"]["masa_kg"] <= D["cr20a"]["carga_kg"]
    assert 2 * m + S["herramientas"]["cr20a"]["doble_masa_kg"] <= D["cr20a"]["carga_kg"]
    assert S["estuche"]["masa_kg"] + S["herramientas"]["cr6al"]["masa_kg"] <= D["cr6al"]["carga_kg"]


# ---------------- Trabado ----------------

@pytest.mark.parametrize("lado", ["impar", "par"])
def test_camada_sin_solapes_y_dentro_del_voladizo(celda, lado):
    D, S = celda
    t = recetas.trabado(D, S)
    rs = recetas.rects(t[lado], S["caja"])
    for i, a in enumerate(rs):
        for b in rs[i + 1:]:
            assert not _solapan(a, b), f"cajas {a} y {b} se pisan"
    assert recetas.voladizo(t[lado], S["caja"], *D["tarima"]) <= S["trabado"]["voladizo_max"] + TOL


def test_trabado_llena_la_tarima_y_traba(celda):
    D, S = celda
    t = recetas.trabado(D, S)
    Lp, Wp = D["tarima"]
    c = S["caja"]
    cota = int((Lp + 2 * S["trabado"]["voladizo_max"]) * (Wp + 2 * S["trabado"]["voladizo_max"]) / (c["largo"] * c["ancho"]))
    assert t["cajas"] == cota, "hay un patron con mas cajas que el elegido"
    assert t["puentes"] == 1.0, "alguna caja de arriba apoya en una sola de abajo"
    assert t["apoyo_min"] >= 1.0 - 1e-6, "alguna caja queda con parte en el aire"
    assert t["impar"] != t["par"], "las camadas no alternan"


def test_voladizo_cero_tambien_funciona(celda):
    """Con voladizo 0 la caja de _supuestos sigue entrando exacta (10 cajas)."""
    D, S = celda
    S2 = copy.deepcopy(S)
    S2["trabado"]["voladizo_max"] = 0.0
    assert recetas.trabado(D, S2)["cajas"] == 10


@pytest.mark.parametrize("desde", ["tarima", "piso"])
def test_altura_de_estiba(celda, desde):
    D, S = celda
    S2 = dict(S, estiba_max_desde=desde)
    alto, limite, n = recetas.altura_estiba(D, S2)
    assert alto <= limite + TOL
    assert alto + S["caja"]["alto"] > limite, "entra una camada mas de las que se usan"
    if desde == "piso":
        assert limite == D["estiba_max"]


def test_camadas_en_la_escena_usan_el_trabado(celda):
    D, S = celda
    t = recetas.trabado(D, S)
    for camada in (1, 2):
        cajas = geometria.cajas_camada(D, S, "Norte", camada)
        assert len(cajas) == t["cajas"]


def test_orden_de_estiba_de_lejos_a_cerca(celda):
    D, S = celda
    import math
    ex, ey = S["pedestal_cr20a"]["centro"]
    d = [math.hypot(c["centro"][0] - ex, c["centro"][1] - ey) for c in recetas.orden_estiba(D, S, "Sur", 1)]
    assert d == sorted(d, reverse=True)


# ---------------- Alcance a cada punto de dejada ----------------

def _todos_alcanzables(rob, puntos, aprox):
    """Resuelve cada punto y su aproximacion arrancando de la solucion anterior (como se mueve el robot)."""
    faltan, q = [], None
    for nombre, p in puntos:
        for dz in (aprox, 0.0):
            objetivo = (p[0], p[1], p[2] + dz)
            r = cinematica.resolver_abajo(rob["cadena"], rob["T_base"], objetivo, rob["largo"], rob["eje_brida"], q)
            if r["ok"]:
                q = r["q"]
            else:
                faltan.append(f"{nombre} dz={dz}: falta {r['err_pos'] * 100:.1f} cm")
    return faltan


@pytest.mark.lento
def test_cr20a_llega_a_cada_caja_de_cada_tarima(celda, robots):
    D, S = celda
    puntos = [(f"{p['tarima']} camada {p['camada']} caja {p['orden']}", p["punto"]) for p in recetas.puntos_estiba(D, S)]
    assert len(puntos) == 4 * geometria.camadas_posibles(D, S) * recetas.trabado(D, S)["cajas"]
    faltan = _todos_alcanzables(robots["cr20a"], puntos, S["aproximacion_z"])
    assert not faltan, "\n".join(faltan)


@pytest.mark.lento
def test_cr6al_llega_a_cada_estuche_de_cada_bahia(celda, robots):
    D, S = celda
    puntos = [(f"{b} estuche {p['i'] + 1}", p["punto"]) for b in S["bahias"]["centros"] for p in recetas.puntos_encaje(D, S, b)]
    faltan = _todos_alcanzables(robots["cr6al"], puntos, S["aproximacion_z"])
    assert not faltan, "\n".join(faltan)
