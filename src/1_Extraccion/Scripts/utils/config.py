import os
from files import read_file, write_to_file

def _get_identif_range(lenght, identif):
    """Devuelve el rango del apps a procesar"""
    # procesar todos los appids
    if identif is None:
        return 0, lenght-1
    
    assert identif.isdigit(), f"Error: El identificador no es un entero válido (valor actual: {identif})."
    int_identif = int(identif)
    assert 1 <= int_identif <= 6, f"El identificador debe estar entre 1 y 6 (valor actual: {identif})."

    bloque = lenght // 6
    inicio = (int_identif - 1) * bloque

    if int_identif == 6:
        fin = lenght - 1
    else:
        fin = (int_identif * bloque) - 1

    return inicio, fin
    

def get_appid_range(config_path, lenght, identif):
    """Lee el inicio y fin de una sesión de scrapping desde un archivo de texto
    Los indices que se guardan corresponden a los de una lista, no corresponden con un appid concreto
    Si no existe el archivo se asigna la parte correspondiente a identif

    Args:
        ruta_txt: ruta del fichero de texto. Debe contener los datos en formato: 'index_inicial,index_final'
        identif: Parte de los datos que se va a extraer
        longitud: Numero de elementos del archivo
    
    Returns:
        Tupla de enteros con los valores de inicio y fin
    """

    # Si existe archivo 
    if os.path.exists(config_path):
        try:
            content = read_file(config_path)
            partes = content.strip().split(",")
            return min(int(partes[0]), lenght), min(int(partes[1]), lenght-1)
        except Exception as e:
            print(f"Error leyendo txt: {e}. Se usarán valores por defecto.")
            return 1, 0
    
    #si no existe archivo
    start_idx, end_idx = _get_identif_range(lenght, identif)
    write_to_file(f"{start_idx},{end_idx}",config_path)      
    return start_idx, end_idx

