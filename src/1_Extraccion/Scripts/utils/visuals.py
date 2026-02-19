import os
from Scripts.utils.config import appidlist_file, gamelist_file, youtube_scraping_file


settings = {
    "total_lenght" : 100,
    "centered" : 50,
    "marked" : "X",
    "obtained" : "✔"
}

def show_header(title):
    print("╔" + "═" * (settings["total_lenght"] - 2) + "╗")
    print("║" + title.center(settings["total_lenght"] - 2) + "║")
    print("╠" + "═" * (settings["total_lenght"] - 2) + "╣")

def show_footer():
    print("╚" + "═" * (settings["total_lenght"] - 2) + "╝")

def show_separator():
    print("║ " + "-" * (settings["total_lenght"] - 4) + " ║")

def format_line_two_columns(left_text, right_text):
    linea = "║ " + left_text.ljust(settings["centered"] - 2)
    linea += right_text.ljust(settings["total_lenght"] - settings["centered"] - 1) + "║"
    return linea

def draw_dependency_line(label, dependence_obj):
    linea_dep = f"Dependencia ({label}): {dependence_obj.get_info()}"
    check = f"[{settings['obtained']}]" if dependence_obj.check() else "[ ]"
    print("║ " + linea_dep.ljust(settings["total_lenght"] - 10) + check.rjust(6) + " ║")

def draw_scripts_section(scripts_info, keys):
    show_header(" Documentos a ejecutar ")
    for i in range(0, len(keys), 2):
        k1 = keys[i]
        m1 = f"[{settings['marked']}]" if scripts_info[k1]["usar"] else "[ ]"
        t1 = f"{k1:<2}) {m1} {scripts_info[k1]['fichero']}"
        
        t2 = ""
        if i + 1 < len(keys):
            k2 = keys[i+1]
            m2 = f"[{settings['marked']}]" if scripts_info[k2]["usar"] else "[ ]"
            t2 = f"{k2:<2}) {m2} {scripts_info[k2]['fichero']}"
            
        print(format_line_two_columns(t1, t2))
    show_footer()

def draw_files_ection(scripts_info, keys, minio_info):
    show_header(" Ficheros y dependencias ")
    
    # Ficheros
    for i in range(0, len(keys), 2):
        f1 = scripts_info[keys[i]]["salida"]
        e1 = f"[{settings['obtained']}]" if os.path.exists(os.path.join("data", f1)) else "[ ]"
        t1 = f"{e1} {f1}"
        
        t2 = ""
        if i + 1 < len(keys):
            f2 = scripts_info[keys[i+1]]["salida"]
            e2 = f"[{settings['obtained']}]" if os.path.exists(os.path.join("data", f2)) else "[ ]"
            t2 = f"{e2} {f2}"
        print(format_line_two_columns(t1, t2))
    
    show_separator()
    
    # MinIO
    m_s = f"[{settings['marked']}]" if minio_info["minio_upload"] else "[ ]"
    m_d = f"[{settings['marked']}]" if minio_info["minio_download"] else "[ ]"
    t_s = f"{m_s} Subida de ficheros a MinIO"
    t_d = f"{m_d} Descarga de ficheros de MinIO"
    print(format_line_two_columns(t_s, t_d))
    
    seleccionados = [k for k, v in scripts_info.items() if v["usar"]]
    minio_activo = minio_info["minio_upload"] or minio_info["minio_download"]

    if seleccionados or minio_activo:
        show_separator()
        
        # Dependencias de Scripts
        for k in sorted(seleccionados):
            for dep in scripts_info[k]["dependences"]:
                draw_dependency_line(k, dep)
        
        # Dependencia de MinIO
        if minio_activo:
            draw_dependency_line("MinIO", minio_dependence)
        
    show_footer()

def show_menu(scripts_info, minio_info):
    os.system('cls' if os.name == 'nt' else 'clear') 
    keys = sorted(scripts_info.keys())
    
    draw_scripts_section(scripts_info, keys)
    draw_files_ection(scripts_info, keys, minio_info)

    print("\nPon la letra de un fichero para seleccionarlo/quitarlo.")
    print("Pon MinioS o MinioD para activar la subida y descarga de ficheros a MinIO.")
    print("Para ejecutar lo seleccionado RUN y para salir EXIT.")


# DEPENDENCIAS

class appidlist_file_dependence():
    def get_info():
        return f"Fichero {appidlist_file.name} (script A)"
    
    def check():
        return appidlist_file.exists()
    
class gamelist_file_dependence():
    def get_info():
        return f"Fichero {gamelist_file.name} (script B)"
    
    def check():
        return gamelist_file.exists()

class youtube_scraping_file_dependence():
    def get_info():
        return f"Fichero {youtube_scraping_file.name} (script C1)"
    
    def check():
        return youtube_scraping_file.exists()
    
class steam_api_dependence():
    def get_info():
        return "API de Steam"
    
    def check():
        API_KEY = os.environ.get("STEAM_API_KEY")
        if API_KEY is None:
            return False
        else:
            return True

class youtube_api_dependence():
    def get_info():
        return "API de YouTube"
    
    def check():
        API_KEY = os.environ.get("API_KEY_YT")
        if API_KEY is None:
            return False
        else:
            return True
    
class minio_dependence():
    def get_info():
        return "Claves (de acceso y secreta) de MinIO"
    
    def check():
        API_KEY1 = os.environ.get("MINIO_ACCESS_KEY")
        API_KEY2 = os.environ.get("MINIO_SECRET_KEY")
        if API_KEY1 is None or API_KEY2 is None:
            return False
        else:
            return True