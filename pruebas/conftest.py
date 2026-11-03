"""Configuracion de pytest para las pruebas de celda/ en la PC.

Correr desde la raiz del repo (con numpy y pytest instalados en cualquier entorno):
    python -m pytest pruebas -q

Los URDF de Dobot se bajan una sola vez a .cache/robots/ (esta en .gitignore).
Estas pruebas no usan Isaac Sim. pruebas/probar_herramientas.py es otra cosa: corre en la maquina.
"""
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from celda import datos  # noqa: E402

CACHE = os.path.join(REPO, ".cache", "robots")


@pytest.fixture(scope="session")
def celda():
    """(D, S) de fase1/celda.json."""
    return datos.cargar()


@pytest.fixture(scope="session")
def robots(celda):
    """{"cr20a": robot, "cr6al": robot} con cadena, base, largo y eje (ver celda.datos.robot)."""
    D, S = celda
    return {c: datos.robot(D, S, c, CACHE) for c in ("cr20a", "cr6al")}
