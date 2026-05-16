# import sys
from time import sleep
from VFDmod import VfdCustomerDisplay, SerialConn


def run_diagnostic(vfd: VfdCustomerDisplay):
    print("--- Запуск диагностики EPSON совместимого дисплея покупателя ---")

    # 1. Проверка инициализации
    print("[1/5] Инициализация...")
    vfd.initialize()
    vfd.clear()
    vfd[0] = "SYSTEM CHECK..."
    vfd[1] = "INITIALIZING..."
    sleep(1.5)

    # 2. Тест "Шахматка" (проверка всех сегментов VFD)
    print("[2/5] Тест сегментов (заливка)...")
    # Код 0xDB — это закрашенный прямоугольник в CP866
    full_block = bytes([0xDB]).decode('cp866')
    vfd[0] = full_block * 20
    vfd[1] = full_block * 20
    sleep(2)
    vfd.clear()

    # 3. Тест кириллицы
    print("[3/5] Тест кириллицы...")
    vfd[0] = "АБВГДЕЖЗИЙКЛМНОПРСТУ"
    vfd[1] = "ФХЦЧШЩЪЫЬЭЮЯ абвгдеё"
    sleep(3)

    # 4. Тест позиционирования (0-base индексы)
    print("[4/5] Тест позиционирования (точка)...")
    vfd.clear()
    for row_idx in [0, 1]:
        for col in range(1, 21):
            vfd.set_cursor(col, row_idx + 1)
            vfd.write(b".")
            sleep(0.05)
    sleep(1)

    # 5. Завершение тестов
    try:
        vfd.clear()
        vfd[0] = "ТЕСТ ЗАВЕРШЕН УСПЕШНО!"
        vfd[1] = "ДИСПЛЕЙ ГОТОВ К РАБОТЕ!"
        sleep(1.5)
    except KeyboardInterrupt:
        vfd.clear()
        print("\nДиагностика завершена.")


if __name__ == "__main__":
    # На Debian USB-дисплеи часто садятся на /dev/ttyACM0
    PORT = '/dev/ttyUSB0'

    try:
        # Передаю SerialConn в конструктор дисплея
        with VfdCustomerDisplay(SerialConn(PORT)) as display:
            run_diagnostic(display)
    except Exception as e:
        print(f"\n[!] Ошибка: {e}")
        print("Проверьте подключение кабеля и права доступа (группа dialout).")
