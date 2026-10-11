"""
Универсальный импортёр данных из внешних систем.

Принимает выгрузку из 1С / iiko / R-Keeper / любой другой системы
(формат xlsx или csv), спрашивает у пользователя маппинг столбцов,
преобразует в наш формат cafe_data.xlsx.

Маппинг сохраняется — при следующем импорте с той же структурой
столбцов диалог не потребуется.

Использование:
    python tools/import_external.py --input выгрузка.xlsx
    python tools/import_external.py --input выгрузка.csv
    python tools/import_external.py --input выгрузка.xlsx --out my_data.xlsx
    python tools/import_external.py --input выгрузка.xlsx --no-collapse
"""

import argparse
import hashlib
import json
import os
import sys

import pandas as pd

# ============================================================
#  КОНСТАНТЫ
# ============================================================
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(TOOLS_DIR)
MAPPINGS_FILE = os.path.join(TOOLS_DIR, "mappings.json")

DEFAULT_OUTPUT = os.path.join(PROJECT_DIR, "cafe_data.xlsx")

# Наши целевые колонки (для одной выгрузки за один период)
TARGET_COLUMNS = [
    "Товар", "Категория",
    "Закуп_1", "Закуп_2",
    "Цена_1", "Цена_2",
    "Кол_1", "Кол_2",
    "Закуп_кол_1", "Закуп_кол_2",
    "Остаток_нач_1", "Остаток_нач_2",
]


# ============================================================
#  ЧТЕНИЕ ФАЙЛА
# ============================================================
def read_file(path: str) -> pd.DataFrame:
    """Читает xlsx или csv, возвращает DataFrame."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Файл не найден: {path}")

    ext = os.path.splitext(path)[1].lower()

    if ext == ".csv":
        for enc in ("utf-8", "utf-8-sig", "cp1251"):
            try:
                return pd.read_csv(path, encoding=enc)
            except UnicodeDecodeError:
                continue
        raise ValueError("Не удалось прочитать CSV: неверная кодировка")

    if ext in (".xlsx", ".xls"):
        xl = pd.ExcelFile(path)
        sheet = xl.sheet_names[0]
        return pd.read_excel(path, sheet_name=sheet)

    raise ValueError(
        f"Формат не поддерживается: {ext}. Разрешены: .xlsx, .xls, .csv"
    )


# ============================================================
#  СИГНАТУРА СТОЛБЦОВ
# ============================================================
def columns_signature(columns) -> str:
    """
    Хеш от отсортированного списка столбцов.
    Одинаковый набор столбцов → одинаковый signature,
    вне зависимости от порядка.
    """
    normalized = sorted(str(c).strip() for c in columns)
    joined = "|".join(normalized)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()[:16]


# ============================================================
#  РАБОТА С МАППИНГАМИ
# ============================================================
def load_mappings() -> dict:
    """Читает файл mappings.json. Если нет — пустая структура."""
    if not os.path.exists(MAPPINGS_FILE):
        return {"mappings": []}
    try:
        with open(MAPPINGS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if "mappings" not in data:
            data = {"mappings": []}
        return data
    except Exception:
        return {"mappings": []}


def save_mappings(data: dict):
    """Сохраняет mappings.json."""
    with open(MAPPINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def find_mapping(signature: str) -> dict | None:
    """Ищет маппинг по signature. Возвращает mapping или None."""
    data = load_mappings()
    for m in data["mappings"]:
        if m.get("signature") == signature:
            return m
    return None


def add_mapping(signature: str, name: str,
                columns, mapping: dict):
    """Добавляет новый маппинг."""
    data = load_mappings()
    data["mappings"] = [m for m in data["mappings"]
                        if m.get("signature") != signature]
    data["mappings"].append({
        "signature": signature,
        "name": name,
        "columns": [str(c) for c in columns],
        "mapping": mapping,
    })
    save_mappings(data)


# ============================================================
#  АВТООПРЕДЕЛЕНИЕ МАППИНГА
# ============================================================
COLUMN_HINTS = {
    "Товар":     ["товар", "наимен", "назван", "name", "номенклат"],
    "Категория": ["категор", "группа", "category", "тип"],
    "Закуп_1":   ["закуп", "себест", "приход", "cost", "purchase"],
    "Цена_1":    ["цена", "продаж", "price", "sale"],
    "Кол_1":     ["кол-во", "колич", "продано", "шт", "qty", "quantity"],
    "Дата":      ["дата", "date", "период"],
}


def guess_mapping(columns) -> dict:
    """
    Угадывает маппинг по именам столбцов.

    Каждый столбец используется один раз: если столбец уже привязан
    к какому-то полю, он не будет использован повторно.
    Это защищает от ситуации, когда <<Закуп.Цена>> цепляется и к
    <<Закуп_1>>, и к <<Цена_1>>.
    """

    result = {}
    used_columns = set()
    lower_cols = [(c, str(c).strip().lower()) for c in columns]

    for target, hints in COLUMN_HINTS.items():
        for original, low in lower_cols:
            if original in used_columns:
                continue
            if any(h in low for h in hints):
                result[target] = str(original)
                used_columns.add(original)
                break
    return result


# ============================================================
#  СВОРАЧИВАНИЕ ДУБЛИКАТОВ
# ============================================================
def collapse_duplicates(df: pd.DataFrame,
                        key_col: str,
                        agg_rules: dict) -> pd.DataFrame:
    """Сворачивает дубликаты по key_col."""
    used_cols = [key_col] + [c for c in agg_rules if c in df.columns]
    sub = df[used_cols].copy()

    actual_rules = {c: agg_rules[c] for c in agg_rules
                    if c in sub.columns}

    if not actual_rules:
        return sub.drop_duplicates(subset=[key_col])

    return sub.groupby(key_col, as_index=False).agg(actual_rules)


# ============================================================
#  ПРИМЕНЕНИЕ МАППИНГА
# ============================================================
def apply_mapping(df: pd.DataFrame,
                  mapping: dict,
                  collapse: bool = True) -> pd.DataFrame:
    """Преобразует входной DataFrame в наш формат."""
    if "Товар" not in mapping:
        raise ValueError("В маппинге нет обязательного поля «Товар»")

    rename_map = {v: k for k, v in mapping.items() if v in df.columns}
    df = df.rename(columns=rename_map)

    keep = [c for c in TARGET_COLUMNS if c in df.columns]
    if "Товар" not in keep:
        raise ValueError("После маппинга нет столбца «Товар»")

    df = df[keep].copy()

    if collapse:
        agg = {}
        for c in df.columns:
            if c == "Товар":
                continue
            if c == "Категория":
                agg[c] = "first"
            else:
                agg[c] = "sum"
        df = collapse_duplicates(df, "Товар", agg)

    return df


# ============================================================
#  ИНТЕРАКТИВНЫЙ ДИАЛОГ
# ============================================================
def interactive_dialog(columns, sig) -> dict:
    """
    Спрашивает у пользователя, какой столбец соответствует какому полю.
    Возвращает маппинг {наша_колонка: имя_столбца_во_входе}.

    columns — список столбцов входного файла.
    sig — signature (для информации).
    """
    print("\n" + "=" * 60)
    print("НАСТРОЙКА МАППИНГА")
    print("=" * 60)

    # Что нужно сопоставить (только обязательные поля)
    fields = [
        ("Товар", True,
         "Название товара"),
        ("Категория", False,
         "Категория (готовый / напиток). Можно пропустить — "
         "тогда ставим «готовый» по умолчанию."),
        ("Закуп_1", True,
         "Закупочная цена в 1 периоде"),
        ("Цена_1", True,
         "Цена продажи в 1 периоде"),
        ("Кол_1", True,
         "Продано штук в 1 периоде"),
        ("Закуп_кол_1", False,
         "Закуплено штук в 1 периоде. Если нет — "
         "поставим равным проданному."),
        ("Остаток_нач_1", False,
         "Остаток на начало 1 периода. Если нет — 0."),
        ("Закуп_2", False,
         "Закупочная цена во 2 периоде. Если нет — "
         "возьмём из 1 периода."),
        ("Цена_2", False,
         "Цена продажи во 2 периоде. Если нет — "
         "возьмём из 1 периода."),
        ("Кол_2", False,
         "Продано штук во 2 периоде. Если нет — "
         "возьмём из 1 периода."),
    ]

    # Автоподсказки по именам столбцов
    hints = guess_mapping(columns)

    # Показываем столбцы с номерами
    print("\nСтолбцы в вашем файле:")
    for i, c in enumerate(columns):
        print(f"  [{i}] {c}")

    print("\nДля каждого поля — введите имя или номер столбца.")
    print("Пустой ввод = пропустить (только для необязательных).")
    print()

    mapping = {}

    for field, required, description in fields:
        while True:
            # Подсказка от автопоиска
            hint_text = ""
            if field in hints:
                hint_text = f" [подсказка: {hints[field]}]"

            prompt = f"Поле «{field}» — {description}{hint_text}\n> "
            answer = input(prompt).strip()

            # Пустой ввод
            if not answer:
                if required:
                    print("  ✗ Это поле обязательное. Введите столбец.")
                    continue
                break

            # Попытка использовать подсказку
            if field in hints and answer.lower() == "hint":
                mapping[field] = hints[field]
                print(f"  ✓ Использую подсказку: {hints[field]}")
                break

            # Ввод — номер столбца
            if answer.isdigit():
                idx = int(answer)
                if 0 <= idx < len(columns):
                    mapping[field] = str(columns[idx])
                    print(f"  ✓ {field} = {columns[idx]}")
                    break
                else:
                    print(f"  ✗ Номер вне диапазона (0–{len(columns) - 1})")
                    continue

            # Ввод — имя столбца
            matched = None
            for c in columns:
                if str(c).strip().lower() == answer.lower():
                    matched = str(c)
                    break
            if matched:
                mapping[field] = matched
                print(f"  ✓ {field} = {matched}")
                break

            print(f"  ✗ Столбец «{answer}» не найден. "
                  f"Введите номер или точное имя.")

    print("\n" + "=" * 60)
    print("ИТОГОВЫЙ МАППИНГ")
    print("=" * 60)
    for k, v in mapping.items():
        print(f"  {k} ← {v}")

    confirm = input("\nСохранить маппинг? (д/н) [д]: ").strip().lower()
    if confirm and confirm not in ("д", "y", "yes", "да"):
        raise ValueError("Маппинг не подтверждён пользователем")

    return mapping


# ============================================================
#  ГЛАВНАЯ ФУНКЦИЯ
# ============================================================
def import_data(input_path: str,
                output_path: str = DEFAULT_OUTPUT,
                dialog_func=None,
                collapse: bool = True) -> str:
    """
    Главная функция импорта.
    dialog_func — функция для диалога, если маппинг не найден.
    Возвращает путь к сохранённому файлу.
    """
    print(f"Открываю файл: {input_path}")
    df = read_file(input_path)

    if df.empty:
        raise ValueError("Файл пустой")

    columns = list(df.columns)
    print(f"Столбцов: {len(columns)}")
    print(f"Строк: {len(df)}")

    sig = columns_signature(columns)
    print(f"Signature: {sig}")

    found = find_mapping(sig)
    if found:
        print(f"Найден сохранённый маппинг: {found.get('name', 'без имени')}")
        mapping = found["mapping"]
    else:
        print("Сохранённый маппинг не найден.")
        if dialog_func is None:
            raise ValueError(
                "Нет сохранённого маппинга и не задан dialog_func."
            )
        mapping = dialog_func(columns, sig)

        name = input(
            "Название формата (например, «1С:Общепит»): "
        ).strip() or f"Формат {sig[:6]}"
        add_mapping(sig, name, columns, mapping)
        print(f"Маппинг сохранён в {MAPPINGS_FILE}")

    print("Преобразую данные...")
    result_df = apply_mapping(df, mapping, collapse=collapse)
    print(f"Товаров после сворачивания: {len(result_df)}")

    with pd.ExcelWriter(output_path, engine="xlsxwriter") as w:
        result_df.to_excel(w, sheet_name="Товары", index=False)

    print(f"Готово: {output_path}")
    return output_path


# ============================================================
#  CLI
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="Импорт данных из внешних систем")
    parser.add_argument("--input", required=True,
                        help="Файл выгрузки (.xlsx, .xls, .csv)")
    parser.add_argument("--out", default=DEFAULT_OUTPUT,
                        help="Куда сохранить (по умолчанию cafe_data.xlsx)")
    parser.add_argument("--no-collapse", action="store_true",
                        help="Не сворачивать дубликаты")
    args = parser.parse_args()

    def dummy_dialog(columns, sig):
        print("\nДиалог маппинга пока не реализован в этом коммите.")
        print("Столбцы в файле:", columns)
        raise NotImplementedError(
            "Коммит 2 добавит интерактивный диалог."
        )

    try:
        import_data(args.input, args.out,
                    dialog_func=interactive_dialog,
                    collapse=not args.no_collapse)
    except Exception as e:
        print(f"ОШИБКА: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
