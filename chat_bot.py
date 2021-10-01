from vk_api.utils import get_random_id
import requests
from datetime import datetime, date
import vk_api, vk

from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import sqlite3 as sql
import time



class VkBot:
    url = "https://api.vk.com/method/"

    def __init__(self, token, token_user, group_id, server_name: str = "Empty"):
        self.params = {
            'access_token': token_user,
            'v': '5.131'}

        self.token_user = token_user
        # Даем серверу имя
        self.server_name = server_name
        # Для Long Poll
        self.vk = vk_api.VkApi(token=token)  # токен группы
        # Для вызова методов vk_api
        self.vk_api = self.vk.get_api()
        self.long_poll = VkBotLongPoll(self.vk, group_id)

    def send_msg(self, send_id, message, random_id=get_random_id()):
        """
        Отправка сообщения через метод messages.send
        :param send_id: vk id пользователя, который получит сообщение
        :param message: содержимое отправляемого письма
        :return: None
        """
        self.vk_api.messages.send(peer_id=send_id, message=message, random_id=random_id)

    """
    Метод подключение к БЛ и создания таблицы 
    """

    def get_connection(self):
        con = sql.connect('Vkinder.db')
        with con:
            cur = con.cursor()
            cur.execute("""CREATE TABLE IF NOT EXISTS Users_vk (
                        Id INTEGER  PRIMARY KEY AUTOINCREMENT NOT NULL,
                        Id_User INTEGER,
                        Id_half_user INTEGER);""")
            con.commit()
        return con

    """
    Мето проверки пользователя в БД для уникальности
    """

    def check_user_db(self, user_id, id_half):
        connection = self.get_connection()
        with connection:
            sql_query = """SELECT * FROM Users_vk WHERE Id_User = ? AND Id_half_user = ? """
        return connection.execute(sql_query, (user_id, id_half))

    """  ЗАПУСК БОТА   """

    def start(self):
        print(f" Чат Бот запущет успешно !")
        """ Подключение базы данных """
        connection = self.get_connection()
        # Слушаем сервер
        for event in self.long_poll.listen():
            # Пришло новое сообщение
            if event.type == VkBotEventType.MESSAGE_NEW:
                user_id = event.object.message['from_id']
                """ Метод поиска информации пользователя """
                result_info_user = get_user_info(self, user_id)

                self.send_msg(user_id,
                              f"Привет {result_info_user['first_name']}, \nЯ чат-бот VKinder  ищу подходящих людей в ВК для \
                                  знакомства и общение.\n Идет поиск ...")

                result_half_users = get_your_half(self, self.token_user, result_info_user)
                [print(value) for key, value in result_half_users.items()]

                if result_half_users:
                    self.vk_api.messages.send(user_id=user_id, random_id=get_random_id(),
                                              message=f" Возможно ваша вторая половинка может быть среди этих людей:\n")
                else:
                    self.vk_api.messages.send(user_id=user_id, random_id=get_random_id(),
                                              message=f" Ничего не найдено :\n")

                for user_key, user_value in result_half_users.items():
                    """ Записываем в БД данные """
                    with connection:
                        connection.execute(
                            f"INSERT INTO Users_vk (Id_User, Id_half_user) values ({user_id},{user_key})")
                        connection.commit()

                    self.vk_api.messages.send(user_id=user_id,
                                              random_id=get_random_id(),
                                              message=f"ID пользователя: {user_value['id']} \n"
                                                          f"Имя: {user_value['first_name']} \n"
                                                          f"Фамилия: {user_value['last_name']} \n"
                                                          f"Пол: {user_value['sex']} \n"
                                                          f"Возвраст: {user_value['age']} \n"
                                                          f"Город: {user_value['city']} \n"
                                                          f"Фото: {user_value['photo_400']} \n")



"""
Метод для поиска информации пользователя для которого ищем собеседников
"""


def get_user_info(self, user_id):
    result = {}
    """ Получаем все данные пользователя"""
    users_get_url = self.url + "users.get"
    users_params = {'user_id': user_id,
                    'fields': 'first_name, last_name, bdate, sex, relation, city'
                    }
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain', 'Content-Encoding': 'utf-8'}
    list_keys = ['id', 'first_name', 'last_name', 'bdate', 'sex', 'relation', 'city']
    res = requests.get(users_get_url, params={**self.params, **users_params}, headers=headers).json()
    for key, value in res['response'][0].items():
        if key in list_keys:
            if key == 'city':
                result[key] = str(value['id'])
            elif key == 'bdate':
                now = date.today().year
                age = now - (datetime.strptime(value, '%d.%m.%Y').year)
                result['age'] = age
            else:
                result[key] = value
    return result


"""
 Метод для поиска пары или собеседника в серивие ВК
 """


def get_your_half(self, token_user, result_info_user):
    result_half = {}
    list_keys = ['id', 'first_name', 'last_name', 'bdate', 'sex', 'relation', 'city', 'photo_400']
    session = vk.Session(access_token=token_user)
    vkapi = vk.API(session, v='5.131')
    count_offset = 0

    while len(result_half) < 5:

        result = vkapi.users.search(q='', sex=[1 if result_info_user['sex'] == 2 else 2],
                                    relation=6,
                                    city=int(result_info_user['city']),
                                    age_from=result_info_user['age'] - 5,
                                    age_to=result_info_user['age'] + 3,
                                    count=5, offset=count_offset,
                                    fields='domain, sex, bdate, relation, city, photo_400')['items']

        for user in result:
            user_id = result_info_user['id']
            user_id_half = user['id']
            new_dic_2 = {}
            """ проверяем пользователей если они уже есть в БД """
            result_check_db = self.check_user_db(user_id, user_id_half).fetchall()

            if len(result_check_db) == 1:
                pass
            else:
                for key, values in user.items():
                    if key in list_keys:
                        if key == 'city':
                           if values['id'] == int(result_info_user['city']):
                              new_dic_2[key] = str(values['title'])
                           else:
                              new_dic_2 = {}
                              break
                        elif key == 'bdate':
                            try:
                                now = date.today().year
                                age = now - (datetime.strptime(values, '%d.%m.%Y').year)
                                new_dic_2['age'] = age
                            except Exception:
                                new_dic_2 = {}
                                break
                        elif key == 'relation':
                            if values == 1 or values == 6:
                                new_dic_2[key] = values
                            else:
                                continue
                        else:
                            new_dic_2[key] = values

                if len(new_dic_2) == 7:
                    result_half[user_id_half] = new_dic_2
                else:
                    pass
            if len(result_half) == 5: break
        count_offset += 5
        time.sleep(2)
    return result_half

