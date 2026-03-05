import pymysql

try:
    # Пробуем подключиться без пароля (для XAMPP)
    connection = pymysql.connect(
        host='localhost',
        user='root',
        password='',  # пустой пароль для XAMPP
        database='RailwayTickets'
    )
    print("✅ Подключение успешно с пустым паролем!")
    connection.close()
except Exception as e:
    print(f"❌ Ошибка с пустым паролем: {e}")

    try:
        # Пробуем с паролем (если вы его устанавливали)
        connection = pymysql.connect(
            host='localhost',
            user='root',
            password='UM8$7I9o',  # замените на ваш пароль
            database='RailwayTickets'
        )
        print("✅ Подключение успешно с паролем!")
        connection.close()
    except Exception as e:
        print(f"❌ Ошибка с паролем: {e}")