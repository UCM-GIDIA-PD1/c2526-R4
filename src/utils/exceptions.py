class BaseProjectException(Exception):
    """Excepcion base para el proyecto"""
    pass


class SteamAPIException(BaseProjectException):
    """Exceptiones relacionadas con steam"""
    def __init__(self, message, appid=None):
        super().__init__(message)
        self.appid = appid
    

class AppdetailsException(SteamAPIException):
    """Exceptiones producidas durante la extraccion de appdetails"""
    pass

class ReviewhistogramException(SteamAPIException):
    """Exceptiones producidas durante la extraccion de appreviewhistogram"""
    pass

class YoutubeQuotaExceeded(BaseProjectException):
    ''' Excepciones producidas por limitación de quota con la API de Youtube'''
    def __init__(self, message, appid=None):
        super().__init__(message)
        self.appid = appid