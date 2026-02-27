import os
import sys
import importlib

from src.utils.main_config import main_scripts_info
from src.utils.visuals import show_menu
from src.utils.dependences import minio_dependence

# Para que pueda usar los ficheros importados que están dentro de Scripts
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, "1_Extraccion"))

def ejecutar_scripts(scripts_info, minio_info):
    print("\n--- INICIANDO EJECUCIÓN ---")

    for clave, info in sorted(scripts_info.items()):
        if info["usar"]:
            print(f">> Importando y ejecutando {clave}: {info['fichero']}...")
            modulo = importlib.import_module(f"{info['fichero']}")
            funcion = getattr(modulo, info["ejecutable"])
            minio = minio_info if minio_dependence.check(minio_info) else {"minio_write": False, "minio_read": False}
            funcion(minio)
            info["usar"] = False

    input("\nProceso terminado. Presiona Enter para volver al menú.")

def main():
    minio_info = {"minio_write": False, "minio_read": False}
    scripts_info = main_scripts_info

    ejecutando = True  

    while ejecutando:
        show_menu(scripts_info, minio_info)
        opcion = input("\nSelección > ").upper().strip()
        
        if opcion == "EXIT":
            ejecutando = False
        elif opcion == "RUN":
            ejecutar_scripts(scripts_info, minio_info)
        elif opcion == "MINIOS":
            minio_info["minio_write"] = not minio_info["minio_write"]
        elif opcion == "MINIOD":
            minio_info["minio_read"] = not minio_info["minio_read"]
        elif opcion in scripts_info:
            scripts_info[opcion]["usar"] = not scripts_info[opcion]["usar"]

if __name__ == "__main__":
    main()