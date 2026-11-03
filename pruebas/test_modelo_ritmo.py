"""Pruebas de celda/modelo_ritmo.py: balances, repetibilidad y que cada falla tenga su efecto."""
import copy

import pytest

from celda import modelo_ritmo, tiempos


@pytest.fixture(scope="module")
def T(celda, robots):
    D, S = celda
    return tiempos.Tiempos(D, S, robots)


@pytest.fixture(scope="module")
def corto(celda):
    """S con una simulacion mas corta para que las pruebas sean rapidas."""
    D, S = celda
    S2 = copy.deepcopy(S)
    S2["ritmo"].update(calentamiento_s=300, duracion_s=1800)
    return D, S2


def _esc(S, configuracion="actual", **cambios):
    e = modelo_ritmo.escenarios(S, configuracion)[0]
    e = copy.deepcopy(e)
    e.update(cambios)
    return e


@pytest.mark.lento
def test_repetible_con_la_misma_semilla(corto, T):
    D, S = corto
    a = modelo_ritmo.simular(D, S, T, _esc(S), 15, semilla=3)
    b = modelo_ritmo.simular(D, S, T, _esc(S), 15, semilla=3)
    assert a == b


@pytest.mark.lento
def test_balance_de_estuches(corto, T):
    """Lo que llega = encajado + perdido + desviado + dejado pasar + retenido + lo que queda en la banda (+/- lo de la ventana)."""
    D, S = corto
    r = modelo_ritmo.simular(D, S, T, _esc(S, p_duda=0.05), 20, semilla=1)
    salidas = r["encajados"] + r["perdidos"] + r["desviados"] + r["dejados_pasar"] + r["retenidos"]
    assert abs(r["llegadas"] - salidas) <= 5 * D["canales"] * S["acumulacion_canal"]["capacidad_estuches"]
    assert 0 <= r["ocupacion_cr6al"] <= 1 and 0 <= r["ocupacion_cr20a"] <= 1


@pytest.mark.lento
def test_ritmo_bajo_se_cumple(corto, T):
    """A 6 estuches/min la celda actual sigue el ritmo sin perder nada."""
    D, S = corto
    r = modelo_ritmo.simular(D, S, T, _esc(S), 6, semilla=1)
    assert r["perdidos"] == 0
    assert r["estuches_min"] == pytest.approx(6, abs=0.6)
    assert r["cuello"].startswith("ninguno")


@pytest.mark.lento
def test_cajas_coherentes(corto, T):
    D, S = corto
    r = modelo_ritmo.simular(D, S, T, _esc(S, "propuesta"), 20, semilla=2)
    assert r["cajas_estibadas"] <= r["cajas_llenas"] + 4
    assert r["cajas_llenas"] == pytest.approx(r["encajados"] / 36, abs=4)


@pytest.mark.lento
def test_falta_de_carton_se_nota(corto, T):
    D, S = corto
    base = modelo_ritmo.simular(D, S, T, _esc(S, "propuesta"), 20, semilla=1)
    falta = modelo_ritmo.simular(D, S, T, _esc(S, "propuesta", carton_inicial=3,
                                               politica={"cr6al_fila": 3, "aviso_carton_bajo": 0}), 20, semilla=1)
    assert falta["sin_carton_min"] > 0
    assert falta["perdidos"] > base["perdidos"]


@pytest.mark.lento
def test_dudas_se_desvian_o_detienen(corto, T):
    D, S = corto
    r = modelo_ritmo.simular(D, S, T, _esc(S, "propuesta", p_duda=0.05), 20, semilla=1)
    assert r["desviados"] > 0
    r = modelo_ritmo.simular(D, S, T, _esc(S, "propuesta", p_duda=0.05, politica={"cr6al_fila": 3, "duda": "detener"}), 20, semilla=1)
    assert r["paradas"] > 0 and r["parada_min"] > 0
    r = modelo_ritmo.simular(D, S, T, _esc(S, "propuesta", p_duda=0.05, politica={"cr6al_fila": 3, "duda": "dejar_pasar"}), 20, semilla=1)
    assert r["dejados_pasar"] > 0 and r["desviados"] == 0


@pytest.mark.lento
def test_fuera_de_receta_nunca_se_encaja(corto, T):
    D, S = corto
    e = _esc(S)
    e["mezcla"] = dict(e["mezcla"], X=0.2)
    r = modelo_ritmo.simular(D, S, T, e, 15, semilla=1)
    assert r["mal_encajados"] == 0 and r["desviados"] > 0


@pytest.mark.lento
def test_propuesta_llega_a_20(corto, T):
    D, S = corto
    r = modelo_ritmo.simular(D, S, T, _esc(S, "propuesta"), 20, semilla=1)
    assert r["estuches_min"] >= 19.5 and r["perdidos"] == 0


@pytest.mark.lento
def test_actual_no_llega_a_15(corto, T):
    """Hallazgo del modelo: con una copa y variedades mezcladas el CR6AL no llega a 15/min."""
    D, S = corto
    r = modelo_ritmo.simular(D, S, T, _esc(S), 15, semilla=1)
    assert r["estuches_min"] < 15 and r["cuello"] == "CR6AL"


def test_fila_distinta_a_la_receta_da_error(corto, T):
    D, S = corto
    with pytest.raises(ValueError, match="a_lo_largo"):
        modelo_ritmo.Planta(D, S, T, _esc(S, "propuesta", politica={"cr6al_fila": 2}), 20, 1)
