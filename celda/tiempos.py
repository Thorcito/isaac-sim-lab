"""Tiempos de movimiento de los dos robots, con la cinematica real del URDF.

Que hace:   resuelve la cinematica inversa (celda/cinematica.py) de cada punto de trabajo y
            estima cuanto tarda cada movimiento:
            - traslado entre dos puntos altos: perfil trapezoidal en cada joint (velocidad y
              aceleracion de _supuestos.robots_movimiento), todos sincronizados; manda el joint
              mas lento. Ademas no puede ser mas rapido que la velocidad maxima del TCP en linea recta.
            - bajada y subida vertical (aproximacion): trapezoide lineal (movimiento_lineal).
            - vacio: toma y soltura (vacio).
            Con eso arma el ciclo de cada operacion: tomar caja plana / abrir / dejar en bahia,
            tomar estuche de cada canal, encajar en cada posicion, desviar al rechazo, tomar en el
            punto fijo y dejar en cada posicion de cada tarima.
Como usar:  from celda import tiempos
            T = tiempos.Tiempos(D, S, robots)     # robots: {"cr20a": datos.robot(...), "cr6al": ...}
            T.resumen()                           # tabla de movimientos tipo
Sin Isaac Sim: solo Python y numpy. Pruebas: pruebas/test_tiempos.py.

Puntos "altos": cada punto de trabajo tiene uno arriba, a aproximacion_z, desde donde la
herramienta baja en vertical. Los traslados van siempre de punto alto a punto alto.
Joint 6: la ventosa es simetrica a media vuelta (estuche y caja son rectangulos), asi que el
giro del joint 6 se cuenta hasta 90 grados como maximo.
"""
import math

import numpy as np

from celda import cinematica, geometria, recetas


def trapecio(d, v, a):
    """Tiempo para recorrer d con velocidad maxima v y aceleracion a, partiendo y llegando quieto."""
    d = abs(d)
    if d < 1e-9:
        return 0.0
    if d >= v * v / a:            # llega a velocidad maxima: acelera, crucero, frena
        return d / v + v / a
    return 2.0 * math.sqrt(d / a)  # no llega: triangulo


def _envolver(d, medio):
    """Lleva un angulo a (-medio, medio]: el joint toma el camino corto (o el equivalente simetrico)."""
    return (d + medio) % (2 * medio) - medio


class Tiempos:
    """Tabla de tiempos de los dos robots para una celda (D, S) y sus cadenas cinematicas."""

    def __init__(self, D, S, robots):
        self.D, self.S, self.R = D, S, robots
        self.aprox = S["aproximacion_z"]
        self.q = {"cr20a": {}, "cr6al": {}}       # nombre del punto alto -> angulos
        self.p = {"cr20a": {}, "cr6al": {}}       # nombre del punto alto -> (x, y, z) del TCP
        self.bajada = {"cr20a": {}, "cr6al": {}}  # nombre del punto alto -> m que baja la herramienta
        self.sin_solucion = []
        self._puntos_cr6al()
        self._puntos_cr20a()

    # ---------- puntos ----------

    def _agregar(self, clave, nombre, punto, bajada, q_inicial):
        """Resuelve el punto alto (punto + bajada en z) y lo guarda. Devuelve los angulos."""
        rob = self.R[clave]
        alto = (punto[0], punto[1], punto[2] + bajada)
        r = cinematica.resolver_abajo(rob["cadena"], rob["T_base"], alto, rob["largo"], rob["eje_brida"], q_inicial)
        if not r["ok"]:
            self.sin_solucion.append(f"{clave} {nombre}: falta {r['err_pos'] * 100:.1f} cm")
        self.q[clave][nombre], self.p[clave][nombre], self.bajada[clave][nombre] = r["q"], alto, bajada
        return r["q"]

    def _puntos_cr6al(self):
        D, S, a = self.D, self.S, self.aprox
        e, b, cj = S["estuche"], S["banda"], S["caja"]
        # Reposo: sobre el centro de las bahias. De ahi arrancan todas las soluciones (misma postura)
        bx = np.mean([c[0] for c in S["bahias"]["centros"].values()])
        by = np.mean([c[1] for c in S["bahias"]["centros"].values()])
        tope_caja = S["bahias"]["alto"] + cj["alto"]
        q0 = self._agregar("cr6al", "reposo", (bx, by, tope_caja), a, None)
        # Canales: estuche detenido contra el final de la banda
        W = geometria.ancho_canales(D, S)
        x = b["x_fin"] - e["largo"] / 2
        for k in range(D["canales"]):
            y = b["y_centro"] - W / 2 + b["ancho_canal"] / 2 + k * (b["ancho_canal"] + b["divisor"])
            self._agregar("cr6al", f"canal{k + 1}", (x, y, b["alto"] + e["alto"]), a, q0)
        mg = S["magazine"]
        self._agregar("cr6al", "magazine", (*mg["centro"], mg["alto"]), a, q0)
        rz = S["rechazo"]
        self._agregar("cr6al", "rechazo", (*rz["centro"], rz["alto"]), a, q0)
        # Bahias: entrada (sobre el centro de la caja) y cada posicion de estuche
        for n, (cx, cy) in S["bahias"]["centros"].items():
            self._agregar("cr6al", f"{n}", (cx, cy, tope_caja), a, q0)
            for p in recetas.puntos_encaje(D, S, n):
                x, y, z = p["punto"]
                # el punto alto queda sobre la caja: la herramienta entra en vertical hasta el estuche
                self._agregar("cr6al", f"{n}/{p['i']}", (x, y, z), tope_caja + a - z, q0)

    def _puntos_cr20a(self):
        D, S, a = self.D, self.S, self.aprox
        tx, ty = geometria.punto_toma(D, S)
        zt = S["minibanda"]["alto"] + S["caja"]["alto"]
        q0 = self._agregar("cr20a", "toma", (tx, ty, zt), a, None)
        for p in recetas.puntos_estiba(D, S):
            self._agregar("cr20a", self.nombre_estiba(p["tarima"], p["camada"], p["orden"]), p["punto"], a, q0)

    @staticmethod
    def nombre_estiba(tarima, camada, orden):
        return f"{tarima}/{camada}/{orden}"

    # ---------- movimientos ----------

    def mover(self, clave, a, b):
        """Traslado de punto alto a punto alto (s)."""
        if a == b:
            return 0.0
        m = self.S["robots_movimiento"]
        r, f = m[clave], m["factor_velocidad"]
        dq = np.asarray(self.q[clave][b]) - np.asarray(self.q[clave][a])
        dq = [_envolver(d, math.pi) for d in dq[:5]] + [_envolver(dq[5], math.pi / 2)]
        t_joint = max(trapecio(d, math.radians(v) * f, math.radians(ac) * f)
                      for d, v, ac in zip(dq, r["vel_joint_grados_s"], r["acel_joint_grados_s2"]))
        dist = float(np.linalg.norm(np.subtract(self.p[clave][b], self.p[clave][a])))
        t_tcp = trapecio(dist, r["vel_tcp_max_m_s"] * f, r["acel_tcp_m_s2"] * f)
        return max(t_joint, t_tcp) + self.S["movimiento_lineal"]["asentamiento_s"]

    def vertical(self, d):
        """Bajada o subida en linea recta de d metros (s)."""
        L = self.S["movimiento_lineal"]
        return trapecio(d, L["vel_m_s"], L["acel_m_s2"]) + L["asentamiento_s"]

    def tomar(self, clave, punto):
        """Bajar desde el punto alto, hacer vacio y subir."""
        d = self.bajada[clave][punto]
        return 2 * self.vertical(d) + self.S["vacio"]["toma_s"]

    def dejar(self, clave, punto):
        """Bajar desde el punto alto, soltar y subir."""
        d = self.bajada[clave][punto]
        return 2 * self.vertical(d) + self.S["vacio"]["soltura_s"]

    # ---------- ciclos (devuelven segundos y donde queda el robot) ----------

    def ciclo_estuche(self, desde, canal, bahia, i):
        """CR6AL: desde un punto alto, toma un estuche del canal y lo deja en la posicion i de la bahia."""
        destino = f"{bahia}/{i}"
        t = (self.mover("cr6al", desde, f"canal{canal}") + self.tomar("cr6al", f"canal{canal}") +
             self.mover("cr6al", f"canal{canal}", destino) + self.dejar("cr6al", destino))
        return t, destino

    def ciclo_rechazo(self, desde, canal):
        """CR6AL: toma un estuche del canal y lo deja en el cajon de rechazo."""
        t = (self.mover("cr6al", desde, f"canal{canal}") + self.tomar("cr6al", f"canal{canal}") +
             self.mover("cr6al", f"canal{canal}", "rechazo") + self.dejar("cr6al", "rechazo"))
        return t, "rechazo"

    def ciclo_armado(self, desde, bahia):
        """CR6AL: toma una caja plana del magazine, la abre y la deja armada en la bahia."""
        t = (self.mover("cr6al", desde, "magazine") + self.tomar("cr6al", "magazine") +
             self.mover("cr6al", "magazine", bahia) + self.S["armado_caja"]["abrir_s"] + self.dejar("cr6al", bahia))
        return t, bahia

    def ciclo_estiba(self, desde, destinos):
        """CR20A: toma en el punto fijo y deja en cada destino (1 caja, o 2 con herramienta doble).

        destinos: lista de nombres de estiba (nombre_estiba). Con dos, la herramienta toma las dos
        cajas juntas y las suelta de a una.
        """
        t = self.mover("cr20a", desde, "toma") + self.tomar("cr20a", "toma")
        actual = "toma"
        for d in destinos:
            t += self.mover("cr20a", actual, d) + self.dejar("cr20a", d)
            actual = d
        return t, actual

    # ---------- resumen ----------

    def resumen(self):
        """Movimientos tipo con su tiempo minimo, medio y maximo (s). Lista de dicts."""
        S = self.S
        filas = []

        def fila(robot, nombre, valores):
            filas.append({"robot": robot, "movimiento": nombre, "min": min(valores),
                          "medio": sum(valores) / len(valores), "max": max(valores), "n": len(valores)})

        bahias = list(S["bahias"]["centros"])
        canales = range(1, self.D["canales"] + 1)
        fila("CR6AL", "Tomar caja plana del magazine (desde la bahia, con vacio)",
             [self.mover("cr6al", b, "magazine") + self.tomar("cr6al", "magazine") for b in bahias])
        fila("CR6AL", "Abrir la caja y dejarla en la bahia", [self.mover("cr6al", "magazine", b) +
             S["armado_caja"]["abrir_s"] + self.dejar("cr6al", b) for b in bahias])
        fila("CR6AL", "Armado completo (magazine -> bahia)", [self.ciclo_armado(b, b)[0] for b in bahias])
        for c in canales:
            fila("CR6AL", f"Tomar estuche del canal {c} (desde las bahias, con vacio)",
                 [self.mover("cr6al", f"{b}/{i}", f"canal{c}") + self.tomar("cr6al", f"canal{c}")
                  for b in bahias for i in range(len(recetas.patron_caja(S)))])
        for b in bahias:
            fila("CR6AL", f"Encajar en {b} (desde la banda, por posicion)",
                 [self.mover("cr6al", f"canal{c}", f"{b}/{i}") + self.dejar("cr6al", f"{b}/{i}")
                  for c in canales for i in range(len(recetas.patron_caja(S)))])
        fila("CR6AL", "Ciclo completo de un estuche (banda -> caja -> banda)",
             [self.ciclo_estuche(f"{b}/{i}", c, b, i)[0] for b in bahias for c in canales
              for i in range(len(recetas.patron_caja(S)))])
        fila("CR6AL", "Desviar un estuche al rechazo", [self.ciclo_rechazo(f"{b}/0", c)[0] for b in bahias for c in canales])
        estiba = [n for n in self.q["cr20a"] if n != "toma"]
        fila("CR20A", "Tomar caja en el punto fijo (desde la tarima, con vacio)",
             [self.mover("cr20a", n, "toma") + self.tomar("cr20a", "toma") for n in estiba])
        for tarima in S["tarimas"]:
            fila("CR20A", f"Dejar en la tarima {tarima} (todas las posiciones)",
                 [self.mover("cr20a", "toma", n) + self.dejar("cr20a", n) for n in estiba if n.startswith(tarima + "/")])
        fila("CR20A", "Ciclo completo de una caja", [self.ciclo_estiba(n, [n])[0] for n in estiba])
        return filas

    def tabla_estiba(self):
        """Tiempo de 'dejar' de cada posicion: {tarima: {camada: [s por orden]}} (para graficos)."""
        out = {}
        for n in self.q["cr20a"]:
            if n == "toma":
                continue
            tarima, camada, orden = n.split("/")
            out.setdefault(tarima, {}).setdefault(int(camada), []).append(
                self.mover("cr20a", "toma", n) + self.dejar("cr20a", n))
        return out
