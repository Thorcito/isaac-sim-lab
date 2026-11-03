"""Genera los resultados de la logica de la celda (corre en la PC, no en Isaac Sim).

Que hace:   con celda/ y celda.json, escribe en resultados/:
            - camadas/camada_N.png: cada camada de la tarima Norte, con la de abajo punteada y el
              orden de estiba (para revisar el trabado a ojo);
            - tiempos.md: tabla de movimientos tipo de los dos robots;
            - ritmo.md y ritmo.png: modelo de ritmo, configuracion actual y propuesta, cada
              escenario a 15 y 20 estuches/min;
            - vision.md y vision_ejemplo.png: matriz de confusion (luz normal y dificil) y una
              imagen sintetica con lo que detecto;
            - datos.json: todos los numeros (los usa resultados/nota.md).
Correr:     desde la raiz del repo, con numpy y matplotlib:
                python resultados/generar.py
            Tarda unos 3 minutos (cinematica inversa, 32 escenarios x 5 semillas, 80 imagenes).
"""
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from celda import datos, geometria, modelo_ritmo, recetas, tiempos, vision  # noqa: E402

SALIDA = os.path.join(REPO, "resultados")
CACHE = os.path.join(REPO, ".cache", "robots")
# Paleta categorica validada (skill dataviz, tema por defecto): ritmo 15 = azul, 20 = naranja
AZUL, NARANJA, TINTA, TINTA_2, GRILLA = "#2a78d6", "#eb6834", "#1f1f1f", "#5c5c5c", "#e4e4e4"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": TINTA_2, "axes.labelcolor": TINTA, "xtick.color": TINTA_2,
                     "ytick.color": TINTA_2, "axes.spines.top": False, "axes.spines.right": False})


def camadas(D, S):
    os.makedirs(os.path.join(SALIDA, "camadas"), exist_ok=True)
    t = recetas.trabado(D, S)
    ex, ey = S["pedestal_cr20a"]["centro"]
    n = geometria.camadas_posibles(D, S)
    rutas = []
    for k in range(1, n + 1):
        fig, ax = plt.subplots(figsize=(5.2, 4.6))
        x0, y0, x1, y1 = geometria.rect_tarima(D, S, "Norte")
        ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#d9c2a0", ec=TINTA_2, lw=1))
        if k > 1:
            for c in geometria.cajas_camada(D, S, "Norte", k - 1):
                (cx, cy), (hx, hy) = c["centro"], c["medio"]
                ax.add_patch(plt.Rectangle((cx - hx, cy - hy), 2 * hx, 2 * hy, fill=False, ec=TINTA_2, lw=1, ls="--"))
        for i, c in enumerate(recetas.orden_estiba(D, S, "Norte", k)):
            (cx, cy), (hx, hy) = c["centro"], c["medio"]
            ax.add_patch(plt.Rectangle((cx - hx + 0.006, cy - hy + 0.006), 2 * hx - 0.012, 2 * hy - 0.012,
                                       fc=AZUL if c["giro"] % 180 == 0 else NARANJA, alpha=0.55, ec=TINTA, lw=1.2))
            ax.text(cx, cy, str(i + 1), ha="center", va="center", fontsize=11, color=TINTA, weight="bold")
        # pedestal del CR20A, para ver desde donde estiba
        lado = S["pedestal_cr20a"]["lado"]
        ax.add_patch(plt.Rectangle((ex - lado / 2, ey - lado / 2), lado, lado, fc=TINTA_2, ec=TINTA))
        ax.text(ex, ey - lado / 2 - 0.06, "CR20A", ha="center", va="top", color=TINTA)
        ax.set_aspect("equal")
        ax.set_xlim(min(x0, ex - lado) - 0.1, max(x1, ex + lado) + 0.1)
        ax.set_ylim(min(y0, ey - lado) - 0.2, max(y1, ey + lado) + 0.1)
        par = "impar" if k % 2 else "par"
        ax.set_title(f"Tarima Norte, camada {k} de {n} ({par}). Punteada: camada de abajo.\n"
                     f"Azul: largo en X, naranja: largo en Y. Numero = orden de estiba.", fontsize=9, color=TINTA)
        ax.set_xlabel("x (m)")
        ax.set_ylabel("y (m)")
        ruta = os.path.join(SALIDA, "camadas", f"camada_{k}.png")
        fig.tight_layout()
        fig.savefig(ruta, dpi=110)
        plt.close(fig)
        rutas.append(ruta)
    return t, rutas


def tabla_md(filas, columnas, encabezados):
    out = ["| " + " | ".join(encabezados) + " |", "|" + "---|" * len(encabezados)]
    for f in filas:
        out.append("| " + " | ".join(c(f) if callable(c) else str(f[c]) for c in columnas) + " |")
    return "\n".join(out)


def grafico_ritmo(tab):
    configs = list(dict.fromkeys(f["config"] for f in tab))
    fig, axes = plt.subplots(len(configs), 1, figsize=(8, 7.5), sharex=True)
    for ax, cfg in zip(axes, configs):
        filas = [f for f in tab if f["config"] == cfg]
        escs = list(dict.fromkeys(f["escenario"] for f in filas))
        y = np.arange(len(escs))
        for j, (ritmo, color) in enumerate(((15, AZUL), (20, NARANJA))):
            v = [next(f["estuches_min"] for f in filas if f["escenario"] == e and f["ritmo"] == ritmo) for e in escs]
            barras = ax.barh(y + (j - 0.5) * 0.38, v, height=0.34, color=color, label=f"llegan {ritmo}/min")
            for b, val in zip(barras, v):
                ax.text(val + 0.2, b.get_y() + b.get_height() / 2, f"{val:.1f}", va="center", fontsize=8, color=TINTA)
        for ref in (15, 20):
            ax.axvline(ref, color=TINTA_2, lw=0.8, ls=":")
        ax.set_yticks(y, escs)
        ax.invert_yaxis()
        ax.set_title(cfg, loc="left", color=TINTA, fontsize=10)
        ax.grid(axis="x", color=GRILLA, lw=0.6)
        ax.set_axisbelow(True)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper right", ncol=2, frameon=False)
    axes[-1].set_xlabel("estuches encajados por minuto (media de 5 semillas, 1 h simulada)")
    axes[-1].set_xlim(0, 23)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    ruta = os.path.join(SALIDA, "ritmo.png")
    fig.savefig(ruta, dpi=110)
    plt.close(fig)


def ejemplo_vision(D, S):
    rnd = np.random.default_rng(11)
    verdad = vision.escena_aleatoria(D, S, rnd, {"X": (0.60, 0.20, 0.75)}, prob_tocar=0.6)
    img = vision.imagen_sintetica(D, S, verdad, 4, rnd, brillo=0.8, ruido=0.03)
    dets = vision.detectar(img, D, S, 4)
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.imshow(img)
    for d in dets:
        u, v = d["px"]
        txt = d["variedad"] if d["categoria"] == "variedad" else d["categoria"]
        ax.plot(u, v, "+", color="white", ms=10, mew=2)
        ax.text(u + 6, v - 6, f"{txt} {d['confianza']:.2f}\n{d['angulo']:+.0f} grados", color="white", fontsize=8,
                bbox={"fc": "black", "alpha": 0.6, "lw": 0})
    ax.set_title("Imagen sintetica (612 x 512 px) y lo que detecto: variedad, confianza y angulo", fontsize=9)
    ax.set_xlabel("u (px)  ->  +Y de la celda")
    ax.set_ylabel("v (px)  ->  +X (sentido de la banda)")
    fig.tight_layout()
    fig.savefig(os.path.join(SALIDA, "vision_ejemplo.png"), dpi=110)
    plt.close(fig)


def main():
    D, S = datos.cargar()
    robots = {c: datos.robot(D, S, c, CACHE) for c in ("cr20a", "cr6al")}
    todo = {}

    t, _ = camadas(D, S)
    todo["trabado"] = {k: t[k] for k in ("cajas", "ocupacion", "voladizo", "puentes", "juntas_m", "apoyo_min",
                                          "transformacion", "descripcion")}
    alto, limite, n = recetas.altura_estiba(D, S)
    todo["estiba"] = {"alto_m": alto, "limite_m": limite, "camadas": n, "desde": S["estiba_max_desde"],
                      "masa_caja_llena_kg": recetas.masa_caja_llena(S)}

    T = tiempos.Tiempos(D, S, robots)
    res = T.resumen()
    todo["tiempos"] = res
    with open(os.path.join(SALIDA, "tiempos.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("# Tiempos de movimiento (modelo)\n\nGenerado por `resultados/generar.py` con la cinematica del URDF "
                "y las velocidades de `celda.json -> robots_movimiento`. Segundos.\n\n")
        f.write(tabla_md(res, ["robot", "movimiento", lambda r: f"{r['min']:.2f}", lambda r: f"{r['medio']:.2f}",
                               lambda r: f"{r['max']:.2f}", "n"], ["Robot", "Movimiento", "Min", "Medio", "Max", "Casos"]))
        f.write("\n")

    tab = modelo_ritmo.correr_escenarios(D, S, T, modelo_ritmo.escenarios(S, "actual") +
                                         modelo_ritmo.escenarios(S, "propuesta"))
    todo["ritmo"] = tab
    with open(os.path.join(SALIDA, "ritmo.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("# Modelo de ritmo (eventos discretos)\n\nGenerado por `resultados/generar.py`. Media de "
                f"{S['ritmo']['semillas']} semillas, {S['ritmo']['duracion_s'] / 60:.0f} min medidos despues de "
                f"{S['ritmo']['calentamiento_s'] / 60:.0f} min de arranque. Perdidos, desviados y retenidos: estuches en la "
                "hora medida.\n\n")
        f.write(tabla_md(tab, ["config", "escenario", "ritmo", lambda r: f"{r['estuches_min']:.1f}",
                               lambda r: f"{r['ocupacion_cr6al'] * 100:.0f} %", lambda r: f"{r['ocupacion_cr20a'] * 100:.0f} %",
                               lambda r: f"{r['cola_media']:.1f}", lambda r: f"{r['perdidos']:.0f}",
                               lambda r: f"{r['desviados']:.0f}", lambda r: f"{r['retenidos']:.0f}",
                               lambda r: f"{r['sin_carton_min']:.1f}", "cuello"],
                         ["Configuracion", "Escenario", "Llegan /min", "Encajados /min", "CR6AL", "CR20A",
                          "Cola media", "Perdidos", "Desviados", "Retenidos", "Sin carton (min)", "Cuello de botella"]))
        f.write("\n\n![Estuches por minuto](ritmo.png)\n")
    grafico_ritmo(tab)

    extra = {"X violeta": (0.60, 0.20, 0.75), "Y naranja": (0.95, 0.45, 0.10)}
    todo["vision"] = {}
    with open(os.path.join(SALIDA, "vision.md"), "w", encoding="utf-8", newline="\n") as f:
        k = vision.intrinsecos(D, S, 4)
        f.write("# Vision: matriz de confusion con imagenes sinteticas\n\nGenerado por `resultados/generar.py`. "
                f"40 imagenes por condicion, {k['ancho']} x {k['alto']} px (resolucion real / 4, "
                f"{vision.mm_por_pixel(D, S, 4):.2f} mm/px). Filas: verdad; columnas: lo que dijo la vision. "
                "'X violeta' e 'Y naranja' estan fuera de receta (el naranja queda entre las variedades A y C).\n")
        for cond in ("normales", "dificiles"):
            r = vision.matriz_confusion(D, S, 40, 4, extra=extra, condiciones=cond)
            todo["vision"][cond] = r
            C = vision.CONDICIONES[cond]
            f.write(f"\n## Luz {'normal' if cond == 'normales' else 'dificil'}\n\nBrillo {C['brillo'][0]}-{C['brillo'][1]}, ruido {C['ruido'][0]}-{C['ruido'][1]}, "
                    f"tinte +/-{C['tinte'] * 100:.0f} %, viñeteo {C['vineteo'][0]}-{C['vineteo'][1]}.\n\n")
            f.write(tabla_md([{"v": v, **r["matriz"][v]} for v in r["filas"]], ["v"] + r["columnas"], ["Verdad"] + r["columnas"]))
            f.write(f"\n\nDetecciones sin estuche real: {r['falsos']}. Error de posicion de los aciertos: medio "
                    f"{r['err_mm_medio']:.1f} mm, maximo {r['err_mm_max']:.1f} mm. Error de angulo maximo {r['err_ang_max']:.1f} grados.\n")
        f.write("\n![Ejemplo](vision_ejemplo.png)\n")
    ejemplo_vision(D, S)

    with open(os.path.join(SALIDA, "datos.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(todo, f, indent=1, ensure_ascii=False, default=float)
    print("Listo:", SALIDA)


if __name__ == "__main__":
    main()
