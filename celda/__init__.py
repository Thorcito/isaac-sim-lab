"""Logica de la celda, sin Isaac Sim.

Regla de este paquete: solo biblioteca estandar de Python y numpy. Nada de isaacsim, omni
ni pxr. Asi cada modulo se prueba en la PC con pytest (pruebas/test_*.py) y tambien se
carga en la maquina de Isaac sin pip.

Los scripts de faseN/ son los ADAPTADORES: leen celda.json, llaman a estas funciones y
traducen el resultado a la escena (prims, joints, ventosas, camara).

En la maquina, con las herramientas cargadas:
    usar_celda()
    from celda import recetas
"""
