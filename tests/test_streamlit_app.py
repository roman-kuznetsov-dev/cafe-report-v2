"""
Smoke-тест веб-версии app.py.

Проверяет:
  - файл app.py существует;
  - синтаксически корректен (можно скомпилировать);
  - содержит импорты основных модулей;
  - модули, используемые app.py, импортируются без ошибок.
"""

import ast
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


APP_PATH = os.path.join(os.path.dirname(__file__), "..", "app.py")


def test_app_py_exists():
    """Файл app.py существует в корне проекта."""
    assert os.path.exists(APP_PATH), "app.py не найден в корне"


def test_app_py_syntax_valid():
    """app.py компилируется без синтаксических ошибок."""
    with open(APP_PATH, encoding="utf-8") as f:
        source = f.read()
    try:
        ast.parse(source)
    except SyntaxError as e:
        raise AssertionError(f"Синтаксическая ошибка в app.py: {e}") from e


def test_app_py_imports_cafe_modules():
    """app.py импортирует основные модули проекта."""
    with open(APP_PATH, encoding="utf-8") as f:
        source = f.read()

    required = [
        "from cafe_analysis import",
        "from cafe_loader import",
        "from cafe_exporter import",
        "from cafe_optimizer import",
    ]
    for imp in required:
        assert imp in source, f"app.py не содержит импорт: {imp}"


def test_cafe_modules_importable():
    """Модули, используемые app.py, импортируются без ошибок."""
    import cafe_analysis  # noqa: F401
    import cafe_charts  # noqa: F401
    import cafe_exporter  # noqa: F401
    import cafe_loader  # noqa: F401
    import cafe_optimizer  # noqa: F401
