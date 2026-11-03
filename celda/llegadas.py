"""Generador de llegadas de estuches: cuando llega el proximo, de que variedad y por que canal.

Lo usan el modelo de ritmo (celda/modelo_ritmo.py) y el generador de estuches de Isaac
(fase3/banda_estuches.py), asi los dos ven la misma secuencia con la misma semilla.

    from celda import llegadas
    g = llegadas.Generador(D, S, ritmo_min=20, mezcla={"A": 1, "B": 1, "C": 1, "D": 1},
                           canales="mezclado", semilla=1)
    dt, variedad, canal = g.siguiente()     # canal 0..4

canales: "mezclado" (cualquier canal) o "por_canal" (uno por variedad de la receta; los
canales que sobran van a las variedades mas frecuentes). Una variedad que no esta en la
receta llega por cualquier canal.
Sin Isaac Sim: solo Python.
"""
import random


def asignar_canales(S, mezcla, modo, n):
    """{variedad: [canales]} segun el modo."""
    todos = list(range(n))
    if modo == "mezclado":
        return {v: todos for v in mezcla}
    if modo != "por_canal":
        raise ValueError(f"canales = {modo!r}: tiene que ser 'mezclado' o 'por_canal'")
    receta = sorted((v for v in mezcla if v in S["variedades"]), key=lambda v: -mezcla[v])
    out = {v: [i] for i, v in enumerate(receta)}
    for i in range(len(receta), n):
        out[receta[(i - len(receta)) % len(receta)]].append(i)
    return {v: out.get(v, todos) for v in mezcla}


class Generador:
    """Llegadas con intervalo medio 60 / ritmo_min s y variacion uniforme de +/- variacion_llegadas."""

    def __init__(self, D, S, ritmo_min, mezcla, canales="mezclado", semilla=1, rnd=None):
        self.rnd = rnd or random.Random(semilla)
        self.intervalo = 60.0 / ritmo_min
        self.var = S["ritmo"]["variacion_llegadas"]
        self.nombres, self.pesos = list(mezcla), list(mezcla.values())
        self.canales_de = asignar_canales(S, mezcla, canales, D["canales"])

    def intervalo_siguiente(self):
        return self.intervalo * self.rnd.uniform(1 - self.var, 1 + self.var)

    def variedad_y_canal(self):
        v = self.rnd.choices(self.nombres, weights=self.pesos)[0]
        return v, self.rnd.choice(self.canales_de[v])

    def siguiente(self):
        """(segundos hasta esta llegada, variedad, canal)."""
        dt = self.intervalo_siguiente()
        return (dt, *self.variedad_y_canal())
