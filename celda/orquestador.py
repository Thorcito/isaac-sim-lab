"""Orquestador: decide que hace cada robot en cada momento y como reacciona a las fallas.

Que hace:   es el papel del PC Linux de la celda. No mueve nada ni mide tiempos: mira una
            "vista" del estado de la planta y devuelve la proxima accion de cada robot, o de
            la banda. La planta puede ser el modelo de ritmo (celda/modelo_ritmo.py) o Isaac
            Sim (adaptador de la etapa 4): las dos le pasan la misma vista y ejecutan las
            mismas acciones.
Como usar:  from celda import orquestador
            o = orquestador.Orquestador(politica)        # politica: _supuestos.politica_fallas
            o.evento("sin_carton")                      # la planta avisa lo que pasa
            o.accion_banda(vista)  -> Accion o None     # compuerta o parada, antes que los robots
            o.siguiente_cr6al(vista) -> Accion          # armar, encajar, desviar o esperar
            o.siguiente_cr20a(vista) -> Accion          # estibar (1 o 2 cajas) o esperar
            o.baliza                                    # "verde", "amarillo" o "rojo"
Sin Isaac Sim: solo Python. Pruebas: pruebas/test_orquestador.py.

Contrato con la planta (lo que tiene que dar un adaptador):
  vista = {
    "canales":  [ [estuche, ...] por canal, solo los visibles, el primero contra el tope ],
                estuche = {"id", "categoria": "variedad" | "duda" | "desconocida", "variedad": "A" | ... | None}
    "cola":     [ largo de la fila de cada canal ],          "cola_max": capacidad de un canal,
    "bahias":   {"B1": {"variedad", "estado": "vacia" | "armando" | "lista" | "saliendo",
                        "cuenta", "reservados", "capacidad"}, ...},
    "carton":   cartones en el magazine,
    "minibanda": [ {"variedad", "lista": True si ya llego al tope o a la fila detras}, ... ] (el primero en el tope),
    "tarimas":  {"Norte": {"variedad", "cajas", "capacidad", "en_cambio"}, ...},
    "herramienta_doble": bool,  "parada": bool,
  }
  Acciones: Accion(tipo, datos) con tipo en
    CR6AL:  "armar" {"bahia"} · "encajar" {"tomas": [(canal, id, bahia), ...]}
            · "encajar_fila" {"canal", "ids", "bahia"} · "desviar" {"canal", "id"} · "esperar"
    CR20A:  "estibar" {"cajas": 1 o 2} · "esperar"
    Banda:  "dejar_pasar" {"canal", "id"} · "detener" {"canal", "id", "motivo"}
  La planta avisa con evento(): sin_carton, carton_repuesto, carton_bajo, bahia_llena, caja_saliendo,
  minibanda_llena, tarima_llena, tarima_cambiada, estuche_dudoso, variedad_desconocida, rechazo,
  encajado, parada, parada_despejada.
"""
from dataclasses import dataclass, field

CATEGORIAS_RECHAZO = ("duda", "desconocida")
POLITICAS = ("desviar", "dejar_pasar", "detener")


@dataclass
class Accion:
    tipo: str
    datos: dict = field(default_factory=dict)


class Orquestador:
    """Maquina de estados de la celda.

    Estados del CR6AL: reposo, armando, encajando, desviando, esperando.
    Estados del CR20A: reposo, estibando, esperando_tarima.
    Baliza: verde (opera), amarillo (alerta: falta carton, tarima en cambio, muchos rechazos),
    rojo (detenida: parada de banda o celda).
    """

    def __init__(self, politica):
        for c in CATEGORIAS_RECHAZO:
            if politica[c] not in POLITICAS:
                raise ValueError(f"politica '{c}' = {politica[c]!r}; tiene que ser una de {POLITICAS}")
        if politica["sin_carton"] not in ("seguir", "detener"):
            raise ValueError("politica 'sin_carton' tiene que ser 'seguir' o 'detener'")
        self.politica = dict(politica)
        self.estado = {"cr6al": "reposo", "cr20a": "reposo"}
        self.alarmas = set()
        self.rechazos_seguidos = 0
        self.registro = []      # (evento, datos) en orden: sirve para el reporte y para depurar

    # ---------------- eventos de la planta ----------------

    def evento(self, nombre, **datos):
        """La planta avisa que algo paso. Actualiza alarmas y baliza."""
        self.registro.append((nombre, datos))
        if nombre in ("sin_carton", "carton_bajo"):
            self.alarmas.add(nombre)
        elif nombre == "carton_repuesto":
            self.alarmas -= {"sin_carton", "carton_bajo"}
        elif nombre == "tarima_llena":
            self.alarmas.add(f"tarima_llena:{datos.get('tarima')}")
        elif nombre == "tarima_cambiada":
            self.alarmas.discard(f"tarima_llena:{datos.get('tarima')}")
        elif nombre == "rechazo":
            self.rechazos_seguidos += 1
            if self.rechazos_seguidos >= self.politica["rechazos_seguidos_para_detener"]:
                self.alarmas.add("muchos_rechazos")
        elif nombre == "encajado":
            self.rechazos_seguidos = 0
        elif nombre == "parada":
            self.alarmas.add("parada")
        elif nombre == "parada_despejada":
            self.alarmas -= {"parada", "muchos_rechazos"}
            self.rechazos_seguidos = 0

    @property
    def baliza(self):
        if "parada" in self.alarmas:
            return "rojo"
        return "amarillo" if self.alarmas else "verde"

    # ---------------- banda: compuerta y paradas ----------------

    def accion_banda(self, vista):
        """Lo que hay que hacer en la banda antes que los robots: dejar pasar o detener."""
        if vista["parada"]:
            return None
        if "muchos_rechazos" in self.alarmas:
            return Accion("detener", {"canal": None, "id": None, "motivo": "muchos rechazos seguidos: revisar camara, luz o receta"})
        if self.politica["sin_carton"] == "detener" and vista["carton"] == 0 and \
                any(b["estado"] == "vacia" for b in vista["bahias"].values()):
            return Accion("detener", {"canal": None, "id": None, "motivo": "sin carton"})
        for c, fila in enumerate(vista["canales"]):
            for e in fila:
                p = self.politica.get(e["categoria"])
                if p == "dejar_pasar":
                    return Accion("dejar_pasar", {"canal": c, "id": e["id"]})
                if p == "detener":
                    return Accion("detener", {"canal": c, "id": e["id"], "motivo": f"estuche en {e['categoria']}"})
        return None

    # ---------------- CR6AL ----------------

    def _esperando(self, vista):
        """Estuches visibles por variedad (los que podrian encajarse si hubiera caja)."""
        n = {}
        for fila in vista["canales"]:
            for e in fila:
                if e["categoria"] == "variedad":
                    n[e["variedad"]] = n.get(e["variedad"], 0) + 1
        return n

    def siguiente_cr6al(self, vista):
        """Proxima accion del CR6AL. Prioridades (recomendacion):

        1. Armar caja en una bahia vacia si hay carton (sin caja, esa variedad tapa su canal).
           Primero la variedad con mas estuches esperando.
        2. Encajar, empezando por el canal con la fila mas larga (para que no se llene y empiece a
           perder estuches): si la politica tiene cr6al_fila = n, primero una fila entera de n
           estuches iguales de un canal; si no hay, hasta cr6al_toma_por_ciclo estuches sueltos.
        3. Desviar al rechazo un estuche en duda o desconocido (si la politica es desviar),
           antes si su canal esta por llenarse.
        4. Esperar.
        """
        if vista["parada"]:
            return self._poner("cr6al", "esperando", Accion("esperar"))
        esperando = self._esperando(vista)

        # 1. Armar
        if vista["carton"] > 0:
            vacias = [(n, b) for n, b in vista["bahias"].items() if b["estado"] == "vacia"]
            if vacias:
                n, _ = max(vacias, key=lambda nb: esperando.get(nb[1]["variedad"], 0))
                return self._poner("cr6al", "armando", Accion("armar", {"bahia": n}))

        # 3a. Desviar urgente: un rechazo ocupa lugar en un canal que esta por llenarse
        urgente = self._rechazo_a_desviar(vista, solo_urgente=True)
        if urgente:
            return urgente

        # 2. Encajar
        lugar = {n: b["capacidad"] - b["cuenta"] - b["reservados"]
                 for n, b in vista["bahias"].items() if b["estado"] == "lista"}
        por_variedad = {b["variedad"]: n for n, b in vista["bahias"].items() if b["estado"] == "lista"}
        canales = sorted(range(len(vista["canales"])), key=lambda c: -vista["cola"][c])
        # 2a. Fila entera: los primeros n estuches de un canal, misma variedad, y la caja con la fila libre
        n = self.politica.get("cr6al_fila", 0)
        for c in canales if n else []:
            fila = vista["canales"][c][:n]
            if len(fila) < n or any(e["categoria"] != "variedad" or e["variedad"] != fila[0]["variedad"] for e in fila):
                continue
            bahia = por_variedad.get(fila[0]["variedad"])
            if bahia and lugar[bahia] >= n:
                b = vista["bahias"][bahia]
                if (b["cuenta"] + b["reservados"]) % n == 0:
                    return self._poner("cr6al", "encajando",
                                       Accion("encajar_fila", {"canal": c, "ids": [e["id"] for e in fila], "bahia": bahia}))
        # 2b. Un rechazo que corta una fila se saca primero (si la politica es desviar)
        for c in canales if n else []:
            fila = vista["canales"][c][:n]
            for e in fila:
                if e["categoria"] in CATEGORIAS_RECHAZO and self.politica[e["categoria"]] == "desviar":
                    return self._poner("cr6al", "desviando", Accion("desviar", {"canal": c, "id": e["id"]}))
        # 2c. De a un estuche (o varios con copas independientes). Con herramienta de fila, solo si
        #     la fila no se puede completar (variedades mezcladas en el canal) o el canal se esta llenando
        tomas = []
        for c in canales:
            fila = vista["canales"][c][:n]
            mezclada = n and len({e["variedad"] for e in fila}) > 1
            if n and not mezclada and vista["cola"][c] < vista["cola_max"] - 2:
                continue   # conviene esperar a que se junte la fila
            for e in vista["canales"][c]:
                if len(tomas) >= self.politica["cr6al_toma_por_ciclo"]:
                    break
                bahia = por_variedad.get(e["variedad"]) if e["categoria"] == "variedad" else None
                if bahia and lugar[bahia] > 0:
                    tomas.append((c, e["id"], bahia))
                    lugar[bahia] -= 1
        if tomas:
            return self._poner("cr6al", "encajando", Accion("encajar", {"tomas": tomas}))

        # 3b. Desviar sin apuro
        r = self._rechazo_a_desviar(vista, solo_urgente=False)
        if r:
            return r
        return self._poner("cr6al", "esperando", Accion("esperar"))

    def _rechazo_a_desviar(self, vista, solo_urgente):
        for c, fila in enumerate(vista["canales"]):
            if solo_urgente and vista["cola"][c] < vista["cola_max"] - 1:
                continue
            for e in fila:
                if e["categoria"] in CATEGORIAS_RECHAZO and self.politica[e["categoria"]] == "desviar":
                    return self._poner("cr6al", "desviando", Accion("desviar", {"canal": c, "id": e["id"]}))
        return None

    # ---------------- CR20A ----------------

    def siguiente_cr20a(self, vista):
        """Estiba la caja del tope si su tarima la recibe; con herramienta doble, dos si estan listas."""
        mb = vista["minibanda"]
        if not mb or not mb[0]["lista"]:
            return self._poner("cr20a", "reposo", Accion("esperar"))

        def recibe(caja):
            t = next(t for t in vista["tarimas"].values() if t["variedad"] == caja["variedad"])
            return not t["en_cambio"] and t["cajas"] < t["capacidad"]

        if not recibe(mb[0]):
            return self._poner("cr20a", "esperando_tarima", Accion("esperar"))
        n = 1
        if vista["herramienta_doble"] and len(mb) > 1 and mb[1]["lista"] and recibe(mb[1]):
            # si las dos van a la misma tarima, tiene que haber lugar para las dos
            t = next(t for t in vista["tarimas"].values() if t["variedad"] == mb[0]["variedad"])
            if mb[1]["variedad"] != mb[0]["variedad"] or t["cajas"] + 2 <= t["capacidad"]:
                n = 2
        return self._poner("cr20a", "estibando", Accion("estibar", {"cajas": n}))

    def _poner(self, robot, estado, accion):
        self.estado[robot] = estado
        return accion
