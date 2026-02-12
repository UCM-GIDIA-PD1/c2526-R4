import os
import sys

# Para que pueda usar los ficheros importados que están dentro de Scripts (Z_funciones)
sys.path.append(os.path.join(os.path.dirname(__file__), "Scripts"))

import Scripts.A_lista_juegos
import Scripts.B_informacion_juegos
import Scripts.C1_informacion_youtube_busquedas
import Scripts.C2_informacion_youtube_videos
import Scripts.D_informacion_resenyas
import Scripts.E_metadatos_imagenes

scripts_info = {
    "A": {
        "fichero": "A_lista_juegos", 
        "salida": "steam_apps.json.gz",
        "ejecutable": Scripts.A_lista_juegos.A_lista_juegos,
        "usar": False
    },
    "B": {
        "fichero": "B_informacion_juegos", 
        "salida": "info_steam_games.json.gz",
        "ejecutable": Scripts.B_informacion_juegos.B_informacion_juegos,
        "usar": False
    },
    "C1": {
        "fichero": "C1_informacion_youtube_busquedas", 
        "salida": "info_steam_youtube_1.json.gz",
        "ejecutable": Scripts.C1_informacion_youtube_busquedas.C1_informacion_youtube_busquedas,
        "usar": False
    },
    "C2": {
        "fichero": "C2_informacion_youtube_videos", 
        "salida": "info_steam_games_and_youtube.json.gz",
        "ejecutable": Scripts.C2_informacion_youtube_videos.C2_informacion_youtube_videos,
        "usar": False
    },
    "D": {
        "fichero": "D_informacion_resenyas", 
        "salida": "info_steam_resenyas.json.gz",
        "ejecutable": Scripts.D_informacion_resenyas.D_informacion_resenyas,
        "usar": False
    },
    "E": {
        "fichero": "E_metadatos_imagenes", 
        "salida": "info_imagenes.json.gz",
        "ejecutable": Scripts.E_metadatos_imagenes.E_metadatos_imagenes,
        "usar": False
    }
}

def mostrar_menu():
    os.system('cls' if os.name == 'nt' else 'clear') # Para limpiar la consola
    print(f"{'DOCUMENTOS':<45} {'FICHEROS':<40} {'EXISTE'}")
    print("▃" * 100)
    
    for key in sorted(scripts_info.keys()):
        info = scripts_info[key]
        marca_uso = "[X]" if info["usar"] else "[ ]"
        nombre_script = info["fichero"]
        fichero_salida = info["salida"]
        
        # Comprobación de ficheros
        ruta_fichero = os.path.join("data", fichero_salida)
        existe = "[✔]" if os.path.exists(ruta_fichero) else "[ ]"
        
        print(f"{key:<3}) {marca_uso} {nombre_script:<37} {fichero_salida:<38} {existe}")
    
    print("▃" * 100)
    print("Pon la letra de un fichero para seleccionarlo/quitarlo. Para ejecutar lo seleccionado RUN y para salir EXIT")

def ejecutar_scripts():
    print("\n--- INICIANDO EJECUCIÓN ---")
    alguno_ejecutado = False

    for clave, info in sorted(scripts_info.items()):
        if info["usar"]:
            print(f">> Ejecutando {clave}: {info['fichero']}...")
            info["ejecutable"]()
            alguno_ejecutado = True
    
    if not alguno_ejecutado:
        print("No hay ningún script seleccionado para ejecutar.")
    
    input("\nProceso terminado. Presiona Enter para volver al menú.")

def main():
    while True:
        mostrar_menu()
        opcion = input("\nSelección > ").upper().strip()
        
        if opcion == "EXIT":
            break
        elif opcion == "RUN":
            ejecutar_scripts()
        elif opcion in scripts_info:
            scripts_info[opcion]["usar"] = not scripts_info[opcion]["usar"]

if __name__ == "__main__":
    main()