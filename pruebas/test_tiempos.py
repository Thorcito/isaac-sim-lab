"""Pruebas de celda/tiempos.py: perfiles trapezoidales y tabla de movimientos de los robots."""
import math

import pytest

from celda import tiempos


def test_trapecio_con_crucero():
    # 1 rad a 1 rad/s con 2 rad/s2: acelera 0,5 s, crucero 0,5 s, frena 0,5 s
    assert tiempos.trapecio(1.0, 1.0, 2.0) == pytest.approx(1.5)


def test_trapecio_triangular():
    # 0,1 m a 1 m/s con 2 m/s2: no llega a la velocidad maxima
    assert tiempos.trapecio(0.1, 1.0, 2.0) == pytest.approx(2 * math.sqrt(0.05))


def test_trapecio_cero_y_signo():
    assert tiempos.trapecio(0.0, 1.0, 1.0) == 0.0
    assert tiempos.trapecio(-0.5, 1.0, 2.0) == tiempos.trapecio(0.5, 1.0, 2.0)


@pytest.fixture(scope="module")
def T(celda, robots):
    D, S = celda
    return tiempos.Tiempos(D, S, robots)


@pytest.mark.lento
def test_todos_los_puntos_tienen_solucion(T):
    assert not T.sin_solucion, "\n".join(T.sin_solucion)


@pytest.mark.lento
def test_movimientos_tipo_en_rango(T):
    """Ningun movimiento tipo da 0 ni un disparate (mas de 15 s)."""
    filas = T.resumen()
    nombres = " ".join(f["movimiento"] for f in filas)
    for clave in ("Tomar caja plana", "Abrir la caja", "Tomar estuche del canal", "Encajar en",
                  "Desviar", "Tomar caja en el punto fijo", "Dejar en la tarima"):
        assert clave in nombres
    for f in filas:
        assert 0.3 < f["min"] <= f["medio"] <= f["max"] < 15.0, f


@pytest.mark.lento
def test_simetria_y_triangulo(T):
    a, b, c = "canal1", "B1/0", "B4/35"
    assert T.mover("cr6al", a, b) == pytest.approx(T.mover("cr6al", b, a))
    # ir de a a c pasando por b no puede ser mas rapido que ir directo
    assert T.mover("cr6al", a, c) <= T.mover("cr6al", a, b) + T.mover("cr6al", b, c) + 1e-9


@pytest.mark.lento
def test_mas_lento_si_baja_la_velocidad(celda, robots):
    D, S = celda
    S2 = dict(S, robots_movimiento=dict(S["robots_movimiento"], factor_velocidad=0.5))
    T1, T2 = tiempos.Tiempos(D, S, robots), tiempos.Tiempos(D, S2, robots)
    assert T2.mover("cr20a", "toma", "Norte/5/1") > T1.mover("cr20a", "toma", "Norte/5/1")


@pytest.mark.lento
def test_vertical_en_la_caja_mas_largo_abajo(T):
    """Dejar un estuche en la capa de abajo baja mas que en la de arriba."""
    assert T.dejar("cr6al", "B1/0") > T.dejar("cr6al", "B1/35")
