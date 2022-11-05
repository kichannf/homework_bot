from http import HTTPStatus
import logging
import os
import sys
import time

import requests

from telegram import Bot
import telegram
from exceptions import *

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s, %(levelname)s, %(message)s, %(name)s')

handler.setFormatter(formatter)
logger.addHandler(handler)


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message
    )
    logger.info(f'Сообщение "{message}" успешно отправлено.')


def send_message_about_error(bot, message):
    bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message
    )


def get_api_answer(current_timestamp):
    """Запрос к АПИ Яндекса"""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code == HTTPStatus.UNAUTHORIZED:
        raise UnauthorizedError('Ошибка авторизации. Ошибка в токене')
    if response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR:
        raise InternalServerError('Внутренняя ошибка сервера')
    if response.status_code == HTTPStatus.NOT_FOUND:
        raise FoundNot('Сервер не может найти запрашиваемый ресурс.')
    if response.status_code == HTTPStatus.REQUEST_TIMEOUT:
        raise RequestTimeout ('Сервер хотел бы отключить это неиспользуемое соединение')
    homeworks = response.json()
    return homeworks


def check_response(response):
    """Проверка ответа API на корректность"""
    """Если ответ API соответствует ожиданиям, возвращает список ДР"""
    if not isinstance(response, dict):
        raise NotDict('Объект не является словарем')
    if 'homeworks' not in response:
        raise KeyError ('Ошибка доступа по ключу "homeworks"')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise NotList('Объект не является списком')
    return homeworks
    

def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе статус этой работы."""
    """В случае успеха, функция возвращает статус проверки работы"""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения,"""
    """которые необходимы для работы программы"""
    environment_variables = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    if not all(environment_variables):
            return False
    return True


def main():
    """Основная логика работы бота."""
    if check_tokens() == False:
        logger.critical('Потеряли переменную окружения')
        sys.exit()
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time()) - 3600
    homework_status = ''
    # Проверка о срабатывание исключение и отправлении ошибки
    error_check = False

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            message_result = parse_status(homework[0])
            if message_result == homework_status:
                logger.debug(f'Статус проверки не изменен')
                continue
            homework_status = message_result
            send_message(bot, message_result)
            logger.info('Сообщение отправлено')
            
        except UnauthorizedError:
            if error_check == False:
                error_check = True
                logger.error('Ошибка авторизации. Ошибка в токене.')
                send_message_about_error(bot, 'Ошибка авторизации. Ошибка в токене')
        except InternalServerError:
            if error_check == False:
                error_check = True
                send_message_about_error(bot, 'Внутренняя ошибка сервера.')
                logger.error('Внутренняя ошибка сервера')
        except FoundNot:
            if error_check == False:
                error_check = True
                send_message_about_error(bot, 'Сервер не может найти запрашиваемый ресурс')
                logger.error('Сервер не может найти запрашиваемый ресурс')
        except NotDict:
            if error_check == False:
                error_check = True
                send_message_about_error(bot, 'Объект не является словарем')
                logger.error('Ошибка получения статуса Домашней Работы')
        except NotList:
            if error_check == False:
                error_check = True
                send_message_about_error(bot, 'Объект не является списком')
                logger.error('Ошибка получения статуса Домашней Работы')
        except KeyError:
            logger.error('Ошибка обращения по ключу')
            if error_check == False:
                error_check = True
                send_message_about_error(bot, 'Ошибка обращения по ключу.')
        except IndexError:
            logger.error('В данный момент нет домашних работ на проверке')
            if error_check == False:
                error_check = True
                send_message_about_error(bot, 'В данный момент нет домашних работ на проверке.')
        except telegram.error.BadRequest:
            logger.error('Ошибка обработки запроса. Проверь ID клиента')
        except telegram.error.Unauthorized:
            logger.error('Ошибка телеграмм токена получателя')

        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
