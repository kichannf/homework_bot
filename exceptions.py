class UnauthorizedError(Exception):
    """Ошибка выдачи API"""


class InternalServerError(Exception):
    """Ошибка выдачи API"""


class NotDict(Exception):
    '''Объект не является словарем'''


class FoundNot(Exception):
    """Сервер не может найти запрашиваемый ресурс"""


class NotList(Exception):
    '''Объект не является списком'''


class RequestTimeout(Exception):
    """Сервер хотел бы отключить это неиспользуемое соединение"""