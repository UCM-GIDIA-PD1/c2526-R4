"""
Módulo para manejar la interacción con el usuario
"""

def handle_input(initial_message, isResponseValid = lambda x: True):
    """
    Gestiona la entrada de usuario por consola con validación personalizada.

    Args:
        initial_message: Mensaje inicial que se muestra al usuario.
        is_response_valid: Función que devuelve un booleano indicando si la entrada es válida.

    Returns:
        str: Cadena de texto validada introducida por el usuario.
    """
    
    response = input(initial_message).strip()
    while not isResponseValid(response):
        response = input("Opción no válida, prueba de nuevo: ").strip()
    return response