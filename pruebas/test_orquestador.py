"""Pruebas de celda/orquestador.py: decisiones y manejo de fallas, sin modelo de tiempo."""
import copy

import pytest

from celda.orquestador import Orquestador

POLITICA = {"duda": "desviar", "desconocida": "desviar", "sin_carton": "seguir", "aviso_carton_bajo": 5,
            "rechazos_seguidos_para_detener": 5, "cr6al_toma_por_ciclo": 1}


def est(id, variedad=None, categoria="variedad"):
    return {"id": id, "categoria": categoria, "variedad": variedad}


def vista(**cambios):
    v = {
        "canales": [[], [], [], [], []], "cola": [0] * 5, "cola_max": 8,
        "bahias": {b: {"variedad": var, "estado": "lista", "cuenta": 0, "reservados": 0, "capacidad": 36}
                   for b, var in (("B1", "A"), ("B2", "B"), ("B3", "C"), ("B4", "D"))},
        "carton": 40, "minibanda": [],
        "tarimas": {t: {"variedad": var, "cajas": 0, "capacidad": 50, "en_cambio": False}
                    for t, var in (("Norte", "A"), ("Este", "B"), ("Oeste", "C"), ("Sur", "D"))},
        "herramienta_doble": False, "parada": False,
    }
    v.update(cambios)
    v["cola"] = [len(c) for c in v["canales"]]
    return v


def test_politica_invalida_da_error():
    with pytest.raises(ValueError):
        Orquestador(dict(POLITICA, duda="tirar"))


def test_arma_caja_si_la_bahia_esta_vacia():
    o = Orquestador(POLITICA)
    v = vista(canales=[[est(1, "C")], [], [], [], []])
    v["bahias"]["B3"]["estado"] = "vacia"
    a = o.siguiente_cr6al(v)
    assert (a.tipo, a.datos["bahia"]) == ("armar", "B3")
    assert o.estado["cr6al"] == "armando"


def test_sin_carton_no_arma_y_sigue_con_otras_variedades():
    o = Orquestador(POLITICA)
    v = vista(carton=0, canales=[[est(1, "C"), est(2, "A")], [], [], [], []])
    v["bahias"]["B3"]["estado"] = "vacia"
    o.evento("sin_carton")
    a = o.siguiente_cr6al(v)
    assert a.tipo == "encajar" and a.datos["tomas"] == [(0, 2, "B1")]
    assert o.baliza == "amarillo"
    o.evento("carton_repuesto")
    assert o.baliza == "verde"


def test_sin_carton_con_politica_detener_para_la_banda():
    o = Orquestador(dict(POLITICA, sin_carton="detener"))
    v = vista(carton=0)
    v["bahias"]["B1"]["estado"] = "vacia"
    assert o.accion_banda(v).tipo == "detener"


def test_encaja_primero_el_canal_mas_lleno():
    o = Orquestador(POLITICA)
    v = vista(canales=[[est(1, "A")], [est(2, "B"), est(3, "B"), est(4, "B")], [], [], []])
    a = o.siguiente_cr6al(v)
    assert a.datos["tomas"][0][0] == 1


def test_bahia_llena_o_saliendo_no_recibe():
    o = Orquestador(POLITICA)
    v = vista(canales=[[est(1, "A"), est(2, "B")], [], [], [], []])
    v["bahias"]["B1"].update(cuenta=36)
    v["bahias"]["B2"]["estado"] = "saliendo"
    assert o.siguiente_cr6al(v).tipo == "esperar"


def test_respeta_lugares_reservados():
    o = Orquestador(dict(POLITICA, cr6al_toma_por_ciclo=3))
    v = vista(canales=[[est(1, "A"), est(2, "A"), est(3, "A")], [], [], [], []])
    v["bahias"]["B1"].update(cuenta=34)
    a = o.siguiente_cr6al(v)
    assert len(a.datos["tomas"]) == 2


@pytest.mark.parametrize("categoria", ["duda", "desconocida"])
def test_rechazo_segun_politica(categoria):
    v = vista(canales=[[est(9, None, categoria)], [], [], [], []])
    assert Orquestador(POLITICA).siguiente_cr6al(v).tipo == "desviar"
    assert Orquestador(dict(POLITICA, **{categoria: "dejar_pasar"})).accion_banda(v).tipo == "dejar_pasar"
    a = Orquestador(dict(POLITICA, **{categoria: "detener"})).accion_banda(v)
    assert a.tipo == "detener" and a.datos["id"] == 9


def test_rechazo_urgente_antes_que_encajar():
    """Si el canal esta por llenarse, el rechazo se saca antes de seguir encajando."""
    o = Orquestador(POLITICA)
    fila = [est(1, None, "duda")] + [est(i, "A") for i in range(2, 9)]
    v = vista(canales=[fila, [], [], [], []])
    assert o.siguiente_cr6al(v).tipo == "desviar"


def test_muchos_rechazos_seguidos_detiene():
    o = Orquestador(POLITICA)
    for _ in range(5):
        o.evento("rechazo")
    assert o.accion_banda(vista()).tipo == "detener"
    o.evento("parada")
    assert o.baliza == "rojo"
    o.evento("parada_despejada")
    assert o.baliza == "verde" and o.accion_banda(vista()) is None


def test_fila_de_tres():
    o = Orquestador(dict(POLITICA, cr6al_fila=3))
    v = vista(canales=[[est(1, "A"), est(2, "A"), est(3, "A")], [est(4, "B")], [], [], []])
    a = o.siguiente_cr6al(v)
    assert a.tipo == "encajar_fila" and a.datos["ids"] == [1, 2, 3] and a.datos["bahia"] == "B1"


def test_fila_espera_a_juntarse():
    """Con herramienta de fila no toma estuches sueltos si la fila todavia puede completarse."""
    o = Orquestador(dict(POLITICA, cr6al_fila=3))
    v = vista(canales=[[est(1, "A"), est(2, "A")], [], [], [], []])
    assert o.siguiente_cr6al(v).tipo == "esperar"
    v = vista(canales=[[est(1, "A"), est(2, "B")], [], [], [], []])   # mezclada: no se va a completar
    assert o.siguiente_cr6al(v).tipo == "encajar"


def test_fila_desalineada_no_se_deja():
    o = Orquestador(dict(POLITICA, cr6al_fila=3))
    v = vista(canales=[[est(1, "A"), est(2, "A"), est(3, "A")], [], [], [], []])
    v["bahias"]["B1"]["cuenta"] = 1
    assert o.siguiente_cr6al(v).tipo != "encajar_fila"


def test_cr20a_estiba_y_espera_tarima_en_cambio():
    o = Orquestador(POLITICA)
    v = vista(minibanda=[{"variedad": "A", "lista": True}])
    assert o.siguiente_cr20a(v).datos == {"cajas": 1}
    v["tarimas"]["Norte"]["en_cambio"] = True
    assert o.siguiente_cr20a(v).tipo == "esperar"
    assert o.estado["cr20a"] == "esperando_tarima"


def test_cr20a_herramienta_doble():
    o = Orquestador(POLITICA)
    v = vista(herramienta_doble=True, minibanda=[{"variedad": "A", "lista": True}, {"variedad": "B", "lista": True}])
    assert o.siguiente_cr20a(v).datos == {"cajas": 2}
    v["tarimas"]["Norte"]["cajas"] = 49
    v["minibanda"][1]["variedad"] = "A"     # las dos a la misma tarima y queda lugar para una sola
    assert o.siguiente_cr20a(v).datos == {"cajas": 1}


def test_vista_no_se_modifica():
    o = Orquestador(POLITICA)
    v = vista(canales=[[est(1, "A")], [], [], [], []])
    copia = copy.deepcopy(v)
    o.siguiente_cr6al(v)
    o.siguiente_cr20a(v)
    o.accion_banda(v)
    assert v == copia
