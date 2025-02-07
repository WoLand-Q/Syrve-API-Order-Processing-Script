import requests
import json
from collections import Counter
import re
from datetime import datetime
import pprint

# Функция для получения токена доступа
def get_access_token(api_login):
    url = "https://api-eu.syrve.live/api/1/access_token"
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "apiLogin": api_login
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        token = data.get('token')
        if not token:
            print("Не удалось получить токен из ответа.")
            return None
        print(f"Получен токен доступа: {token}")
        return token
    except requests.HTTPError as http_err:
        print(f"HTTP ошибка: {http_err} - Ответ: {response.text}")
    except Exception as err:
        print(f"Произошла ошибка: {err}")
    return None

# Функция для получения списка организаций
def get_organizations(token):
    url = "https://api-eu.syrve.live/api/1/organizations"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        organizations = data.get('organizations', [])
        print(f"Получено организаций: {len(organizations)}")
        return organizations
    except requests.HTTPError as http_err:
        print(f"HTTP ошибка: {http_err} - Ответ: {response.text}")
    except Exception as err:
        print(f"Произошла ошибка: {err}")
    return None

# Функция для получения доставок по дате и статусу
def get_deliveries(token, organization_ids, date_from, date_to):
    url = "https://api-eu.syrve.live/api/1/deliveries/by_delivery_date_and_status"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "organizationIds": organization_ids,
        "deliveryDateFrom": date_from,
        "deliveryDateTo": date_to,
        "statuses": ["Closed"],
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        # Инициализируем пустой список для заказов
        orders = []

        # Извлекаем заказы из 'ordersByOrganizations'
        orders_by_orgs = data.get('ordersByOrganizations', [])
        for org_orders in orders_by_orgs:
            org_id = org_orders.get('organizationId')
            org_orders_list = org_orders.get('orders', [])
            orders.extend(org_orders_list)

        print(f"Получено заказов: {len(orders)}")

        # Печатаем ВСЕ заказы в консоль (через pprint)
        if orders:
            print("\nВсе заказы:")
            for idx, order_data in enumerate(orders, 1):
                print(f"\n--- Заказ #{idx} ---")
                pprint.pprint(order_data)

        return orders
    except requests.HTTPError as http_err:
        print(f"HTTP ошибка: {http_err} - Ответ: {response.text}")
    except Exception as err:
        print(f"Произошла ошибка: {err}")
    return None

# Функция для обработки заказов
def process_orders(orders):
    phone_numbers = []
    total_orders = len(orders)
    no_customer_data_count = 0
    no_phone_number_count = 0
    invalid_phone_number_count = 0
    zero_amount_count = 0

    # Паттерн для проверки номера телефона (обновленный)
    phone_pattern = re.compile(r"^\+380(39|50|63|66|67|68|73|91|92|93|95|96|97|98|99)(?!0000000|1111111|2222222|3333333|4444444|5555555|6666666|7777777|8888888|9999999)\d{7}$")

    for order_wrapper in orders:
        # Проверяем, что есть ключ 'order'
        order = order_wrapper.get('order')
        if not order:
            continue  # Если нет данных о заказе, переходим к следующему

        # Проверка данных заказчика
        customer = order.get('customer')
        if not customer:
            no_customer_data_count += 1
            continue  # Переход к следующему заказу

        # Получение номера телефона
        phone = order.get('phone')
        if not phone:
            no_phone_number_count += 1
            continue

        phone_numbers.append(phone)

        # Проверка валидности номера телефона
        if not phone_pattern.match(phone):
            invalid_phone_number_count += 1

        # Проверка суммы заказа
        total_price = order.get('sum', 0)
        if total_price == 0:
            zero_amount_count += 1

    # Подсчет дубликатов
    phone_counts = Counter(phone_numbers)
    duplicate_phones = {phone: count for phone, count in phone_counts.items() if count > 1}

    # Вывод результатов
    print(f"Общее количество заказов: {total_orders}")
    print(f"Заказы без данных заказчика: {no_customer_data_count}")
    print(f"Заказы без номера телефона: {no_phone_number_count}")
    print(f"Заказы с некорректным номером телефона: {invalid_phone_number_count}")
    print(f"Заказы с нулевой суммой: {zero_amount_count}")

    print("\nДубликаты номеров телефонов:")
    for phone, count in duplicate_phones.items():
        print(f"{phone}: {count} раз(а)")

def main():
    api_login = "ВАШ_API_ЛОГИН"
    date_from = "2025-02-05 00:00:00.000"
    date_to = "2025-02-05 23:59:59.999"

    # Получение токена доступа
    token = get_access_token(api_login)
    if not token:
        print("Не удалось получить токен доступа.")
        return

    # Получение списка организаций
    organizations = get_organizations(token)
    if not organizations:
        print("Не удалось получить список организаций.")
        return

    # Вывод списка организаций
    print("Список доступных организаций:")
    for idx, org in enumerate(organizations, 1):
        print(f"{idx}. {org.get('name')} (ID: {org.get('id')})")

    # Запрос выбора организаций
    print("Введите номера организаций, для которых нужно получить заказы (через запятую), или '0' для выбора всех:")
    selected_indices = input()

    if selected_indices.strip() == '0':
        # Выбраны все организации
        organization_ids = [org.get('id') for org in organizations if 'id' in org]
    else:
        try:
            # Парсим введенные номера
            indices = [int(i.strip()) for i in selected_indices.split(',')]
            # Проверяем корректность номеров
            if any(i < 1 or i > len(organizations) for i in indices):
                print("Пожалуйста, введите корректные номера организаций.")
                return
            # Получаем выбранные organization_ids
            organization_ids = [organizations[i-1].get('id') for i in indices]
        except ValueError:
            print("Пожалуйста, введите номера организаций через запятую.")
            return

    # Проверка полученных идентификаторов организаций
    print(f"Идентификаторы выбранных организаций: {organization_ids}")

    # Получение доставок
    orders = get_deliveries(token, organization_ids, date_from, date_to)
    if not orders:
        print("Не найдено заказов или произошла ошибка при получении заказов.")
        return

    # Обработка заказов
    process_orders(orders)

if __name__ == "__main__":
    main()
