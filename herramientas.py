"""Herramientas generales para Isaac Sim 6.2 (repo Thorcito/isaac-sim-lab).

Cargar UNA vez por sesion (despues de cada reinicio de Isaac Sim):
    exec(open("/isaac-sim/trabajo/repo/herramientas.py").read())

Bajar la ultima version del repo y recargar las herramientas:
    actualizar()

Despues se llaman las funciones, por ejemplo:
    ayuda()
    ver("/isaac-sim/trabajo/notas/inventario_ejemplos.txt")
    correr("fase1/layout.py")
"""
import os, sys, re, shutil, subprocess, platform, inspect, io, tarfile, tempfile, urllib.request
from collections import defaultdict
import omni.ui as ui

TRABAJO = "/isaac-sim/trabajo"
REPO_DIR = TRABAJO + "/repo"        # copia del repo: se REEMPLAZA en cada actualizar()
MIS_SCRIPTS = TRABAJO + "/scripts"  # tus scripts propios: actualizar() no los toca
REPO_URL = "https://codeload.github.com/Thorcito/isaac-sim-lab/tar.gz/refs/heads/main"
_VENTANAS = {}


def mostrar(texto, titulo="Resultado", ancho=1000, alto=700):
    """Muestra cualquier texto en una ventana copiable (clic, Ctrl+A, Ctrl+C)."""
    win = ui.Window(titulo, width=ancho, height=alto)
    with win.frame:
        f = ui.StringField(multiline=True)
        f.model.set_value(str(texto))
    _VENTANAS[titulo] = win  # mantiene la ventana viva
    return win


def ver(ruta):
    """Abre un archivo de texto en una ventana copiable."""
    try:
        texto = open(ruta, encoding="utf-8", errors="ignore").read()
    except Exception as e:
        texto = f"No se pudo abrir {ruta}:\n{e}"
    return mostrar(texto, f"Visor: {os.path.basename(ruta)}")


def archivos(carpeta=TRABAJO):
    """Lista carpetas y archivos (con tamano) a partir de una carpeta."""
    lineas = []
    for root, dirs, files in os.walk(carpeta):
        nivel = root.replace(carpeta, "").count(os.sep)
        lineas.append("  " * nivel + (os.path.basename(root) or root) + "/")
        for f in sorted(files):
            p = os.path.join(root, f)
            lineas.append("  " * (nivel + 1) + f"{f}  ({os.path.getsize(p)/1024:.1f} KB)")
    return mostrar("\n".join(lineas) or "(vacia)", f"Archivos: {carpeta}", 800, 600)


def guardar(nombre, texto, carpeta=MIS_SCRIPTS):
    """Guarda un texto o codigo en un archivo. Ej: guardar("mi_script.py", '''print(1)''')"""
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, nombre)
    open(ruta, "w", encoding="utf-8").write(texto)
    return mostrar(f"Guardado en {ruta}", "Guardado", 600, 120)


def correr(nombre):
    """Corre un script. Busca primero en scripts/ (tuyos) y luego en repo/. Ej: correr("fase1/layout.py")"""
    if nombre.startswith("/"):
        ruta = nombre
    else:
        ruta = next((os.path.join(c, nombre) for c in (MIS_SCRIPTS, REPO_DIR)
                     if os.path.isfile(os.path.join(c, nombre))), None)
    if not ruta or not os.path.isfile(ruta):
        return mostrar(f"No encontre {nombre} en {MIS_SCRIPTS} ni en {REPO_DIR}", "correr", 700, 150)
    exec(open(ruta, encoding="utf-8").read(), globals())


def actualizar():
    """Baja la ultima version del repo de GitHub a trabajo/repo y recarga las herramientas."""
    try:
        req = urllib.request.Request(REPO_URL, headers={"Cache-Control": "no-cache"})
        datos = urllib.request.urlopen(req, timeout=30).read()
        tmp = tempfile.mkdtemp()
        with tarfile.open(fileobj=io.BytesIO(datos), mode="r:gz") as tar:
            tar.extractall(tmp, filter="data")
        raiz = os.path.join(tmp, os.listdir(tmp)[0])   # carpeta isaac-sim-lab-main/
        if os.path.isdir(REPO_DIR):
            shutil.rmtree(REPO_DIR)
        shutil.copytree(raiz, REPO_DIR)
        shutil.rmtree(tmp, ignore_errors=True)
        lista = []
        for root, _, files in os.walk(REPO_DIR):
            for f in sorted(files):
                lista.append(os.path.relpath(os.path.join(root, f), REPO_DIR))
        exec(open(os.path.join(REPO_DIR, "herramientas.py"), encoding="utf-8").read(), globals())
        return mostrar(f"Repo actualizado en {REPO_DIR} ({len(datos)/1024:.0f} KB)\n\n" + "\n".join(sorted(lista)),
                       "actualizar", 800, 500)
    except Exception as e:
        return mostrar(f"No se pudo actualizar:\n{e}", "actualizar", 700, 200)


def diagnostico():
    """Python, permisos de trabajo, internet, git y modulos isaacsim cargados."""
    out = [f"Python: {sys.version.split()[0]} | {platform.platform()}"]
    out.append(f"trabajo existe: {os.path.isdir(TRABAJO)} | escribible: {os.access(TRABAJO, os.W_OK)}")
    for t in ["git", "pip", "bash", "curl"]:
        out.append(f"{t} -> {shutil.which(t)}")
    try:
        import urllib.request
        out.append(f"internet github: {urllib.request.urlopen('https://github.com', timeout=5).status}")
    except Exception as e:
        out.append(f"internet github: {e}")
    try:
        out.append("usuario: " + subprocess.run(["whoami"], capture_output=True, text=True).stdout.strip())
    except Exception as e:
        out.append(f"subprocess: {e}")
    mods = sorted({".".join(m.split(".")[:3]) for m in sys.modules if m.startswith("isaacsim.")})
    out.append("modulos isaacsim cargados:\n  " + "\n  ".join(mods))
    return mostrar("\n".join(out), "Diagnostico")


def inventario_ejemplos(guardar_txt=True):
    """Lista Robotics Examples y Physics Demo Scenes (solo lee, no cambia nada)."""
    import omni.kit.app
    from isaacsim.examples.browser import get_instance
    mgr = omni.kit.app.get_app().get_extension_manager()
    out = ["=== ROBOTICS EXAMPLES ==="]
    ex = get_instance()._browser_model._examples
    for cat in sorted(ex):
        items = ex[cat]
        items = items.values() if isinstance(items, dict) else items
        names = [str(getattr(i, "name", None) or getattr(i, "_name", None) or repr(i)[:60]) for i in items]
        out.append(f"{cat}: {', '.join(sorted(names))}")
    phys, pexts = defaultdict(set), []
    for e in mgr.get_extensions():
        n = e["name"]
        if not ("physx" in n and "demo" in n):
            continue
        pexts.append(n)
        for root, _, files in os.walk(mgr.get_extension_path(e["id"])):
            for f in files:
                if not f.endswith(".py"):
                    continue
                s = open(os.path.join(root, f), encoding="utf-8", errors="ignore").read()
                t = re.search(r"^\s*title\s*=\s*[\"'](.+?)[\"']", s, re.M)
                c = re.search(r"category\s*=\s*demo\.Categories\.(\w+)", s)
                if t:
                    phys[c.group(1) if c else "?"].add(t.group(1))
    out += ["", "=== PHYSICS DEMOS ===", "Extensiones: " + ", ".join(pexts)]
    out += [f"{k}: {', '.join(sorted(v))}" for k, v in sorted(phys.items())]
    texto = "\n".join(out)
    if guardar_txt:
        os.makedirs(TRABAJO + "/notas", exist_ok=True)
        open(TRABAJO + "/notas/inventario_ejemplos.txt", "w").write(texto)
    return mostrar(texto, "Inventario de ejemplos", 1100, 800)


def inspeccionar(obj, titulo="Inspector"):
    """Muestra atributos y metodos de cualquier objeto de Python."""
    out = [f"TIPO: {type(obj).__module__}.{type(obj).__name__}"]
    for k, v in (vars(obj).items() if hasattr(obj, "__dict__") else []):
        info = f"len={len(v)}" if isinstance(v, (list, dict, set, tuple)) else ""
        out.append(f"{k}: {type(v).__name__} {info}")
        if isinstance(v, dict) and v:
            out.append(f"    claves: {list(v.keys())[:40]}")
    out.append("\nMETODOS: " + ", ".join(m for m in dir(obj) if not m.startswith("_")))
    return mostrar("\n".join(out), titulo)


def prims(raiz="/"):
    """Arbol de prims de la escena abierta, con tipo y fisica. Ej: prims("/World/Robot")"""
    import omni.usd
    from pxr import Usd, UsdPhysics
    stage = omni.usd.get_context().get_stage()
    inicio = stage.GetPrimAtPath(raiz) if raiz != "/" else stage.GetPseudoRoot()
    if not inicio or not inicio.IsValid():
        return mostrar(f"No existe el prim {raiz}", "Prims")
    out = []
    for p in Usd.PrimRange(inicio):
        if p.IsPseudoRoot():
            continue
        nivel = str(p.GetPath()).count("/") - 1
        fis = []
        if p.HasAPI(UsdPhysics.RigidBodyAPI): fis.append("rigid")
        if p.HasAPI(UsdPhysics.CollisionAPI): fis.append("collision")
        if p.HasAPI(UsdPhysics.ArticulationRootAPI): fis.append("ARTICULATION")
        out.append("  " * nivel + f"{p.GetName()}  [{p.GetTypeName()}] {' '.join(fis)}")
    return mostrar("\n".join(out) or "(escena vacia)", f"Prims: {raiz}", 900, 700)


def escena():
    """Resumen de la escena abierta: unidades, fisica, cuerpos, robots, joints, camaras y luces."""
    import omni.usd, omni.timeline
    from pxr import Usd, UsdGeom, UsdPhysics, UsdLux
    stage = omni.usd.get_context().get_stage()
    if stage is None:
        return mostrar("No hay escena abierta", "Escena")
    out = []
    url = stage.GetRootLayer().identifier
    out.append(f"ARCHIVO: {url}")
    out.append(f"Unidades: {UsdGeom.GetStageMetersPerUnit(stage)} m por unidad | Eje arriba: {UsdGeom.GetStageUpAxis(stage)}")
    tl = omni.timeline.get_timeline_interface()
    out.append(f"Timeline: {'PLAY' if tl.is_playing() else 'detenido'} | t = {tl.get_current_time():.2f} s")

    tipos = defaultdict(int)
    escenas_fis, cuerpos, estaticos, robots, joints, camaras, luces = [], [], [], [], [], [], []
    for p in stage.Traverse():
        tipos[p.GetTypeName() or "(sin tipo)"] += 1
        ruta = str(p.GetPath())
        if p.IsA(UsdPhysics.Scene):
            s = UsdPhysics.Scene(p)
            g = s.GetGravityMagnitudeAttr().Get()
            d = s.GetGravityDirectionAttr().Get()
            hz = p.GetAttribute("physxScene:timeStepsPerSecond").Get() if p.HasAttribute("physxScene:timeStepsPerSecond") else None
            gpu = p.GetAttribute("physxScene:enableGPUDynamics").Get() if p.HasAttribute("physxScene:enableGPUDynamics") else None
            escenas_fis.append(f"{ruta} | gravedad {g} dir {d} | pasos/s {hz} | GPU {gpu}")
        if p.HasAPI(UsdPhysics.RigidBodyAPI):
            m = p.GetAttribute("physics:mass").Get() if p.HasAttribute("physics:mass") else None
            cin = p.GetAttribute("physics:kinematicEnabled").Get() if p.HasAttribute("physics:kinematicEnabled") else False
            cuerpos.append(f"{ruta} | masa {m if m else 'auto (por densidad)'}{' | CINEMATICO' if cin else ''}")
        elif p.HasAPI(UsdPhysics.CollisionAPI):
            estaticos.append(ruta)
        if p.HasAPI(UsdPhysics.ArticulationRootAPI):
            robots.append(ruta)
        if p.IsA(UsdPhysics.Joint):
            joints.append(f"{ruta} [{p.GetTypeName()}]")
        if p.IsA(UsdGeom.Camera):
            f = UsdGeom.Camera(p).GetFocalLengthAttr().Get()
            camaras.append(f"{ruta} | focal {f}")
        if p.HasAPI(UsdLux.LightAPI) or "Light" in (p.GetTypeName() or ""):
            luces.append(f"{ruta} [{p.GetTypeName()}]")

    def seccion(titulo, items, maximo=40):
        out.append(f"\n{titulo} ({len(items)})")
        out.extend("  " + i for i in items[:maximo])
        if len(items) > maximo:
            out.append(f"  ... y {len(items) - maximo} mas")

    seccion("ESCENA DE FISICA", escenas_fis)
    seccion("CUERPOS RIGIDOS (se mueven con la fisica)", cuerpos)
    seccion("COLISIONADORES ESTATICOS (chocan pero no se mueven)", estaticos)
    seccion("ROBOTS / ARTICULACIONES", robots)
    seccion("JOINTS", joints)
    seccion("CAMARAS", camaras)
    seccion("LUCES", luces)
    out.append("\nPRIMS POR TIPO")
    out.extend(f"  {t}: {n}" for t, n in sorted(tipos.items(), key=lambda x: -x[1]))
    return mostrar("\n".join(out), "Escena", 1000, 750)


def ayuda():
    """Lista las herramientas disponibles."""
    fns = [actualizar, correr, mostrar, ver, archivos, guardar, diagnostico, inventario_ejemplos, inspeccionar, prims, escena, ayuda]
    out = []
    for f in fns:
        out.append(f"{f.__name__}{inspect.signature(f)}\n    {(f.__doc__ or '').strip()}")
    return mostrar("\n\n".join(out), "Ayuda: herramientas", 900, 650)


print("herramientas cargadas: escribi ayuda() para ver la lista")
