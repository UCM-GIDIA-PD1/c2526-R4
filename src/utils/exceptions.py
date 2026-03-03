"""
Módulo de excepciones del proyecto.
"""

# Excepción base del proyecto
class BaseProjectException(Exception):
    """Excepcion base para el proyecto"""
    pass

# Excepciones reservadas para la API Web de Steam
class SteamAPIException(BaseProjectException):
    """Exceptiones relacionadas con steam"""
    def __init__(self, message, appid=None):
        super().__init__(message)
        self.appid = appid
    
# Excepciones específicas de Appdetails y Reviewhistogram
class AppdetailsException(SteamAPIException):
    """Exceptiones producidas durante la extraccion de appdetails"""
    pass

class ReviewhistogramException(SteamAPIException):
    """Exceptiones producidas durante la extraccion de appreviewhistogram"""
    pass