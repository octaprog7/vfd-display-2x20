from time import sleep
from VFDmod import VfdCustomerDisplay, SerialConn

# --- Пример использования ---
if __name__ == "__main__":
    # На Debian USB-дисплеи часто садятся на /dev/ttyACM0
    port = '/dev/ttyUSB0'

    try:
        with VfdCustomerDisplay(SerialConn(port)) as vfd:
            vfd.initialize()
            vfd.clear()

            vfd[0] = "Привет, покупатель!"  # Статичный текст (line 1)
            vfd[1] = "Сегодня скидка 100%"  # Доступ через индекс (line 2)

            # Задержка жизни скрипта, чтобы порт оставался открытым!
            print("Текст отправлен. Нажмите Ctrl+C для выхода...")
            while True:
                sleep(1)
    except Exception as e:
        print(f"\n[!] Ошибка: {e}")
        print("Проверьте подключение кабеля и права доступа (группа dialout).")
