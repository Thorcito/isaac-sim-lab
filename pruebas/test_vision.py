"""Pruebas de celda/vision.py con imagenes sinteticas de los 5 canales (solo numpy)."""
import math

import numpy as np
import pytest

from celda import vision

ESCALA = 4
VIOLETA = (0.60, 0.20, 0.75)    # fuera de receta, lejos de todas
NARANJA = (0.95, 0.45, 0.10)    # fuera de receta, entre rojo (A) y amarillo (C)


def test_campo_y_resolucion(celda):
    D, S = celda
    ancho, largo = vision.campo_m(D, S)
    assert ancho == pytest.approx(D["camara"]["campo"][0], abs=0.005)
    assert largo == pytest.approx(D["camara"]["campo"][1], abs=0.005)
    # sobre la banda da el dato del ejercicio (0,27 mm/px); sobre el estuche, un poco menos
    mm_banda = vision.mm_por_pixel(D, S) * D["camara"]["altura_sobre_banda"] / vision.intrinsecos(D, S)["z"]
    assert mm_banda == pytest.approx(D["camara"]["mm_por_px"], abs=0.01)


def test_pixel_mundo_ida_y_vuelta(celda):
    D, S = celda
    for x, y in ((1.97, 2.75), (2.2, 2.5), (1.8, 3.0)):
        u, v = vision.mundo_a_pixel(x, y, D, S, ESCALA)
        assert vision.pixel_a_mundo(u, v, D, S, ESCALA) == pytest.approx((x, y))
    k = vision.intrinsecos(D, S, ESCALA)
    assert vision.pixel_a_mundo(k["cx"], k["cy"], D, S, ESCALA) == pytest.approx(tuple(S["camara"]["campo_centro"]))


def test_componentes_conexas():
    m = np.zeros((6, 8), bool)
    m[0:2, 0:2] = True          # bloque 1
    m[4:6, 0:3] = True          # bloque 2
    m[0:6, 6] = True            # columna: 3
    m[2, 5] = True              # pegado a la columna en diagonal? no: (2,5)-(2,6) son vecinos
    lab, n = vision.componentes(m)
    assert n == 3
    assert lab[0, 0] == lab[1, 1] and lab[4, 0] != lab[0, 0] and lab[2, 5] == lab[0, 6]
    assert (lab > 0).sum() == m.sum()


def test_componentes_forma_en_u():
    """Una U se une por abajo aunque las dos patas empiecen separadas."""
    m = np.zeros((5, 5), bool)
    m[0:5, 0] = m[0:5, 4] = m[4, 0:5] = True
    assert vision.componentes(m)[1] == 1


def test_hsv(celda):
    h, s, v = vision.rgb_a_hsv(np.array([[1.0, 0, 0], [0, 1.0, 0], [0, 0, 1.0], [0.5, 0.5, 0.5]]))
    assert list(h[:3]) == pytest.approx([0, 120, 240])
    assert s[3] == 0 and v[3] == 0.5


def _detectar_una(D, S, color, xy=(2.0, 2.75), giro=0.0, **luz):
    img = vision.imagen_sintetica(D, S, [{"color": color, "xy": xy, "giro": giro}], ESCALA,
                                  np.random.default_rng(1), **luz)
    return vision.detectar(img, D, S, ESCALA)


@pytest.mark.parametrize("var", ["A", "B", "C", "D"])
def test_cada_variedad_con_posicion_y_angulo(celda, var):
    D, S = celda
    dets = _detectar_una(D, S, S["variedades"][var]["color"], xy=(2.05, 2.62), giro=7.0)
    assert len(dets) == 1
    d = dets[0]
    assert (d["categoria"], d["variedad"]) == ("variedad", var)
    assert d["confianza"] >= S["vision_umbral_confianza"]
    assert math.dist(d["xy"], (2.05, 2.62)) < 0.003
    assert abs(d["angulo"] - 7.0) < 2.0


def test_color_fuera_de_receta(celda):
    D, S = celda
    d = _detectar_una(D, S, VIOLETA)
    assert len(d) == 1 and d[0]["categoria"] == "desconocida"


def test_color_ambiguo_no_se_ignora(celda):
    """Un tono entre dos variedades nunca se clasifica como una de ellas: queda desconocido o en duda."""
    D, S = celda
    for brillo in (0.6, 1.0, 1.3):
        dets = _detectar_una(D, S, NARANJA, brillo=brillo)
        assert dets and all(d["categoria"] in ("desconocida", "duda") for d in dets)


@pytest.mark.parametrize("brillo", [0.6, 1.3])
def test_brillo_no_cambia_la_variedad(celda, brillo):
    D, S = celda
    d = _detectar_una(D, S, S["variedades"]["C"]["color"], brillo=brillo, ruido=0.03)
    assert [x["variedad"] for x in d] == ["C"]


def test_estuches_tocandose(celda):
    """Dos iguales pegados en el mismo canal se separan; dos distintos pegados tambien."""
    D, S = celda
    e = S["estuche"]
    y = vision.canales_y(D, S)[2]
    x0 = 2.17
    rojo, verde = S["variedades"]["A"]["color"], S["variedades"]["B"]["color"]
    verdad = [{"color": rojo, "xy": (x0, y), "giro": 0}, {"color": rojo, "xy": (x0 - e["largo"], y), "giro": 0},
              {"color": verde, "xy": (x0 - 2 * e["largo"], y), "giro": 0}]
    img = vision.imagen_sintetica(D, S, verdad, ESCALA, np.random.default_rng(2))
    dets = vision.detectar(img, D, S, ESCALA)
    assert sorted(d["variedad"] for d in dets) == ["A", "A", "B"]
    for t in verdad:
        assert min(math.dist(d["xy"], t["xy"]) for d in dets) < 0.006


@pytest.mark.lento
def test_matriz_de_confusion_condiciones_normales(celda):
    D, S = celda
    r = vision.matriz_confusion(D, S, n_imagenes=15, escala=ESCALA, extra={"X": VIOLETA}, condiciones="normales")
    M = r["matriz"]
    for v in S["variedades"]:
        total = sum(M[v].values())
        assert M[v][v] >= 0.95 * total, (v, M[v])
    assert M["X"]["desconocida"] >= 0.9 * sum(M["X"].values())
    assert r["falsos"] == 0 and r["err_mm_max"] < 6


@pytest.mark.lento
def test_matriz_de_confusion_luz_dificil_sin_errores_de_variedad(celda):
    """Con luz mala aparecen dudas, pero ningun estuche va a la caja de otra variedad."""
    D, S = celda
    r = vision.matriz_confusion(D, S, n_imagenes=15, escala=ESCALA, extra={"X": VIOLETA, "Y": NARANJA},
                                condiciones="dificiles")
    M = r["matriz"]
    for verdad in M:
        for pred in S["variedades"]:
            if pred != verdad:
                assert M[verdad][pred] == 0, f"{verdad} clasificado como {pred}"
    assert sum(M[v]["duda"] for v in M) > 0, "con luz mala tendria que haber alguna duda"
