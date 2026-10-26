# -*- coding: utf-8 -*-
"""Сверка четырёх ответов. Выдан готовым, менять его не нужно.

    python3 src/partner/verify.py
    python3 src/partner/verify.py --answers src/incident.md

Обычный режим запускает src/report.py. Режим --answers читает ручные ответы
из файла и не запускает программу участника. Готовые ответы не печатаются.
Контрольные суммы служат для сверки, а не для сокрытия коротких ответов.
"""
import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path

КОРЕНЬ = Path(__file__).resolve().parents[2]
ОТЧЁТ = КОРЕНЬ / "src/report.py"
ПУНКТЫ = [
    ("первый подозрительный вызов", "первый_подозрительный_вызов", False),
    ("отменено чужих заказов", "отменено_чужих_заказов", True),
    ("аккаунт выгодоприобретателя", "аккаунт_выгодоприобретателя", False),
    ("оформлено на этот аккаунт", "оформлено_на_один_аккаунт", True),
]


def мой_вариант():
    """Одна буква назначенного варианта; русская А нормализуется в латинскую A."""
    файл = КОРЕНЬ / "src/variant.txt"
    if not файл.exists():
        raise SystemExit("Не найден src/variant.txt. Впиши одну латинскую букву "
                         "варианта, назначенного рандомайзером или стаффом: A, B, C, D или E.")
    буква = файл.read_text(encoding="utf-8").strip().upper().replace("А", "A")
    if буква not in ("A", "B", "C", "D", "E") or not (КОРЕНЬ / "datasets" / буква).is_dir():
        raise SystemExit(f"Варианта {буква!r} нет. Впиши в src/variant.txt одну букву: A, B, C, D или E.")
    return буква


def посолить(вариант, значение):
    основа = f"lavka-2026|{вариант}|{str(значение).strip().lower()}"
    return hashlib.sha256(основа.encode("utf-8")).hexdigest()[:16]


def разобрать_ответы(текст):
    подписи = {п[0] for п in ПУНКТЫ}
    ответы, повторы = {}, set()
    for строка in текст.splitlines():
        if ":" not in строка:
            continue
        ключ, значение = строка.split(":", 1)
        ключ = ключ.strip().lower()
        if ключ not in подписи:
            continue
        if ключ in ответы:
            повторы.add(ключ)
        ответы[ключ] = значение.strip()
    return ответы, повторы


def main():
    парсер = argparse.ArgumentParser(description=__doc__)
    парсер.add_argument("--answers", metavar="ФАЙЛ", help="сверить ручные ответы без запуска report.py")
    параметры = парсер.parse_args()
    вариант = мой_вариант()
    суммы = {}
    for строка in (КОРЕНЬ / "datasets" / вариант / "answers.sha256").read_text(encoding="utf-8").splitlines():
        if строка.startswith("#") or ":" not in строка:
            continue
        поле, значение = строка.split(":", 1)
        суммы[поле.strip()] = значение.strip()

    if параметры.answers:
        файл = Path(параметры.answers)
        if not файл.is_absolute():
            файл = КОРЕНЬ / файл
        try:
            текст = файл.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as ошибка:
            raise SystemExit(f"Не удалось прочитать файл ручных ответов: {ошибка}")
        print("Ручная сверка: src/report.py не запускается.")
    else:
        if not ОТЧЁТ.exists():
            raise SystemExit("Файла src/report.py нет. Напиши программу либо используй "
                             "--answers src/incident.md для ручных ответов.")
        try:
            запуск = subprocess.run([sys.executable, str(ОТЧЁТ)], capture_output=True,
                                    text=True, encoding="utf-8", timeout=120, cwd=str(КОРЕНЬ))
        except subprocess.TimeoutExpired:
            raise SystemExit("src/report.py не завершился за 120 секунд.")
        except UnicodeError:
            raise SystemExit("Вывод src/report.py не удалось прочитать как UTF-8.")
        if запуск.returncode != 0:
            print("src/report.py завершился с ошибкой:\n")
            print((запуск.stderr or "").strip()[-600:])
            raise SystemExit(1)
        текст = запуск.stdout
        строки = текст.splitlines()
        ожидаемые = [п[0] for п in ПУНКТЫ]
        if len(строки) != 4 or any(
                not строка.startswith(подпись + ": ")
                for строка, подпись in zip(строки, ожидаемые)):
            print("Формат вывода не соответствует README: нужны ровно четыре строки "
                  "в указанном порядке. Найденные ответы сверяются ниже.")

    ответы, повторы = разобрать_ответы(текст)
    print(f"Вариант {вариант}. Сверяю выводы с фактами инцидента.\n")
    сошлось = 0
    for подпись, поле, это_число in ПУНКТЫ:
        дано = ответы.get(подпись)
        if подпись in повторы:
            print(f"  ? {подпись}: найдено несколько ответов; оставь одну строку")
            continue
        if дано is None:
            print(f"  ? {подпись}: строки с таким началом в выводе нет")
            continue
        if это_число and re.fullmatch(r"[0-9]+", дано) is None:
            print(f"  - {подпись}: не сходится — нужно целое неотрицательное число без пояснений")
            continue
        нормализованное = (дано.lstrip("0") or "0") if это_число else дано
        совпало = посолить(вариант, нормализованное) == суммы.get(поле)
        print(f"  {'+' if совпало else '-'} {подпись}: {'сходится' if совпало else 'не сходится'}")
        сошлось += совпало
    print(f"\nСошлось пунктов: {сошлось} из {len(ПУНКТЫ)}")
    print("Правильные значения этот скрипт не показывает. На P2P объясни выводы по журналу.")


if __name__ == "__main__":
    main()
