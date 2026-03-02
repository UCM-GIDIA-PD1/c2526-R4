import os
import sys
import importlib

from src.utils.main_config import main_transformacion_info, main_extraccion_info
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
    scripts_info = [main_extraccion_info, main_transformacion_info]
    page = 0 # 0 --> generico | 1 --> extracción | 2 --> transformacion

    ejecutando = True
    while ejecutando:
        info_actual = scripts_info[page - 1] if page != 0 else {}
        show_menu(info_actual, page, minio_info)
        opcion = input("\nSelección > ").upper().strip()
        
        if opcion == "EXIT":
            ejecutando = False

        elif opcion in ["0", "1", "2"]:
            page = int(opcion) 

        elif page != 0:
            if opcion == "RUN":
                ejecutar_scripts(info_actual, minio_info)
            elif opcion == "MINIOS":
                minio_info["minio_write"] = not minio_info["minio_write"]
            elif opcion == "MINIOD":
                minio_info["minio_read"] = not minio_info["minio_read"]
            elif opcion in info_actual:
                info_actual[opcion]["usar"] = not info_actual[opcion]["usar"]

if __name__ == "__main__":
    main()