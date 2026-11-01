"""
Модуль для управления VFD-дисплеями по протоколу EPSON.
Операционные Системы (ОС): Linux (/dev/ttyACM*, /dev/ttyUSB*), Windows (COMx), macOS (/dev/tty.usb*).
Python: Python 3.10+ и библиотеку pyserial.
Вакуумно-флуоресцентный (VFD - Vacuum Fluorescent Display) дисплей покупателя!
"""

# Copyright (c) 2026 Roman Shevchik (octaprog7) <kolbasilyvasily@yandex.ru>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# <https://www.gnu.org/licenses/gpl-3.0.html>

import os
import sys
import locale
from enum import Enum, auto


if not sys.platform.startswith("linux"):
    print("Предупреждение: Драйвер протестирован на Linux. "
          "На других платформах используйте autodetect_port() или укажите порт вручную (например 'COM3').")
if sys.version_info < (3, 10):
    sys.exit("Ошибка: Этот проект требует Python 3.10 или выше.")

# Проверка наличия необходимых библиотек
try:
    import serial
except ImportError:
    serial = None
    print(f"Критическая ошибка: Библиотека 'serial' не установлена.")
    sys.exit(1)


class DisplayType(Enum):
    """Тип подключаемого устройства."""
    TEXT = auto()
    GRAPHIC = auto()


class SerialConn:
    """Транспортный уровень для работы с последовательным портом.
    Ориентирован на Linux-системы (интерфейсы ttyACM / ttyUSB)."""

    def __init__(self, port: str, baud_rate: int = 9600, timeout: float = 0.5):
        """Инициализация параметров соединения."""
        self._port = port
        self._baud_rate = baud_rate
        self._timeout = timeout
        self._connection: serial.Serial | None = None

    def open(self) -> None:
        """Открывает соединение с портом, если оно еще не открыто."""
        if not self.is_open:
            self._connection = serial.Serial(
                port=self._port,
                baudrate=self._baud_rate,
                timeout=self._timeout
            )

    @property
    def is_open(self) -> bool:
        """Проверяет, открыт ли порт в данный момент."""
        return self._connection is not None and self._connection.is_open

    def close(self) -> None:
        """Закрывает соединение с портом."""
        if self.is_open:
            self._connection.close()  # type: ignore

    def write(self, data: bytes) -> None:
        """Отправляет сырые байты в порт."""
        if not self.is_open:
            raise ConnectionError(f"Порт {self._port} недоступен")
        self._connection.write(data)  # type: ignore


def autodetect_port() -> str:
    """Автоматически определяет последовательный порт подключенного устройства.

    ОС:
      - Linux:  /dev/ttyACM*, /dev/ttyUSB*;
      - Windows: COMx (Диспетчер устройств);
      - macOS:  /dev/tty.usb*.

    :return: Имя порта (например, '/dev/ttyUSB0' или 'COM3').
    :raises ConnectionError: Если порт не найден.
    """
    try:
        from serial.tools import list_ports
    except ImportError:
        raise RuntimeError("Библиотека 'serial' не установлена (pip install pyserial).")

    ports = list(list_ports.comports())
    if not ports:
        raise ConnectionError("Не найдено ни одного последовательного порта. "
                              "Проверьте подключение дисплея.")

    if sys.platform.startswith("linux"):
        # Сначала USB-устройства (ACM — CDC-совместимые, USB — конвертеры)
        candidates = [p.device for p in ports if "ttyACM" in p.device or "ttyUSB" in p.device]
    elif sys.platform == "darwin":
        candidates = [p.device for p in ports if "tty.usb" in p.device]
    else:
        # Windows и прочие: беру все COM-порты
        candidates = [p.device for p in ports]

    if not candidates:
        # Ничего характерного не нашли — возвращаем первый попавшийся порт
        candidates = [p.device for p in ports]

    return candidates[0]


class POSDisplay:
    """Базовый абстрактный класс дисплея покупателя."""

    def __init__(self, connection: SerialConn, encoding: str):
        """Создает объект дисплея с привязкой к транспорту и кодировке."""
        self._conn = connection
        self._encoding = encoding
        self._rows: int = 0
        self._cols: int = 0
        self._buffer: list[str] = []
        self._display_type: DisplayType | None = None

    def connect(self) -> None:
        """Устанавливает связь и инициализирует экранный буфер."""
        self._conn.open()
        self._buffer = [" " * self._cols for _ in range(self._rows)]

    def disconnect(self) -> None:
        """Разрывает связь с устройством."""
        self._conn.close()

    def __enter__(self):
        """Поддержка контекстного менеджера (with)."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Автоматическое закрытие порта при выходе из with."""
        self.disconnect()

    def __del__(self):
        """Освобождение ресурсов при удалении объекта из памяти."""
        self.disconnect()

    def _update_buffer(self, text: str, line: int) -> None:
        """Обновляет внутреннее состояние строк для синхронизации."""
        formatted = text[:self._cols].ljust(self._cols)
        self._buffer[line - 1] = formatted

    def __len__(self) -> int:
        """Возвращает общую емкость дисплея в символах."""
        return self._rows * self._cols

    def __str__(self) -> str:
        """Возвращает текстовую визуализацию текущего состояния экрана."""
        if not self._buffer: return "[Экран не активен]"
        header = f"[{self._display_type.name if self._display_type else 'UNKNOWN'}]"
        border = f"+{'-' * self._cols}+"
        return "\n".join([header, border, *(f"|{line}|" for line in self._buffer), border])

    @property
    def display_type(self) -> DisplayType | None:
        """Возвращает тип дисплея (ТЕКСТОВЫЙ/ГРАФИЧЕСКИЙ)."""
        return self._display_type

    def get_rows_cols(self) -> tuple[int, int]:
        """Возвращает количество строк и столбцов дисплея."""
        raise NotImplementedError()


class EpsonProtocol(POSDisplay):
    """Реализация стандартного набора команд протокола EPSON."""

    def initialize(self) -> None:
        """Сброс настроек устройства к заводским (команда ESC @)."""
        self._conn.write(b'\x1b\x40')

    def clear(self) -> None:
        """Полная очистка экрана и сброс буфера."""
        self._conn.write(b'\x0c')
        self._buffer = [" " * self._cols for _ in range(self._rows)]

    def set_cursor(self, col: int, row: int) -> None:
        """Устанавливает курсор в указанную позицию (1-based)."""
        self._conn.write(b'\x1b\x6c' + bytes([col, row]))

    def write(self, data: str | bytes, index: int = 0) -> None:
        """
        Универсальный метод вывода данных.
        Если передана строка — выводит текст с обновлением буфера.
        Если переданы байты — отправляет их напрямую в порт.

        :param data: Строка или байты для отправки.
        :param index: Индекс строки (0 или 1).
        """
        if isinstance(data, str):
            if not (0 <= index < self._rows):
                raise IndexError(f"Некорректный индекс строки: {index}")
            # Устанавливаем курсор в начало выбранной строки (i + 1 для железа)
            self.set_cursor(1, 1 + index)
            self._update_buffer(data, 1 + index)
            self._conn.write(self._buffer[index].encode(self._encoding))
        elif isinstance(data, bytes):
            # Прямая отправка без изменения внутреннего буфера текста
            self._conn.write(data)
        else:
            raise TypeError("Аргумент data должен быть типа str или bytes")

    def __setitem__(self, index: int, text: str):
        """Запись vfd[i] = text."""
        self.write(text, index)

    def __call__(self, text: str, index: int = 0, scroll: bool = False):
        """Вызов vfd(text, index=0)."""
        if scroll:
            # Бегущая строка, для упрощения, только на первой строке
            # self.write("SCROLL MODE...", index)
            self.write(text, index)
            # Тут могла быть логика scroll
        else:
            self.write(text, index)

    def set_brightness(self, level: int) -> None:
        """Установка яркости дисплея (0-3).
        0 - 20%, 1 - 40%, 2 - 60%, 3 - 100%."""
        if not level in range(4):
            raise ValueError("Уровень яркости должен быть от 0 до 3!")
        # Команда ESC * n
        self._conn.write(b'\x1b\x2a' + bytes([1 + level]))

    def set_blinking(self, enable: bool = True) -> None:
        """Включить/выключить мигание всего экрана."""
        # Команда ESC [ n (зависит от прошивки, обычно 0 - выкл, 1 - вкл)
        code = 1 if enable else 0
        self._conn.write(b'\x1b\x5b' + bytes([code]))

    def define_custom_char(self, id_char: int, pattern: tuple[int, int, int, int, int]) -> None:
        """Определяет пользовательский символ.
        :param id_char: ID символа (0-7).
        :param pattern: Список из 5 байт (каждый байт - вертикальная колонка 7 пикселей).
        Каждый символ — это сетка 5x7 пикселей!"""
        if not id_char in range(8):
            raise ValueError("ID символа должен быть от 0 до 7!")
        if 5 != len(pattern):
            raise ValueError("Спрайт должен содержать ровно 5 байт!")

        # Команда ESC & s n m [d1...da]
        # s=1, n=m=char_code
        header = b'\x1b\x26\x01' + bytes([id_char, id_char])
        self._conn.write(header + bytes(pattern))

    def custom_chars(self, enable: bool = True) -> None:
        """Включает или выключает использование пользовательских символов, см. define_custom_char.
        Если True — символы с кодами 0-7 заменяются на твои спрайты."""
        code = 1 if enable else 0
        self._conn.write(b'\x1b\x25' + bytes([code]))

    def self_test(self) -> None:
        """Запуск встроенного аппаратного теста дисплея."""
        # Команда в большинстве Epson-совместимых VFD
        self._conn.write(b'\x1b\x64')


# Иконки для мониторинга (5x7 пикселей)
VFD_ICON_TEMP = (0x0E, 0x11, 0x5D, 0x11, 0x0E)  # Термометр
VFD_ICON_LIGHTNING = (0x12, 0x25, 0x7F, 0x12, 0x04)  # Молния (нагрузка)
VFD_ICON_BELL = (0x0C, 0x1E, 0x1F, 0x1E, 0x0C)  # Колокольчик (тревога)


class VfdCustomerDisplay(EpsonProtocol):
    """Класс для VFD дисплея c EPSON совместимой системой команд."""
    DEFAULT_ENCODING: str = 'cp866' # для VFD дисплеев с поддержкой русского языка
    #
    CHARSET_USA = 0x00
    CHARSET_EUROPE = 0x02
    CHARSET_CYRILLIC = 0x07

    # Соответствие кодировок Python и CHARSET-кодов дисплея
    ENCODING_TO_CHARSET: dict[str, int] = {
        'ascii': CHARSET_USA,
        'cp437': CHARSET_EUROPE,
        'cp866': CHARSET_CYRILLIC,
    }

    def __init__(self, connection: SerialConn, encoding: str | None = None):
        """Настройка геометрии (2x20) и кодировки по умолчанию.
        :param encoding: Явная кодировка ('cp866', 'cp437', 'ascii').
                         Если None - определяется по локали ОС в initialize()."""
        self._explicit_encoding = encoding is not None
        super().__init__(connection, encoding=encoding or self.DEFAULT_ENCODING)
        self._rows, self._cols = 2, 20
        # тип для этой модели
        self._display_type = DisplayType.TEXT

    def set_charset(self, code: int, encoding: str | None = None) -> None:
        """
        Переключает кодовую страницу. При encoding=None кодировка
        выбирается автоматически на основе констант CHARSET.
        """
        if encoding is None:
            match code:
                case self.CHARSET_USA:
                    encoding = 'ascii'
                case self.CHARSET_EUROPE:
                    encoding = 'cp437'
                case self.CHARSET_CYRILLIC:
                    # Кириллица всегда кодируется в CP866 (не в текущую кодировку!)
                    encoding = self.DEFAULT_ENCODING
                case _:
                    raise ValueError(f"Нет автоматической кодировки для CHARSET кода: {code}")

        # Проверка на вхождение в список разрешенных констант
        if code not in (self.CHARSET_USA, self.CHARSET_EUROPE, self.CHARSET_CYRILLIC):
            raise ValueError(f"Код {code} не поддерживается данной моделью дисплея!")

        self._encoding = encoding
        self._conn.write(b'\x1b\x74' + bytes([code]))

    def get_encoding(self)->str:
        """Возвращает текущую кодировку."""
        return self._encoding

    def initialize(self) -> None:
        eu_lang = ('de', 'fr', 'es', 'it', 'nl')
        """Инициализация с выбором набора символов (кириллица/латиница)."""
        super().initialize()
        if self._explicit_encoding:
            # Кодировка задана пользователем явно - синхронизирую набор символов с ней,
            # игнорирую локаль ОС (для тестов и нестандартных сценариев)
            target_code = self.ENCODING_TO_CHARSET.get(self._encoding)
            if target_code is None:
                raise ValueError(
                    f"Нет CHARSET-кода для кодировки '{self._encoding}'. "
                    f"Доступно: {', '.join(self.ENCODING_TO_CHARSET)}")
        else:
            # Кодировка не задана - определяю язык системы кроссплатформенно:
            # Linux/macOS — переменные окружения LANG/LC_ALL,
            # Windows — locale.getlocale() (например 'Russian_Russia').
            try:
                # попытка получить текущую локаль
                lang, _ = locale.getlocale()
            except ValueError:
                # в ОС задана неверная локаль
                lang = None
            # Кроссплатформенность: Windows возвращает 'Russian_Russia'/'ru_RU' —
            # привожу к нижнему регистру. На Linux язык берём из окружения (LANG).
            lang = (lang or os.environ.get("LC_ALL") or os.environ.get("LANG") or "").lower()

            match lang:
                case str(l) if l.startswith('ru'):
                    target_code =  self.CHARSET_CYRILLIC
                case str(l) if l.startswith('en'):
                    target_code = self.CHARSET_USA
                # евро-префиксы
                case str(l) if l.startswith(eu_lang):
                    target_code = self.CHARSET_EUROPE
                case _:
                    #  латиница должна быть на любом POS-дисплее (ASCII)
                    target_code = self.CHARSET_USA
        #
        self.set_charset(code=target_code)

    def meter(self, label: str, value: float, index: int = 0) -> None:
        """Рисует горизонтальный текстовый столбик (Progress Bar).
        Пример: CPU [#######   ] 72%."""
        val = max(0.0, min(100.0, value))
        # 4 символа на метку, 2 на скобки, 4 на проценты = 10.
        # Остается ровно 10 символов на шкалу при cols=20.
        bar_len = self._cols - 10
        filled = int((val / 100) * bar_len)

        bar = "#" * filled + " " * (bar_len - filled)
        # Формат: Метка(4) + [ + Бар(10) + ] + Проценты(3) + %
        line = f"{label[:4]:<4}[{bar}]{val:>3.0f}%"
        #
        self.write(line, index)

    def get_rows_cols(self) -> tuple[int, int]:
        return 2, 20