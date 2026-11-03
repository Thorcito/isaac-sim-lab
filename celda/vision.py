"""Vision: clasificacion de estuches por color, posicion y orientacion, sin Isaac Sim.

Que hace:   1) intrinsecos de la camara (sensor, lente y resolucion de celda.json) y la
               conversion de pixel a metros en la celda, sobre el plano de la cara de arriba
               de los estuches;
            2) detectar(imagen): separa los estuches del fondo por saturacion y brillo, los
               clasifica por tono (HSV) en las 4 variedades o "desconocida", calcula una
               confianza (debajo de vision_umbral_confianza queda en "duda"), el centroide y
               la orientacion; si dos estuches iguales se tocan, los separa por largo;
            3) imagen_sintetica(...): genera una imagen de prueba de los 5 canales con numpy
               (ruido, brillo, viñeteo, tinte de la luz, etiqueta blanca, estuches tocandose).
Como usar:  from celda import vision
            dets = vision.detectar(img, D, S, escala=4)     # img: alto x ancho x 3, valores 0..1
Sin Isaac Sim: solo numpy. En la etapa 5 el adaptador le pasa la imagen del sensor de camara.
Pruebas:    pruebas/test_vision.py (incluye la matriz de confusion).

Orientacion de la imagen (supuesto, tambien vale para la camara de Isaac): la camara mira
hacia abajo; las columnas (u) crecen hacia +Y del mundo (a traves de los canales, 0,67 m) y
las filas (v) crecen hacia +X (sentido de la banda, 0,56 m). escala divide la resolucion para
que las pruebas sean rapidas: escala 4 = 612 x 512 px.
"""
import math

import numpy as np

from celda import geometria

FONDO, DESCONOCIDA = -1, -2


# ---------------- Camara ----------------

def intrinsecos(D, S, escala=1):
    """Parametros de la camara: fx, fy (px), cx, cy (px), ancho, alto (px), z (m hasta el plano)."""
    cam = S["camara"]
    ancho, alto = cam["resolucion_px"][0] // escala, cam["resolucion_px"][1] // escala
    pix_x = cam["sensor_mm"][0] / ancho
    pix_y = cam["sensor_mm"][1] / alto
    f = D["camara"]["focal_mm"]
    z = D["camara"]["altura_sobre_banda"] - S["estuche"]["alto"]   # hasta la cara de arriba
    return {"fx": f / pix_x, "fy": f / pix_y, "cx": (ancho - 1) / 2, "cy": (alto - 1) / 2,
            "ancho": ancho, "alto": alto, "z": z}


def campo_m(D, S):
    """Campo de vision sobre la banda (m): (a traves de los canales, a lo largo)."""
    cam, f, h = S["camara"], D["camara"]["focal_mm"], D["camara"]["altura_sobre_banda"]
    return cam["sensor_mm"][0] / f * h, cam["sensor_mm"][1] / f * h


def pixel_a_mundo(u, v, D, S, escala=1):
    """(x, y) en metros en la celda del pixel (u = columna, v = fila)."""
    k = intrinsecos(D, S, escala)
    fx, fy = S["camara"]["campo_centro"]
    return fx + (v - k["cy"]) / k["fy"] * k["z"], fy + (u - k["cx"]) / k["fx"] * k["z"]


def mundo_a_pixel(x, y, D, S, escala=1):
    """Inversa de pixel_a_mundo: (u, v)."""
    k = intrinsecos(D, S, escala)
    fx, fy = S["camara"]["campo_centro"]
    return k["cx"] + (y - fy) / k["z"] * k["fx"], k["cy"] + (x - fx) / k["z"] * k["fy"]


def mm_por_pixel(D, S, escala=1):
    k = intrinsecos(D, S, escala)
    return k["z"] / k["fx"] * 1000.0


# ---------------- Color ----------------

def rgb_a_hsv(img):
    """img (..., 3) en 0..1 -> h en grados (0..360), s y v en 0..1."""
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    mx, mn = img.max(axis=-1), img.min(axis=-1)
    d = mx - mn
    s = np.where(mx > 0, d / np.maximum(mx, 1e-9), 0.0)
    dd = np.maximum(d, 1e-9)
    h = np.where(mx == r, ((g - b) / dd) % 6, np.where(mx == g, (b - r) / dd + 2, (r - g) / dd + 4)) * 60.0
    h = np.where(d > 0, h, 0.0)
    return h, s, mx


def tonos(S):
    """{variedad: tono en grados} de los colores de _supuestos.variedades."""
    out = {}
    for k, v in S["variedades"].items():
        h, _, _ = rgb_a_hsv(np.array(v["color"], float))
        out[k] = float(h)
    return out


def _dist_tono(h, centro):
    d = np.abs(h - centro) % 360.0
    return np.minimum(d, 360.0 - d)


def suavizar(img, radio):
    """Promedio de cada pixel con sus vecinos en un cuadrado de (2 radio + 1) de lado: baja el ruido."""
    if radio <= 0:
        return img
    p = np.pad(img, ((radio, radio), (radio, radio), (0, 0)), mode="edge")
    H, W = img.shape[:2]
    acc = np.zeros_like(img)
    for dv in range(2 * radio + 1):
        for du in range(2 * radio + 1):
            acc += p[dv:dv + H, du:du + W]
    return acc / (2 * radio + 1) ** 2


def _tono_medio(h):
    """Promedio circular de tonos en grados (359 y 1 promedian 0, no 180)."""
    a = np.radians(h)
    return math.degrees(math.atan2(np.sin(a).mean(), np.cos(a).mean())) % 360.0


def clasificar_pixeles(img, S):
    """Mapa de clase por pixel: indice de variedad (0..n-1), DESCONOCIDA o FONDO; y la distancia de tono."""
    V = S["vision"]
    h, s, v = rgb_a_hsv(img)
    nombres = list(S["variedades"])
    centros = tonos(S)
    dist = np.stack([_dist_tono(h, centros[n]) for n in nombres])
    mejor = dist.argmin(axis=0)
    dmin = dist.min(axis=0)
    color = (s >= V["sat_min"]) & (v >= V["val_min"])
    clase = np.where(color, np.where(dmin <= V["tol_tono_grados"], mejor, DESCONOCIDA), FONDO)
    return clase, dmin, nombres


# ---------------- Componentes conexas (solo numpy) ----------------

def componentes(mask):
    """Etiqueta las regiones conectadas (4 vecinos) de una mascara booleana. Devuelve (etiquetas, n).

    Metodo por tramos: cada fila se parte en tramos de pixeles seguidos (con numpy); un tramo se
    une a los de la fila de abajo que se le superponen (union-find sobre tramos, que son pocos).
    """
    H, W = mask.shape
    borde = np.zeros((H, 1), bool)
    d = np.diff(np.hstack([borde, mask, borde]).astype(np.int8), axis=1)
    fi, ini = np.nonzero(d == 1)
    _, fin = np.nonzero(d == -1)          # mismo orden: fila a fila, de izquierda a derecha
    padre = list(range(len(fi)))

    def raiz(i):
        while padre[i] != i:
            padre[i] = padre[padre[i]]
            i = padre[i]
        return i

    filas = np.searchsorted(fi, np.arange(H + 1))   # tramos de la fila r: filas[r] .. filas[r+1]
    for r in range(H - 1):
        a, a1, b, b1 = filas[r], filas[r + 1], filas[r + 1], filas[r + 2]
        while a < a1 and b < b1:          # dos punteros sobre los tramos de r y r+1
            if ini[a] < fin[b] and ini[b] < fin[a]:
                ra, rb = raiz(a), raiz(b)
                if ra != rb:
                    padre[max(ra, rb)] = min(ra, rb)
            if fin[a] < fin[b]:
                a += 1
            else:
                b += 1
    raices = np.array([raiz(i) for i in range(len(fi))], dtype=np.int64)
    unicas, lab = np.unique(raices, return_inverse=True)
    etiquetas = np.zeros((H, W), np.int32)
    for f, i0, i1, l in zip(fi, ini, fin, lab):
        etiquetas[f, i0:i1] = l + 1
    return etiquetas, len(unicas)


# ---------------- Deteccion ----------------

def _estuche_px(D, S, escala):
    """Area de un estuche visto desde arriba, en pixeles."""
    mm = mm_por_pixel(D, S, escala)
    e = S["estuche"]
    return (e["largo"] * 1000 / mm) * (e["ancho"] * 1000 / mm)


def _forma(us, vs, D, S, escala):
    """Centroide en pixeles y en el mundo, y angulo del eje largo respecto de X del mundo (grados, -90..90]."""
    cu, cv = float(us.mean()), float(vs.mean())
    k = intrinsecos(D, S, escala)
    # ejes del mundo: X crece con v, Y crece con u (escalados a metros para que el angulo sea real)
    dx, dy = (vs - cv) / k["fy"], (us - cu) / k["fx"]
    cov = np.cov(np.vstack([dx, dy]))
    w, vec = np.linalg.eigh(cov)
    eje = vec[:, int(np.argmax(w))]
    ang = math.degrees(math.atan2(eje[1], eje[0]))
    ang = (ang + 90.0) % 180.0 - 90.0
    return (cu, cv), pixel_a_mundo(cu, cv, D, S, escala), ang, eje


def detectar(img, D, S, escala=1):
    """Detecta y clasifica los estuches de una imagen. Lista de dicts:

    categoria ("variedad" | "duda" | "desconocida"), variedad (A..D o None), confianza (0..1),
    clase_color (la variedad o "desconocida" que dio el color, aunque quede en duda),
    px (u, v), xy (m en la celda), angulo (grados respecto de X), area_px.
    """
    V = S["vision"]
    umbral = S["vision_umbral_confianza"]
    img = suavizar(img, V["suavizado_px"])
    clase, _, nombres = clasificar_pixeles(img, S)
    h = rgb_a_hsv(img)[0]
    centros = tonos(S)
    a_est = _estuche_px(D, S, escala)
    a_vis = a_est * V["area_completa"]
    cubierto = np.zeros(clase.shape, bool)
    out = []
    for c in list(range(len(nombres))) + [DESCONOCIDA]:
        etiquetas, n = componentes(clase == c)
        if n == 0:
            continue
        cuentas = np.bincount(etiquetas.ravel())
        for lab in np.nonzero(cuentas >= V["area_minima"] * a_est)[0]:
            if lab == 0:
                continue
            vs, us = np.nonzero(etiquetas == lab)
            # cuantos estuches hay en la mancha (si se tocan dos iguales, la mancha es el doble de larga)
            cuantos = max(1, int(round(len(us) / a_vis))) if len(us) > 1.5 * a_vis else 1
            _, _, ang, eje = _forma(us, vs, D, S, escala)
            k = intrinsecos(D, S, escala)
            proy = ((vs - vs.mean()) / k["fy"]) * eje[0] + ((us - us.mean()) / k["fx"]) * eje[1]
            cortes = np.quantile(proy, np.linspace(0, 1, cuantos + 1))
            for i in range(cuantos):
                sel = (proy >= cortes[i]) & (proy <= cortes[i + 1]) if i == cuantos - 1 else (proy >= cortes[i]) & (proy < cortes[i + 1])
                su, sv = us[sel], vs[sel]
                if len(su) < 3:
                    continue
                px, xy, ang_i, _ = _forma(su, sv, D, S, escala)
                if c == DESCONOCIDA:
                    f_tono = 1.0
                else:
                    # tono medio de la mancha (promedio circular: el ruido de cada pixel se cancela)
                    hm = _tono_medio(h[sv, su])
                    dm = float(_dist_tono(hm, centros[nombres[c]]))
                    f_tono = min(1.0, max(0.0, 1 - (dm - V["tol_estricta_grados"]) /
                                          (V["tol_tono_grados"] - V["tol_estricta_grados"])))
                conf = f_tono * min(1.0, len(su) / a_vis)
                nombre = "desconocida" if c == DESCONOCIDA else nombres[c]
                if conf < umbral:
                    cat, var = "duda", None
                elif c == DESCONOCIDA:
                    cat, var = "desconocida", None
                else:
                    cat, var = "variedad", nombre
                out.append({"categoria": cat, "variedad": var, "confianza": conf, "clase_color": nombre,
                            "px": px, "xy": xy, "angulo": ang if cuantos > 1 else ang_i, "area_px": int(len(su))})
                cubierto[sv, su] = True
    # Red de seguridad: color del tamano de un estuche que ninguna clase explico (por ejemplo un tono
    # entre dos variedades, que se parte en manchas chicas de cada una) queda en duda: no se ignora.
    resto = (clase != FONDO) & ~cubierto
    etiquetas, n = componentes(resto)
    if n:
        cuentas = np.bincount(etiquetas.ravel())
        for lab in np.nonzero(cuentas >= V["area_completa"] * 0.5 * a_est)[0]:
            if lab == 0:
                continue
            vs, us = np.nonzero(etiquetas == lab)
            px, xy, ang, _ = _forma(us, vs, D, S, escala)
            if any(math.dist(xy, d["xy"]) < S["estuche"]["ancho"] / 2 for d in out):
                continue   # es el resto ruidoso de un estuche que ya se detecto
            out.append({"categoria": "duda", "variedad": None, "confianza": 0.0, "clase_color": "mezcla",
                        "px": px, "xy": xy, "angulo": ang, "area_px": int(len(us))})
    return out


# ---------------- Imagenes sinteticas ----------------

def canales_y(D, S):
    """Y del centro de cada canal (m)."""
    b = S["banda"]
    W = geometria.ancho_canales(D, S)
    return [b["y_centro"] - W / 2 + b["ancho_canal"] / 2 + k * (b["ancho_canal"] + b["divisor"]) for k in range(D["canales"])]


def imagen_sintetica(D, S, estuches, escala=4, rnd=None, brillo=1.0, ruido=0.02, tinte=(1.0, 1.0, 1.0), vineteo=0.15):
    """Imagen (alto x ancho x 3, 0..1) de la banda vista por la camara, con los estuches dados.

    estuches: lista de dicts {"color": (r, g, b), "xy": (x, y) en m, "giro": grados}.
    brillo: ganancia de la luz; ruido: desvio del ruido gaussiano; tinte: ganancia por canal (luz
    mas calida o fria); vineteo: cuanto se oscurecen las esquinas.
    """
    rnd = rnd or np.random.default_rng(0)
    k = intrinsecos(D, S, escala)
    H, W = k["alto"], k["ancho"]
    vv, uu = np.mgrid[0:H, 0:W].astype(float)
    X, Y = pixel_a_mundo(uu, vv, D, S, escala)
    b, e, V = S["banda"], S["estuche"], S["vision"]
    img = np.empty((H, W, 3))
    img[:] = 0.20 + 0.03 * rnd.standard_normal((H, W, 1))          # banda gris con textura
    Wc = geometria.ancho_canales(D, S)
    y = b["y_centro"] - Wc / 2
    for i in range(D["canales"] - 1):                                # divisores claros entre canales
        y += b["ancho_canal"]
        img[(Y >= y) & (Y < y + b["divisor"])] = 0.75
        y += b["divisor"]
    fuera = (Y < b["y_centro"] - Wc / 2) | (Y > b["y_centro"] + Wc / 2) | (X > b["x_fin"])
    img[fuera] = 0.08                                                # estructura y piso, oscuros
    for est in estuches:
        a = math.radians(est["giro"])
        dx, dy = X - est["xy"][0], Y - est["xy"][1]
        lx, ly = dx * math.cos(a) + dy * math.sin(a), -dx * math.sin(a) + dy * math.cos(a)
        dentro = (np.abs(lx) <= e["largo"] / 2) & (np.abs(ly) <= e["ancho"] / 2)
        tono = np.array(est["color"]) * rnd.uniform(0.92, 1.05)
        img[dentro] = tono
        et = (np.abs(lx) <= e["largo"] * V["etiqueta"][0] / 2) & (np.abs(ly) <= e["ancho"] * V["etiqueta"][1] / 2)
        img[et] = 0.92                                               # etiqueta blanca con codigo de barras
    r2 = ((uu - k["cx"]) / W) ** 2 + ((vv - k["cy"]) / H) ** 2
    img = img * (1.0 - vineteo * 4 * r2)[..., None] * brillo * np.array(tinte)
    img = img + ruido * rnd.standard_normal(img.shape)
    return np.clip(img, 0.0, 1.0)


def escena_aleatoria(D, S, rnd, extra=None, prob_tocar=0.4):
    """Estuches al azar en los 5 canales, contra el final de la banda y en fila; a veces tocandose.

    extra: dict variedad -> color para variedades fuera de receta que pueden aparecer (con 10 %).
    Devuelve lista de dicts {"variedad", "color", "xy", "giro"} (la verdad para comparar).
    """
    e, b = S["estuche"], S["banda"]
    colores = {k: v["color"] for k, v in S["variedades"].items()}
    if extra:
        colores.update(extra)
    nombres = list(colores)
    pesos = np.array([1.0 if n in S["variedades"] else 0.4 for n in nombres])
    pesos /= pesos.sum()
    # campo visto en el plano de la cara de arriba de los estuches (un poco menor que sobre la banda)
    k = intrinsecos(D, S, 4)
    x_campo, x_fin_campo = pixel_a_mundo(k["cx"], 0, D, S, 4)[0], pixel_a_mundo(k["cx"], k["alto"] - 1, D, S, 4)[0]
    # la fila arranca dentro del campo (el estuche contra el tope queda en parte fuera: ver nota)
    x_inicio = min(b["x_fin"], x_fin_campo) - e["largo"] / 2 - 0.005
    out = []
    for yc in canales_y(D, S):
        x = x_inicio
        for _ in range(int(rnd.integers(0, 4))):
            if x - e["largo"] / 2 < x_campo:
                break
            v = nombres[int(rnd.choice(len(nombres), p=pesos))]
            out.append({"variedad": v, "color": colores[v], "xy": (x, yc + rnd.uniform(-0.005, 0.005)),
                        "giro": float(rnd.uniform(-6, 6))})
            x -= e["largo"] + (0.0 if rnd.random() < prob_tocar else rnd.uniform(0.02, 0.10))
    return out


# Rangos de luz y ruido de las imagenes de prueba (se sortea un valor por imagen)
CONDICIONES = {
    "normales": {"brillo": (0.6, 1.3), "ruido": (0.01, 0.04), "tinte": 0.07, "vineteo": (0.0, 0.25)},
    "dificiles": {"brillo": (0.30, 1.6), "ruido": (0.03, 0.09), "tinte": 0.18, "vineteo": (0.1, 0.45)},
}


def matriz_confusion(D, S, n_imagenes=40, escala=4, semilla=7, extra=None, condiciones="normales"):
    """Corre detectar() sobre imagenes sinteticas con luz variable y compara con la verdad.

    extra: {nombre: color} de variedades fuera de receta que aparecen en las imagenes.
    condiciones: clave de CONDICIONES (rango de brillo, ruido, tinte de la luz y viñeteo).
    Devuelve dict: filas (verdad), columnas (prediccion), matriz {verdad: {prediccion: n}}, falsos
    (detecciones sin estuche real), errores de posicion (mm) y de angulo (grados) de los aciertos.
    """
    rnd = np.random.default_rng(semilla)
    extra = extra or {}
    C = CONDICIONES[condiciones]
    filas = list(S["variedades"]) + list(extra)
    cols = list(S["variedades"]) + ["desconocida", "duda", "no detectado"]
    M = {f: {c: 0 for c in cols} for f in filas}
    err_mm, err_ang, falsos = [], [], 0
    for _ in range(n_imagenes):
        verdad = escena_aleatoria(D, S, rnd, extra)
        img = imagen_sintetica(D, S, verdad, escala, rnd, brillo=float(rnd.uniform(*C["brillo"])),
                               ruido=float(rnd.uniform(*C["ruido"])),
                               tinte=tuple(rnd.uniform(1 - C["tinte"], 1 + C["tinte"], 3)),
                               vineteo=float(rnd.uniform(*C["vineteo"])))
        dets = detectar(img, D, S, escala)
        usadas = set()
        for t in verdad:
            cand = [(math.dist(d["xy"], t["xy"]), i) for i, d in enumerate(dets) if i not in usadas]
            cand = [c for c in cand if c[0] < S["estuche"]["ancho"] / 2]
            if not cand:
                M[t["variedad"]]["no detectado"] += 1
                continue
            dist, i = min(cand)
            usadas.add(i)
            d = dets[i]
            pred = d["variedad"] if d["categoria"] == "variedad" else d["categoria"]
            M[t["variedad"]][pred] += 1
            if pred == t["variedad"]:
                err_mm.append(dist * 1000)
                err_ang.append(abs((d["angulo"] - t["giro"] + 90) % 180 - 90))
        falsos += len(dets) - len(usadas)
    return {"filas": filas, "columnas": cols, "matriz": M, "falsos": falsos,
            "err_mm_medio": float(np.mean(err_mm)) if err_mm else float("nan"),
            "err_mm_max": float(np.max(err_mm)) if err_mm else float("nan"),
            "err_ang_max": float(np.max(err_ang)) if err_ang else float("nan")}
