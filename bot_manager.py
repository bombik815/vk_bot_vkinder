# Импортируем созданный нами класс VkBot
from chat_bot import VkBot
# Получаем из config.py наш api-token

# vk_api_token - API токен, который вы ранее создали
# 172998024 - id сообщества-бота
token_user = input("Ведите ваш API-токен пользователя созданный ранее: ")
group_id = input("Введите ID вашей группы: ")
token = input("Ведите  API-токен сообщества созданный ранее: ")
VKinder = VkBot(token, token_user, group_id, "VKinder")


if __name__ == '__main__':
    VKinder.start()

