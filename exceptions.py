class UniqueException(Exception):
    """Родительский класс пользовательских."""

    pass


class UnauthorizedError(UniqueException):
    """Ошибка выдачи API."""

    pass


class InternalServerError(UniqueException):
    """Ошибка выдачи API."""

    pass


class NotDict(UniqueException):
    """Объект не является словарем."""

    pass


class FoundNot(UniqueException):
    """Сервер не может найти запрашиваемый ресурс."""

    pass


class NotList(UniqueException):
    """Объект не является списком."""

    pass


class RequestTimeout(UniqueException):
    """Сервер хотел бы отключить это неиспользуемое соединение."""

    pass
