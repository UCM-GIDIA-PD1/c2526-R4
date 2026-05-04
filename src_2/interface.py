"""
Módulo para manejar la interacción con el usuario
"""

def handle_input(initial_message, isResponseValid = lambda x: True):
    respuesta = input(initial_message).strip()
    while not isResponseValid(respuesta):
        respuesta = input("Opción no válida, prueba de nuevo: ").strip()
    return respuesta