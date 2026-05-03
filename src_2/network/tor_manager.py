"""
Módulo encargado de la gestión de TOR
"""

import platform
import time
import subprocess
from psutil import process_iter
import stem.control
from stem import Signal
from src_2.config import TORRC_PATH, TOR_CONTROL_PORT

_TOR_BIN = "tor.exe" if platform.system() == "Windows" else "tor"

def _is_tor_running():
    for proc in process_iter(attrs=["name"]):
        try:
            if _TOR_BIN.lower() == proc.info["name"].lower():
                return True
        except (KeyError, AttributeError):
            continue
    return False

def start_tor():
    if _is_tor_running():
        return
    subprocess.Popen(
        [_TOR_BIN, "-f", str(TORRC_PATH)],
        stdout=subprocess.DEVNULL, 
        stderr=subprocess.DEVNULL
    )
    time.sleep(10)

def renew_tor_identity():
    try:
        with stem.control.Controller.from_port(port=TOR_CONTROL_PORT) as ctrl:
            ctrl.authenticate()
            ctrl.signal(Signal.NEWNYM)
            time.sleep(5)
            return True
    except Exception as e:
        print(f"Error al rotar IP: {e}")
        return False