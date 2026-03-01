import os
from .files import file_exists
from .dependences import minio_dependence, ucm_vpn_dependence

settings = {
    "total_lenght" : 100,
    "centered" : 50,
    "marked" : "X",
    "obtained" : "✓"
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

def draw_dependency_line(label, dependence_obj, minio):
    linea_dep = f"Dependencia ({label}): {dependence_obj.get_info()}"
    check = f"[{settings['obtained']}]" if dependence_obj.check(minio) else "[ ]"
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

def draw_files_section(scripts_info, keys, minio_info):
    if minio_info["minio_read"]:
        show_header(" Ficheros (en MinIO) y dependencias ")
    else:
        show_header(" Ficheros y dependencias ")

    # Ficheros
    for i in range(0, len(keys), 2):
        f1 = scripts_info[keys[i]]["salida"]
        if not isinstance(f1, list):
            f1 = [f1]
        for f1_elem in f1:
            e1 = f"[{settings['obtained']}]" if file_exists(f1_elem, minio_info) else "[ ]"
            t1 = f"{e1} {f1_elem}"
            
            t2 = ""

        if i + 1 < len(keys):
            f2 = scripts_info[keys[i+1]]["salida"]
            if not isinstance(f2, list):
                f2 = [f2]
            for f2_elem in f2:
                e2 = f"[{settings['obtained']}]" if file_exists(scripts_info[keys[i+1]]["salida"], minio_info) else "[ ]"
                t2 = f"{e2} {f2_elem}"
        print(format_line_two_columns(t1, t2))
    
    show_separator()
    
    # MinIO
    m_s = f"[{settings["marked"]}]" if minio_info["minio_write"] else "[ ]"
    m_d = f"[{settings["marked"]}]" if minio_info["minio_read"] else "[ ]"
    t_s = f"{m_s} Subida de ficheros a MinIO"
    t_d = f"{m_d} Descarga de ficheros de MinIO"
    print(format_line_two_columns(t_s, t_d))
    
    seleccionados = [k for k, v in scripts_info.items() if v["usar"]]
    minio_activo = minio_info["minio_write"] or minio_info["minio_read"]

    if seleccionados or minio_activo:
        show_separator()
        
        # Dependencias de Scripts
        for k in sorted(seleccionados):
            for dep in scripts_info[k]["dependences"]:
                draw_dependency_line(k, dep, minio_info)
        
        # Dependencia de MinIO
        if minio_activo:
            draw_dependency_line("MinIO", minio_dependence, minio_info)
            if minio_dependence.check():
                draw_dependency_line("MinIO", ucm_vpn_dependence, minio_info)
        
    show_footer()

def show_menu(scripts_info, minio_info):
    os.system('cls' if os.name == 'nt' else 'clear') 
    keys = sorted(scripts_info.keys())
    
    draw_scripts_section(scripts_info, keys)
    draw_files_section(scripts_info, keys, minio_info)

    print("\nPon la letra de un fichero para seleccionarlo/quitarlo.")
    print("Pon MinioS o MinioD para activar la subida y descarga de ficheros a MinIO.")
    print("Para ejecutar lo seleccionado RUN y para salir EXIT.")