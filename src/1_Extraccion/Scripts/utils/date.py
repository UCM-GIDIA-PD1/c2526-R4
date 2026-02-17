from datetime import datetime
def unix_to_date_string(timestamp):
    """
    Convierte un timestamp Unix a formato YYYY-MM-DD
    
    Args:
        timestamp (int): Timestamp Unix
    
    Returns:
        str: Fecha en formato YYYY-MM-DD
    """
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime('%Y-%m-%d')

def format_date_string(date_str):
    """
    Convierte fechas de Steam a formato 'YYYY-MM-DD'.
    Soporta múltiples formatos.

    Args:
        fecha_str (str): Fecha en formato 'DD Mon, YYYY'.

    Returns:
        str | None: La fecha en formato RFC 3339 ('YYYY-MM-DD')
        Retorna None si la fecha no se carga correctamente.
    """
    try:
        dt = datetime.strptime(date_str, "%d %b, %Y")
        return dt.strftime("%Y-%m-%d")

    except ValueError:
        return None

    