"""Modelo de ritmo: simulacion de eventos discretos de una estacion.

Que hace:   simula la celda en el tiempo, sin fisica: llegan estuches por los 5 canales,
            la camara los clasifica (con dudas y variedades fuera de receta segun el
            escenario), el orquestador (celda/orquestador.py) decide que hace cada robot, y
            cada accion dura lo que dice celda/tiempos.py. Incluye magazine de cartones,
            bahias, salida a la mini-banda, tarimas que se llenan y el operador.
            Motor escrito a mano (una cola de eventos con heapq): corre en la PC y tambien en
            la maquina de Isaac sin instalar nada.
Como usar:  from celda import modelo_ritmo
            r = modelo_ritmo.simular(D, S, T, escenario, semilla=1)     # T = tiempos.Tiempos(...)
            tabla = modelo_ritmo.correr_escenarios(D, S, T, modelo_ritmo.escenarios(S))
Salidas:    estuches/min encajados, ocupacion de cada robot, colas, estuches perdidos (la fila
            del canal estaba llena), desviados, dejados pasar, retenidos por parada, mal
            encajados, tiempo sin carton y el cuello de botella.
Sin Isaac Sim: solo Python. Pruebas: pruebas/test_modelo_ritmo.py.

Simplificaciones: el estuche llega directo a la fila de su canal (el viaje por la banda solo
retrasa todo igual); el CR6AL lo toma desde el punto del tope de su canal aunque este 1 a 3
lugares mas atras; la caja vuelve a tener lugar en la mini-banda apenas el CR20A la toma.
"""
import heapq
import random

from celda import llegadas, orquestador, recetas


CONFIGURACIONES = {
    # Como esta planteada la celda: una copa, variedades mezcladas en cualquier canal
    "actual": {"config": "Actual: 1 copa, variedades mezcladas", "canales": "mezclado", "politica": {}},
    # Propuesta: la linea manda una variedad por canal y la herramienta toma una fila de 3 estuches
    "propuesta": {"config": "Propuesta: fila de 3, una variedad por canal", "canales": "por_canal",
                  "politica": {"cr6al_fila": 3}},
}


def escenarios(S, configuracion="actual"):
    """Escenarios del ejercicio para una configuracion. Cada uno se corre a 15 y a 20 estuches/min.

    La quinta variedad 'X' (fuera de receta) llega en el 5 % de los estuches.
    """
    cfg = CONFIGURACIONES[configuracion]
    pareja = {v: 1.0 for v in S["variedades"]}
    desbalanceada = dict(zip(S["variedades"], (0.55, 0.25, 0.15, 0.05)))
    con_x = dict(pareja, X=len(pareja) * 0.05 / 0.95)
    base = {"config": cfg["config"], "canales": cfg["canales"], "mezcla": pareja, "p_duda": 0.0, "p_error": 0.0,
            "carton_inicial": None, "politica": dict(cfg["politica"]), "herramienta_doble": False}
    lista = [
        dict(base, nombre="Mezcla pareja"),
        dict(base, nombre="Mezcla desbalanceada (55/25/15/5 %)", mezcla=desbalanceada),
        dict(base, nombre="Falta de carton (10 cartones, sin aviso previo)", carton_inicial=10,
             politica=dict(cfg["politica"], aviso_carton_bajo=0)),
        dict(base, nombre="Variedad fuera de receta (5 %)", mezcla=con_x),
        dict(base, nombre="5 % de dudas de la camara", p_duda=0.05),
        dict(base, nombre="Herramienta doble en el CR20A", herramienta_doble=True),
    ]
    if configuracion == "actual":
        lista.append(dict(base, nombre="3 copas que toman de a una", politica={"cr6al_toma_por_ciclo": 3}))
    return lista


class Planta:
    """Estado de la estacion y motor de eventos. Ejecuta las acciones del orquestador."""

    def __init__(self, D, S, T, esc, ritmo_min, semilla):
        self.D, self.S, self.T, self.esc = D, S, T, esc
        self.rnd = random.Random(semilla)
        R = S["ritmo"]
        self.t0, self.t1 = R["calentamiento_s"], R["calentamiento_s"] + R["duracion_s"]

        politica = dict(S["politica_fallas"], **esc["politica"])
        self.toma_max = politica["cr6al_toma_por_ciclo"]
        self.aviso = politica["aviso_carton_bajo"]
        self.o = orquestador.Orquestador(politica)
        self.ev, self.seq, self.t = [], 0, 0.0
        n_canales, A = D["canales"], S["acumulacion_canal"]
        self.colas = [[] for _ in range(n_canales)]
        self.gen = llegadas.Generador(D, S, ritmo_min, esc["mezcla"], esc["canales"], rnd=self.rnd)
        fila = politica.get("cr6al_fila", 0)
        if fila and fila != S["receta_encajado"]["a_lo_largo"]:
            raise ValueError(f"cr6al_fila = {fila}: la herramienta deja una fila entera, tiene que ser igual a a_lo_largo")
        self.cola_max, self.visibles = A["capacidad_estuches"], A["visibles"]
        cap = len(recetas.patron_caja(S))
        self.bahias = {v["bahia"]: {"variedad": k, "estado": "vacia", "cuenta": 0, "reservados": 0, "capacidad": cap}
                       for k, v in S["variedades"].items()}
        self.cap_magazine = S["magazine"]["capacidad_cartones"]
        self.carton = esc["carton_inicial"] if esc["carton_inicial"] is not None else self.cap_magazine
        self.reponiendo = False
        self.minibanda, self.esperan_salir = [], []
        tr = recetas.trabado(D, S)
        self.por_camada = tr["cajas"]
        cap_t = tr["cajas"] * recetas.altura_estiba(D, S)[2]
        self.tarimas = {v["tarima"]: {"variedad": k, "cajas": 0, "capacidad": cap_t, "en_cambio": False}
                        for k, v in S["variedades"].items()}
        self.parada, self.motivo_parada = False, None
        self.libre = {"cr6al": True, "cr20a": True}
        self.pos = {"cr6al": "reposo", "cr20a": "toma"}
        self.id = 0
        self.st = {k: 0 for k in ("llegadas", "encajados", "perdidos", "desviados", "dejados_pasar", "retenidos",
                                  "mal_encajados", "cajas_llenas", "cajas_estibadas", "paradas", "cajas_armadas")}
        self.ocupado = {"cr6al": 0.0, "cr20a": 0.0}
        self.integral = {"cola": 0.0, "sin_carton": 0.0, "bahia_bloqueada": 0.0, "parada": 0.0}
        self.max_cola = [0] * n_canales
        self.max_minibanda = 0
        self.t_ultimo = 0.0

    # ---------- motor ----------

    def _programar(self, dt, tipo, **datos):
        self.seq += 1
        heapq.heappush(self.ev, (self.t + dt, self.seq, tipo, datos))

    def _en_ventana(self):
        return self.t0 <= self.t < self.t1

    def _contar(self, clave, n=1):
        if self._en_ventana():
            self.st[clave] += n

    def _avanzar(self, t):
        """Acumula las integrales en el tiempo (dentro de la ventana medida) hasta t."""
        a, b = max(self.t_ultimo, self.t0), min(t, self.t1)
        if b > a:
            dt = b - a
            self.integral["cola"] += dt * sum(len(c) for c in self.colas)
            self.integral["sin_carton"] += dt * (self.carton == 0)
            self.integral["bahia_bloqueada"] += dt * bool(self.esperan_salir)
            self.integral["parada"] += dt * self.parada
        self.t_ultimo = t
        self.t = t

    def _ocupar(self, robot, dur):
        a, b = max(self.t, self.t0), min(self.t + dur, self.t1)
        if b > a:
            self.ocupado[robot] += b - a
        self.libre[robot] = False

    def correr(self):
        self._programar(0.0, "llegada")
        while self.ev:
            t, _, tipo, datos = heapq.heappop(self.ev)
            if t > self.t1:
                break
            self._avanzar(t)
            getattr(self, "_e_" + tipo)(**datos)
            self._despachar()
        self._avanzar(self.t1)
        return self._resultado()

    # ---------- eventos ----------

    def _e_llegada(self):
        self._programar(self.gen.intervalo_siguiente(), "llegada")
        self._contar("llegadas")
        if self.parada:
            self._contar("retenidos")   # la banda esta parada: la linea de arriba los retiene
            return
        v, c = self.gen.variedad_y_canal()
        self.id += 1
        e = {"id": self.id, "real": v}
        if v not in self.S["variedades"]:
            e.update(categoria="desconocida", variedad=None)
            self.o.evento("variedad_desconocida", id=self.id)
        elif self.rnd.random() < self.esc["p_duda"]:
            e.update(categoria="duda", variedad=None)
            self.o.evento("estuche_dudoso", id=self.id)
        elif self.rnd.random() < self.esc["p_error"]:
            e.update(categoria="variedad", variedad=self.rnd.choice([k for k in self.S["variedades"] if k != v]))
        else:
            e.update(categoria="variedad", variedad=v)
        if len(self.colas[c]) >= self.cola_max:
            self._contar("perdidos")    # la fila del canal llego hasta atras: la banda lo empuja fuera
            return
        self.colas[c].append(e)
        self.max_cola[c] = max(self.max_cola[c], len(self.colas[c]))

    def _e_fin_cr6al(self, accion, datos):
        self.libre["cr6al"] = True
        if accion == "armar":
            b = self.bahias[datos["bahia"]]
            b.update(estado="lista", cuenta=0, reservados=0)
            self._contar("cajas_armadas")
        elif accion in ("encajar", "encajar_fila"):
            for e, bahia in datos["piezas"]:
                b = self.bahias[bahia]
                b["cuenta"] += 1
                b["reservados"] -= 1
                self._contar("encajados")
                if e["real"] != b["variedad"]:
                    self._contar("mal_encajados")
                self.o.evento("encajado")
                if b["cuenta"] == b["capacidad"]:
                    b["estado"] = "saliendo"
                    self._contar("cajas_llenas")
                    self.o.evento("bahia_llena", bahia=bahia)
                    self._programar(self.S["transferencia"]["salida_bahia_s"], "salida", bahia=bahia)
        elif accion == "desviar":
            self._contar("desviados")
            self.o.evento("rechazo")

    def _e_salida(self, bahia):
        self.esperan_salir.append(bahia)
        self._sacar_cajas()

    def _sacar_cajas(self):
        """Pasa las cajas llenas de las bahias a la mini-banda mientras haya lugar."""
        tr = self.S["transferencia"]
        while self.esperan_salir and len(self.minibanda) < tr["minibanda_capacidad_cajas"]:
            bahia = self.esperan_salir.pop(0)
            caja = {"variedad": self.bahias[bahia]["variedad"], "lista": False}
            self.minibanda.append(caja)
            self.max_minibanda = max(self.max_minibanda, len(self.minibanda))
            self.bahias[bahia].update(estado="vacia", cuenta=0, reservados=0)
            self._programar(self.D["minibanda_largo"] / tr["minibanda_vel_m_s"], "llega_tope", caja=caja)
            self.o.evento("caja_saliendo", bahia=bahia)
        if self.esperan_salir:
            self.o.evento("minibanda_llena")

    def _e_llega_tope(self, caja):
        caja["lista"] = True

    def _e_fin_cr20a(self, llenas):
        self.libre["cr20a"] = True
        for nombre in llenas:
            self.o.evento("tarima_llena", tarima=nombre)
            self.tarimas[nombre]["en_cambio"] = True
            self._programar(self.S["operador"]["cambiar_tarima_s"], "tarima_cambiada", tarima=nombre)

    def _e_tarima_cambiada(self, tarima):
        self.tarimas[tarima].update(cajas=0, en_cambio=False)
        self.o.evento("tarima_cambiada", tarima=tarima)

    def _e_carton_repuesto(self):
        self.carton, self.reponiendo = self.cap_magazine, False
        self.o.evento("carton_repuesto")

    def _e_parada_despejada(self, canal, id):
        if canal is not None:
            self.colas[canal] = [e for e in self.colas[canal] if e["id"] != id]
        self.parada = False
        self.o.evento("parada_despejada")

    # ---------- despacho de acciones ----------

    def vista(self):
        return {
            "canales": [c[:self.visibles] for c in self.colas],
            "cola": [len(c) for c in self.colas], "cola_max": self.cola_max,
            "bahias": self.bahias, "carton": self.carton,
            "minibanda": self.minibanda, "tarimas": self.tarimas,
            "herramienta_doble": self.esc["herramienta_doble"], "parada": self.parada,
        }

    def _despachar(self):
        while True:
            a = self.o.accion_banda(self.vista())
            if a is None:
                break
            if a.tipo == "dejar_pasar":
                self.colas[a.datos["canal"]] = [e for e in self.colas[a.datos["canal"]] if e["id"] != a.datos["id"]]
                self._contar("dejados_pasar")
                self.o.evento("rechazo")
            elif a.tipo == "detener":
                self.parada = True
                self._contar("paradas")
                self.o.evento("parada", motivo=a.datos["motivo"])
                self._programar(self.S["operador"]["despejar_parada_s"], "parada_despejada",
                                canal=a.datos["canal"], id=a.datos["id"])
                break
        if self.libre["cr6al"]:
            self._iniciar_cr6al(self.o.siguiente_cr6al(self.vista()))
        if self.libre["cr20a"]:
            self._iniciar_cr20a(self.o.siguiente_cr20a(self.vista()))

    def _sacar(self, canal, id):
        cola = self.colas[canal]
        e = next(e for e in cola if e["id"] == id)
        cola.remove(e)
        return e

    def _iniciar_cr6al(self, a):
        T, pos = self.T, self.pos["cr6al"]
        if a.tipo == "esperar":
            return
        if a.tipo == "armar":
            self.carton -= 1
            self.bahias[a.datos["bahia"]]["estado"] = "armando"
            if self.carton == 0:
                self.o.evento("sin_carton")
            elif self.carton == self.aviso:
                self.o.evento("carton_bajo")
            if (self.carton == 0 or self.carton == self.aviso) and not self.reponiendo:
                self.reponiendo = True
                self._programar(self.S["operador"]["reponer_carton_s"], "carton_repuesto")
            dur, fin = T.ciclo_armado(pos, a.datos["bahia"])
            datos = a.datos
        elif a.tipo == "encajar":
            piezas, dur, actual = [], 0.0, pos
            for canal, id, bahia in a.datos["tomas"]:       # primero toma todos
                piezas.append((self._sacar(canal, id), bahia))
                p = f"canal{canal + 1}"
                dur += T.mover("cr6al", actual, p) + T.tomar("cr6al", p)
                actual = p
            for _, bahia in piezas:                          # despues los deja de a uno
                b = self.bahias[bahia]
                destino = f"{bahia}/{b['cuenta'] + b['reservados']}"
                b["reservados"] += 1
                dur += T.mover("cr6al", actual, destino) + T.dejar("cr6al", destino)
                actual = destino
            fin, datos = actual, {"piezas": piezas}
        elif a.tipo == "encajar_fila":
            # una sola bajada en el canal toma la fila, una sola bajada en la caja la deja (posicion del medio)
            canal, bahia = a.datos["canal"], a.datos["bahia"]
            piezas = [(self._sacar(canal, id), bahia) for id in a.datos["ids"]]
            b = self.bahias[bahia]
            destino = f"{bahia}/{b['cuenta'] + b['reservados'] + len(piezas) // 2}"
            b["reservados"] += len(piezas)
            p = f"canal{canal + 1}"
            dur = T.mover("cr6al", pos, p) + T.tomar("cr6al", p) + T.mover("cr6al", p, destino) + T.dejar("cr6al", destino)
            fin, datos = destino, {"piezas": piezas}
        elif a.tipo == "desviar":
            self._sacar(a.datos["canal"], a.datos["id"])
            dur, fin = T.ciclo_rechazo(pos, a.datos["canal"] + 1)
            datos = a.datos
        else:
            raise ValueError(f"accion desconocida del CR6AL: {a.tipo}")
        self.pos["cr6al"] = fin
        self._ocupar("cr6al", dur)
        self._programar(dur, "fin_cr6al", accion=a.tipo, datos=datos)

    def _iniciar_cr20a(self, a):
        if a.tipo == "esperar":
            return
        destinos, llenas = [], []
        for _ in range(a.datos["cajas"]):
            caja = self.minibanda.pop(0)
            nombre = next(n for n, t in self.tarimas.items() if t["variedad"] == caja["variedad"])
            t = self.tarimas[nombre]
            k = t["cajas"]
            destinos.append(self.T.nombre_estiba(nombre, k // self.por_camada + 1, k % self.por_camada + 1))
            t["cajas"] += 1
            if t["cajas"] == t["capacidad"]:
                llenas.append(nombre)
            self._contar("cajas_estibadas")
        dur, fin = self.T.ciclo_estiba(self.pos["cr20a"], destinos)
        self.pos["cr20a"] = fin
        self._ocupar("cr20a", dur)
        self._programar(dur, "fin_cr20a", llenas=llenas)
        self._sacar_cajas()   # al tomar la caja del tope, la mini-banda tiene lugar

    # ---------- resultado ----------

    def _resultado(self):
        dur = self.t1 - self.t0
        m = dur / 60.0
        st = dict(self.st)
        r = {
            "estuches_min": st["encajados"] / m,
            "llegadas_min": st["llegadas"] / m,
            "ocupacion_cr6al": self.ocupado["cr6al"] / dur,
            "ocupacion_cr20a": self.ocupado["cr20a"] / dur,
            "cola_media": self.integral["cola"] / dur,
            "cola_max_canal": max(self.max_cola),
            "minibanda_max": self.max_minibanda,
            "sin_carton_min": self.integral["sin_carton"] / 60.0,
            "bahia_bloqueada_min": self.integral["bahia_bloqueada"] / 60.0,
            "parada_min": self.integral["parada"] / 60.0,
            **{k: st[k] for k in st},
        }
        r["cuello"] = cuello_de_botella(r)
        return r


def cuello_de_botella(r):
    """Que frena la celda, segun los resultados de una corrida."""
    no_entran = r["perdidos"] + r["retenidos"]
    if r["llegadas"] == 0 or no_entran <= 0.01 * r["llegadas"]:
        mas = "CR6AL" if r["ocupacion_cr6al"] >= r["ocupacion_cr20a"] else "CR20A"
        return f"ninguno (sigue el ritmo; el mas cargado es el {mas})"
    if r["parada_min"] > 1.0:
        return "paradas por rechazos"
    if r["ocupacion_cr6al"] >= 0.97:
        # saturado: aunque falte carton, lo que limita es el robot (las otras variedades siguen)
        return "CR6AL" + (" (y falta de carton)" if r["sin_carton_min"] > 1.0 else "")
    if r["sin_carton_min"] > 1.0:
        return "falta de carton"
    if r["bahia_bloqueada_min"] > 1.0 and r["ocupacion_cr20a"] > 0.9:
        return "CR20A (las cajas no salen)"
    return "CR6AL"


def simular(D, S, T, esc, ritmo_min, semilla=1):
    """Una corrida: devuelve el dict de resultados."""
    return Planta(D, S, T, esc, ritmo_min, semilla).correr()


def correr_escenarios(D, S, T, lista, ritmos=None):
    """Corre cada escenario a cada ritmo con varias semillas y promedia.

    Devuelve lista de dicts: escenario, ritmo, y la media de cada resultado (cuello: el mas repetido).
    """
    ritmos = ritmos or D["ritmo_estuches_min"]
    out = []
    for esc in lista:
        for ritmo in ritmos:
            corridas = [simular(D, S, T, esc, ritmo, s + 1) for s in range(S["ritmo"]["semillas"])]
            fila = {"config": esc["config"], "escenario": esc["nombre"], "ritmo": ritmo}
            for k, v in corridas[0].items():
                if k == "cuello":
                    cuellos = [c["cuello"] for c in corridas]
                    fila[k] = max(set(cuellos), key=cuellos.count)
                else:
                    fila[k] = sum(c[k] for c in corridas) / len(corridas)
            out.append(fila)
    return out
