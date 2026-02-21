# dump_my_structure.py
"""
Створює дамп зі структурою проекту і вмістом тільки ваших файлів
Виправлена версія з правильною структурою
"""

import os
from pathlib import Path
from datetime import datetime


def dump_my_structure():
    root_dir = Path(__file__).parent
    output_file = root_dir / "my_project_structure.txt"

    print(f"📁 Створюю дамп структури вашого проекту: {output_file}")
    print(f"📂 Робоча папка: {root_dir}")

    # ТІЛЬКИ ваші файли - розширення, які ви створювали
    extensions = {'.py', '.yaml', '.yml', '.env', '.md', '.txt', '.json'}

    # Папки, які ТРЕБА включити (ваш код)
    include_dirs = {'src', 'test'}

    # Папки, які ТРЕБА виключити
    exclude_dirs = {
        '__pycache__', '.venv', 'venv', 'env', '.git', '.idea',
        'node_modules', 'dist', 'build', '.pytest_cache', 'data', 'logs'
    }

    # Функція для перевірки чи файл ваш
    def is_my_file(path):
        rel_path = path.relative_to(root_dir)
        parts = rel_path.parts

        # ⚠️ СПЕЦІАЛЬНА ПЕРЕВІРКА ДЛЯ .gitignore
        if path.name == '.gitignore':
            return True

        # Виключаємо системні папки
        if any(excl in str(rel_path) for excl in exclude_dirs):
            return False

        # Якщо файл в src або test - беремо
        if len(parts) > 0 and parts[0] in include_dirs:
            return True

        # Файли в корені проекту
        if len(parts) == 1:
            # Важливі файли в корені
            if path.name in ['main.py', 'config.yaml', '.env', 'requirements.txt',
                             'README.md', 'dump_my_structure.py', 'combine_project.py']:
                return True
            # Файли з правильним розширенням
            if path.suffix in extensions:
                return True

        return False

    # Збираємо всі ваші файли і папки
    my_files = []
    my_dirs = set()

    print("\n📂 ЗБІР ФАЙЛІВ:")
    for path in sorted(root_dir.rglob('*')):
        if path.is_file() and is_my_file(path):
            my_files.append(path)
            print(f"   + {path.relative_to(root_dir)}")
            # Додаємо всі батьківські папки
            parent = path.parent
            while parent != root_dir:
                my_dirs.add(parent)
                parent = parent.parent

    # Сортуємо
    my_files.sort()
    my_dirs = sorted(my_dirs)

    # Відкриваємо файл для запису
    with open(output_file, 'w', encoding='utf-8') as out:
        # Заголовок
        out.write("=" * 80 + "\n")
        out.write("🔥 ВАШ ПРОЕКТ - СТРУКТУРА ТА ФАЙЛИ\n")
        out.write(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        out.write("=" * 80 + "\n\n")

        # ===== СТРУКТУРА =====
        out.write("📁 СТРУКТУРА ВАШОГО ПРОЕКТУ:\n")
        out.write("-" * 80 + "\n\n")

        def print_structure(dir_path, level=0):
            """Рекурсивно виводить структуру папок без дублювання"""
            indent = "  " * level

            # Виводимо назву папки
            if level == 0:
                out.write(f"{indent}📁 {root_dir.name}/\n")
            else:
                out.write(f"{indent}📁 {dir_path.name}/\n")

            # Збираємо всі підпапки і файли в цій папці
            items = []
            subdirs = []

            # Спочатку збираємо всі підпапки
            for path in sorted(dir_path.iterdir()):
                if path.is_dir():
                    if path in my_dirs or any(f.parent == path for f in my_files):
                        subdirs.append(('dir', path))

            # Потім збираємо файли в поточній папці
            files = []
            for path in sorted(dir_path.iterdir()):
                if path.is_file() and path in my_files:
                    files.append(('file', path))

            # Спочатку виводимо файли
            for item_type, item_path in files:
                if item_path.name == '.gitignore':
                    out.write(f"{indent}  📄 🔒 {item_path.name} (GITIGNORE)\n")
                elif item_path.name == '.env':
                    out.write(f"{indent}  📄 🔐 {item_path.name} (ENV)\n")
                elif item_path.name == 'config.yaml':
                    out.write(f"{indent}  📄 ⚙️ {item_path.name} (CONFIG)\n")
                else:
                    out.write(f"{indent}  📄 {item_path.name}\n")

            # Потім виводимо підпапки (рекурсивно)
            for item_type, item_path in subdirs:
                print_structure(item_path, level + 1)

        # Починаємо з кореня
        print_structure(root_dir)

        # ===== ВМІСТ =====
        out.write("\n" + "=" * 80 + "\n\n")
        out.write("📄 ВМІСТ ВАШИХ ФАЙЛІВ:\n")
        out.write("=" * 80 + "\n\n")

        for path in my_files:
            rel_path = path.relative_to(root_dir)
            out.write(f"\n{'=' * 80}\n")

            if path.name == '.gitignore':
                out.write(f"📄 🔒 ФАЙЛ: {rel_path} (GITIGNORE)\n")
            elif path.name == '.env':
                out.write(f"📄 🔐 ФАЙЛ: {rel_path} (ENV)\n")
            elif path.name == 'config.yaml':
                out.write(f"📄 ⚙️ ФАЙЛ: {rel_path} (CONFIG)\n")
            else:
                out.write(f"📄 ФАЙЛ: {rel_path}\n")

            out.write(f"{'=' * 80}\n\n")
            try:
                content = path.read_text(encoding='utf-8')
                out.write(content)
                if not content.endswith('\n'):
                    out.write('\n')
            except Exception as e:
                out.write(f"[Помилка читання: {e}]\n")

        # ===== СТАТИСТИКА =====
        out.write("\n" + "=" * 80 + "\n")
        out.write("📊 СТАТИСТИКА:\n")
        out.write("=" * 80 + "\n")
        out.write(f"📁 Папок з кодом: {len(my_dirs)}\n")
        out.write(f"📄 Всього файлів: {len(my_files)}\n")

        # Статистика по типах
        stats = {}
        for f in my_files:
            ext = f.suffix or '(без розширення)'
            stats[ext] = stats.get(ext, 0) + 1

        out.write("\n📊 По розширеннях:\n")
        for ext, count in sorted(stats.items()):
            out.write(f"  {ext}: {count} файлів\n")

        # Статистика по папках
        out.write("\n📊 По папках:\n")
        dir_stats = {}
        for f in my_files:
            parent = f.parent.name or 'root'
            dir_stats[parent] = dir_stats.get(parent, 0) + 1

        for dir_name, count in sorted(dir_stats.items()):
            out.write(f"  📁 {dir_name}: {count} файлів\n")

        gitignore_count = len([f for f in my_files if f.name == '.gitignore'])
        out.write(f"\n🔒 .gitignore: {'Є' if gitignore_count > 0 else 'НЕМАЄ'}\n")
        out.write("=" * 80 + "\n")

    print(f"\n✅ ГОТОВО! Файл: {output_file}")
    print(f"📊 Розмір: {output_file.stat().st_size / 1024:.1f} KB")

    # Підсумок
    gitignore_in_dump = any(f.name == '.gitignore' for f in my_files)
    if gitignore_in_dump:
        print(f"🔒 .gitignore УСПІШНО ВКЛЮЧЕНО!")
    else:
        print(f"❌ .gitignore НЕ ВКЛЮЧЕНО!")


if __name__ == "__main__":
    dump_my_structure()