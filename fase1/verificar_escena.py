"""Etapa 1 · Verifica la escena a escala contra celda.json y dibuja los alcances.

Que hace:   mide cada pieza de /World/Celda con medidas() (lo mismo que usa medir())
            y la compara con celda.json. Despues revisa la escena contra los datos
            del ejercicio: piso, zona de estiba, tarimas, tolerancia, mini-banda,
            canales, camara, pasos de personal y que nada se pise. Dibuja con
            debug_draw los circulos de alcance (1,7 m del CR20A y 1,8 m del CR6AL)
            sobre el piso.
Correr:     con la escena de la etapa 1 abierta (o recien armada):
                correr("fase1/verificar_escena.py")
Que ver:    una ventana "Etapa 1: verificacion" con una linea PASA o FALLA por
            control y el resumen arriba; una ventana "Medir" con las piezas clave;
            los dos circulos en el viewport. El reporte tambien queda en
            /isaac-sim/trabajo/notas/etapa1_verificacion.txt.
Lista:      la etapa 1 esta lista cuando todo da PASA.
Borrar los circulos: limpiar_dibujos()

PROBADO EN LA MAQUINA: no (probado en PC con usd-core, sin el dibujo)
"""
import math
import os

# ---------------- PARAMETROS ----------------
PARAMS = {
    "raiz": "/World/Celda",
    "tol": 0.001,                               # 1 mm para comparar medidas
    "color_cr20a": (1.0, 0.55, 0.0, 1.0),
    "color_cr6al": (0.2, 0.6, 1.0, 1.0),
    "z_circulos": 0.01,                         # apenas sobre el piso
    "nota": TRABAJO + "/notas/etapa1_verificacion.txt",
}
# Piezas que no ocupan piso (pintura, marcas o cosas en el aire): no cuentan para choques ni pasos
NO_OCUPAN = ("/Piso", "/Pasos/", "/ZonaEstiba/Linea", "/Alimentacion/PuntoToma", "/Alimentacion/Tope",
             "/Camara/Campo", "/Camara/Cuerpo", "/Camara/Viga", "/Alimentacion/Banda/Canal", "/Alimentacion/Banda/Divisor")
# --------------------------------------------


def _verificar():
    D, S, ruta_datos = leer_celda()
    correr("fase1/piezas.py")
    R, tol = PARAMS["raiz"], PARAMS["tol"]
    lista = piezas(D, S)
    med = medidas(*[R + p["ruta"] for p in lista])

    filas = []

    def control(ok, texto):
        filas.append(("PASA " if ok else "FALLA") + "  " + texto)
        return ok

    def cerca(a, b):
        return all(abs(x - y) <= tol for x, y in zip(a, b))

    def planta(ruta):
        m = med[R + ruta]
        return (m["min"][0], m["min"][1], m["max"][0], m["max"][1])

    def solapa(a, b, holgura=0.0):
        return a[0] < b[2] + holgura - tol and b[0] < a[2] + holgura - tol and a[1] < b[3] + holgura - tol and b[1] < a[3] + holgura - tol

    def separacion(a, b):
        dx = max(b[0] - a[2], a[0] - b[2], 0.0)
        dy = max(b[1] - a[3], a[1] - b[3], 0.0)
        return math.hypot(dx, dy) if dx and dy else max(dx, dy)

    # ---------- A. La escena es igual a celda.json ----------
    faltan = [p["ruta"] for p in lista if med[R + p["ruta"]] is None]
    control(not faltan, f"Existen las {len(lista)} piezas" + (f" (faltan: {', '.join(faltan)})" if faltan else ""))
    if faltan:
        return _reporte(filas, ruta_datos, ["Corre primero correr(\"fase1/armar_escena.py\")."])
    distintas = [p["ruta"] for p in lista if not (cerca(med[R + p["ruta"]]["centro"], p["centro"]) and cerca(med[R + p["ruta"]]["tam"], p["tam"]))]
    control(not distintas, "Cada pieza medida coincide con celda.json (centro y tamano, +-1 mm)" +
            (f"; distintas: {', '.join(distintas)}" if distintas else ""))

    # ---------- B. La escena cumple los datos del ejercicio ----------
    Lx, Wy = D["piso"]
    t = med[R + "/Piso"]["tam"]
    control(abs(t[0] - Lx) <= tol and abs(t[1] - Wy) <= tol, f"Piso {t[0]:.3f} x {t[1]:.3f} m (dato {Lx} x {Wy})")

    zona = medidas(R + "/ZonaEstiba/LineaN", R + "/ZonaEstiba/LineaS", R + "/ZonaEstiba/LineaE", R + "/ZonaEstiba/LineaO")
    zr = (min(m["min"][0] for m in zona.values()), min(m["min"][1] for m in zona.values()),
          max(m["max"][0] for m in zona.values()), max(m["max"][1] for m in zona.values()))
    L = D["zona_estiba_lado"]
    control(abs(zr[2] - zr[0] - L) <= tol and abs(zr[3] - zr[1] - L) <= tol,
            f"Zona de estiba {zr[2] - zr[0]:.3f} x {zr[3] - zr[1]:.3f} m (dato {L} x {L})")

    tar = {n: planta(f"/ZonaEstiba/Tarimas/{n}") for n in S["tarimas"]}
    a, b = sorted(D["tarima"])
    for n, r in tar.items():
        dims = sorted([r[2] - r[0], r[3] - r[1]])
        control(abs(dims[0] - a) <= tol and abs(dims[1] - b) <= tol, f"Tarima {n}: {r[2] - r[0]:.3f} x {r[3] - r[1]:.3f} m (dato {b} x {a})")
    control(len(tar) == 4, f"Hay {len(tar)} tarimas (dato 4)")
    tolp = D["tarima_tolerancia"]
    margen = min(min(r[0] - zr[0], r[1] - zr[1], zr[2] - r[2], zr[3] - r[3]) for r in tar.values())
    control(margen >= -tol, f"Las tarimas caben en la zona de estiba (margen minimo {margen:.3f} m)")
    control(margen >= tolp - tol, f"Corridas {tolp} m (tolerancia) siguen dentro de la zona (margen {margen:.3f} m)")
    nombres = list(tar)
    pares = [(nombres[i], nombres[j]) for i in range(4) for j in range(i + 1, 4)]
    gap = min(separacion(tar[x], tar[y]) for x, y in pares)
    control(gap >= 2 * tolp - tol, f"Entre tarimas hay al menos {gap:.3f} m: no chocan aunque dos se corran {tolp} m hacia la otra")
    ped = planta("/ZonaEstiba/Pedestal_CR20A")
    hol = min(separacion(ped, r) for r in tar.values())
    control(hol >= tolp - tol, f"Holgura pedestal-tarimas {hol:.3f} m (tolerancia {tolp} m)")
    pc = med[R + "/ZonaEstiba/Pedestal_CR20A"]["centro"]
    centrado = math.hypot(pc[0] - (zr[0] + zr[2]) / 2, pc[1] - (zr[1] + zr[3]) / 2)
    control(centrado <= tol, f"Pedestal del CR20A en el centro de la cruz (desvio {centrado:.3f} m)")

    t = med[R + "/Alimentacion/MiniBanda"]["tam"]
    control(abs(t[0] - D["minibanda_largo"]) <= tol, f"Mini-banda de {t[0]:.3f} m (dato {D['minibanda_largo']})")
    tope_x = med[R + "/Alimentacion/Tope"]["max"][0]
    control(abs(tope_x - med[R + "/Alimentacion/MiniBanda"]["max"][0]) <= tol, "El tope esta en el extremo de la mini-banda (punto de toma fijo)")
    bah = [p["ruta"] for p in lista if p["ruta"].startswith("/Alimentacion/Bahias/")]
    control(len(bah) == D["bahias"], f"Hay {len(bah)} bahias (dato {D['bahias']})")
    canales = [p["ruta"] for p in lista if p["ruta"].startswith("/Alimentacion/Banda/Canal")]
    control(len(canales) == D["canales"], f"La banda tiene {len(canales)} canales (dato {D['canales']})")

    sup_banda = max(med[R + c]["max"][2] for c in canales)
    h = med[R + "/Camara/Cuerpo"]["min"][2] - sup_banda
    control(abs(h - D["camara"]["altura_sobre_banda"]) <= tol, f"Camara a {h:.3f} m sobre la banda (dato {D['camara']['altura_sobre_banda']})")
    campo = med[R + "/Camara/Campo"]
    ct = sorted(campo["tam"][:2], reverse=True)
    control(cerca(ct, D["camara"]["campo"]), f"Campo de la camara {ct[0]:.3f} x {ct[1]:.3f} m (dato {D['camara']['campo'][0]} x {D['camara']['campo'][1]})")
    y0 = min(med[R + c]["min"][1] for c in canales)
    y1 = max(med[R + c]["max"][1] for c in canales)
    control(campo["min"][1] <= y0 + tol and campo["max"][1] >= y1 - tol,
            f"El campo cubre los {D['canales']} canales completos ({y1 - y0:.3f} m de canales en {campo['tam'][1]:.3f} m de campo)")

    # ---------- C. Piso: todo adentro, nada se pisa, pasos libres ----------
    todo = medidas(R)[R]
    control(todo["min"][0] >= -tol and todo["min"][1] >= -tol and todo["max"][0] <= Lx + tol and todo["max"][1] <= Wy + tol,
            f"Todo dentro del piso (X {todo['min'][0]:.2f} a {todo['max'][0]:.2f}, Y {todo['min'][1]:.2f} a {todo['max'][1]:.2f})")
    ocupan = {p["ruta"]: planta(p["ruta"]) for p in lista if not p["ruta"].startswith(NO_OCUPAN)}
    rutas = list(ocupan)
    choques = [f"{rutas[i]} con {rutas[j]}" for i in range(len(rutas)) for j in range(i + 1, len(rutas))
               if solapa(ocupan[rutas[i]], ocupan[rutas[j]])]
    control(not choques, f"Ningun equipo pisa a otro ({len(rutas)} equipos)" + (f"; chocan: {'; '.join(choques)}" if choques else ""))
    for n, (py0, py1) in S["pasos_personal"].items():
        franja = (0.0, py0, Lx, py1)
        dentro = [r for r, pl in ocupan.items() if solapa(pl, franja)]
        control(not dentro, f"Paso de personal {n} libre, {py1 - py0:.2f} m de ancho" + (f" (lo pisan: {', '.join(dentro)})" if dentro else ""))
    zona_libre = [r for r, pl in ocupan.items() if solapa(pl, zr) and "/ZonaEstiba/" not in r]
    control(not zona_libre, "En la zona de estiba solo hay tarimas y pedestal" + (f" (tambien: {', '.join(zona_libre)})" if zona_libre else ""))

    # ---------- D. Alcances en planta (informativo: el chequeo real en 3D es la etapa 2) ----------
    info = []
    c20 = med[R + "/ZonaEstiba/Pedestal_CR20A"]["centro"]
    c6 = med[R + "/Alimentacion/Pedestal_CR6AL"]["centro"]
    r20, r6 = D["cr20a"]["alcance"], D["cr6al"]["alcance"]
    sale = max(r20 - (Lx - c20[0]), r20 - (Wy - c20[1]), r20 - c20[1], 0.0)
    info.append(f"Circulo del CR20A ({r20} m) {'dentro del piso' if sale <= tol else f'sale {sale:.2f} m del piso'}")
    solape = r20 + r6 - math.hypot(c20[0] - c6[0], c20[1] - c6[1])
    info.append(f"Los circulos del CR20A y del CR6AL se solapan {max(solape, 0):.2f} m (zona de posible interferencia)")
    tx, ty = punto_toma(D, S)
    info.append(f"CR20A -> punto de toma: {math.hypot(tx - c20[0], ty - c20[1]):.3f} m en planta")
    lejos = max(math.hypot(x - c20[0], y - c20[1]) for r in tar.values() for x in (r[0], r[2]) for y in (r[1], r[3]))
    info.append(f"CR20A -> esquina mas lejana de las tarimas: {lejos:.3f} m en planta (la caja mas lejana esta mas cerca; ver etapa 2)")
    for n, ruta in (("banda (campo de camara)", "/Camara/Campo"), ("magazine", "/Alimentacion/Magazine")):
        pl = planta(ruta)
        info.append(f"CR6AL -> {n}, esquina mas lejana: {max(math.hypot(x - c6[0], y - c6[1]) for x in (pl[0], pl[2]) for y in (pl[1], pl[3])):.3f} m")
    pl = [planta(b) for b in bah]
    info.append(f"CR6AL -> bahia mas lejana, esquina: {max(math.hypot(x - c6[0], y - c6[1]) for r in pl for x in (r[0], r[2]) for y in (r[1], r[3])):.3f} m")

    try:
        limpiar_dibujos()
        z = PARAMS["z_circulos"]
        dibujar_circulo((c20[0], c20[1], z), r20, PARAMS["color_cr20a"])
        dibujar_circulo((c6[0], c6[1], z), r6, PARAMS["color_cr6al"])
        info.append("Circulos dibujados: naranja = CR20A 1,7 m, azul = CR6AL 1,8 m (borrar con limpiar_dibujos())")
    except Exception as e:
        info.append(f"No se pudieron dibujar los circulos: {e}")

    medir(R + "/Piso", R + "/ZonaEstiba", R + "/ZonaEstiba/Tarimas/Norte", R + "/Alimentacion/MiniBanda", R + "/Camara/Campo")
    return _reporte(filas, ruta_datos, info)


def _reporte(filas, ruta_datos, info):
    pasa = sum(f.startswith("PASA") for f in filas)
    estado = "ETAPA 1 LISTA" if pasa == len(filas) else "ETAPA 1 NO ESTA LISTA"
    texto = "\n".join([f"{estado}: {pasa} de {len(filas)} controles PASA", f"Datos: {ruta_datos}", ""] + filas +
                      ["", "INFORMATIVO"] + [f"  {i}" for i in info])
    os.makedirs(os.path.dirname(PARAMS["nota"]), exist_ok=True)
    open(PARAMS["nota"], "w", encoding="utf-8").write(texto)
    mostrar(texto + f"\n\nGuardado en {PARAMS['nota']}", "Etapa 1: verificacion", 1000, 700)


_verificar()
