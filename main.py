# Copyright (c) 2026 Roman Shevchik (octaprog7) <kolbasilyvasily@yandex.ru>
# SPDX-License-Identifier: GPL-3.0-or-later

from time import sleep
from VFDmod import VfdCustomerDisplay, SerialConn, autodetect_port

# --- Пример использования ---
if __name__ == "__main__":
    # Автопоиск порта: Linux — /dev/ttyACM*/ttyUSB*, Windows — COMx
    port = autodetect_port()

    try:
        # Текст на Русском языке, поэтому задаю кодировку явно, 
        # initialize() выберет кодировку CP866
        with VfdCustomerDisplay(SerialConn(port), encoding='cp866') as vfd:
            vfd.initialize()
            vfd.clear()

            vfd[0] = "Привет, покупатель!"  # Статичный текст (line 1)
            vfd[1] = "Сегодня скидка 100%"  # Доступ через индекс (line 2)

            # Задержка жизни скрипта, чтобы порт оставался открытым!
            print(f"Текст отправлен на {port}. Нажмите Ctrl+C для выхода...")
            while True:
                sleep(1)
    except Exception as e:
        print(f"\n[!] Ошибка: {e}")
        print("Проверьте подключение дисплея. В Linux права: группа dialout.")
