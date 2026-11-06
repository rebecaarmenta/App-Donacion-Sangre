"""Arranca la plataforma en tu computadora: python run.py  →  http://localhost:8000"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import uvicorn  # noqa: E402

if __name__ == "__main__":
    print("Abre http://localhost:8000 en tu navegador (Ctrl + C para detener)")
    uvicorn.run("donacion.main:app", host="127.0.0.1", port=8000)
