class UnauthorizedError(Exception):
    """Ошибка выдачи API."""

    pass


class InternalServerError(Exception):
    """Ошибка выдачи API."""

    pass


class NotDict(Exception):
    """Объект не является словарем."""

    pass


class FoundNot(Exception):
    """Сервер не может найти запрашиваемый ресурс."""

    pass


class NotList(Exception):
    """Объект не является списком."""

    pass


class RequestTimeout(Exception):
    """Сервер хотел бы отключить это неиспользуемое соединение."""

    pass
