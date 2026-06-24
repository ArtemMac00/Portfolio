import sqlite3
import datetime
import os
import json
import csv
import sys
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.database import *
from backend.ai_service import ai_suggest_priority

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_task(t):
    priority_colors = {"High": Colors.RED, "Medium": Colors.YELLOW, "Low": Colors.GREEN}
    status_icons = {"InProgress": "🟡", "Done": "✅", "Archived": "📦"}
    color = priority_colors.get(t[4], Colors.RESET)
    icon = status_icons.get(t[5], "❓")
    print(f"{color}[{t[0]}] {t[2]} {icon} [{t[4]}]{Colors.RESET}")
    print(f"    {t[3]}")
    print(f"    📅 Создано: {t[6][:10]} | Обновлено: {t[7][:10]}")
    if t[8]:
        print(f"    ⏰ Дедлайн: {t[8][:10]}")
    print()

def validate_username(username: str) -> bool:
    return bool(re.match(r'^[a-zA-Z0-9_-]{3,20}$', username))

def register_user():
    print(f"\n{Colors.BOLD}{Colors.CYAN}=== РЕГИСТРАЦИЯ НОВОГО ПОЛЬЗОВАТЕЛЯ ==={Colors.RESET}")
    print()
    
    while True:
        username = input("Имя пользователя (3-20 символов, буквы/цифры/_/-): ").strip()
        if not validate_username(username):
            print(f"{Colors.RED}❌ Неверный формат. Используй 3-20 символов (буквы, цифры, _, -){Colors.RESET}")
            continue
        
        existing = get_user(username)
        if existing:
            print(f"{Colors.RED}❌ Пользователь '{username}' уже существует{Colors.RESET}")
            continue
        break
    
    while True:
        password = input("Пароль (минимум 4 символа): ").strip()
        if len(password) < 4:
            print(f"{Colors.RED}❌ Пароль должен быть не менее 4 символов{Colors.RESET}")
            continue
        
        password2 = input("Повторите пароль: ").strip()
        if password != password2:
            print(f"{Colors.RED}❌ Пароли не совпадают{Colors.RESET}")
            continue
        break
    
    if create_user(username, password):
        print(f"{Colors.GREEN}✅ Пользователь '{username}' успешно зарегистрирован!{Colors.RESET}")
        print(f"{Colors.YELLOW}💡 Теперь войдите с новыми данными{Colors.RESET}")
        return True
    else:
        print(f"{Colors.RED}❌ Ошибка при регистрации. Попробуйте снова.{Colors.RESET}")
        return False

def login_user() -> tuple:
    print(f"\n{Colors.BOLD}{Colors.CYAN}=== ВХОД В СИСТЕМУ ==={Colors.RESET}")
    print(f"{Colors.YELLOW}💡 Если у вас нет аккаунта — введите 'register'{Colors.RESET}")
    print()
    
    while True:
        username = input("Имя пользователя: ").strip()
        
        if username.lower() == 'register':
            if register_user():
                continue
            else:
                continue
        
        password = input("Пароль: ").strip()
        
        user = get_user(username)
        if not user:
            print(f"{Colors.RED}❌ Пользователь не найден. Введите 'register' для создания.{Colors.RESET}")
            continue
        
        if user[2] != password:
            print(f"{Colors.RED}❌ Неверный пароль{Colors.RESET}")
            continue
        
        print(f"{Colors.GREEN}✅ Добро пожаловать, {username}!{Colors.RESET}\n")
        return user[0], username

def show_users():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, created_at FROM users ORDER BY id")
    users = cursor.fetchall()
    conn.close()
    
    if not users:
        print(f"{Colors.YELLOW}📭 Нет пользователей{Colors.RESET}")
        return
    
    print(f"\n{Colors.BOLD}{Colors.CYAN}=== СПИСОК ПОЛЬЗОВАТЕЛЕЙ ==={Colors.RESET}")
    print(f"{Colors.BOLD}ID  | Имя пользователя | Дата регистрации{Colors.RESET}")
    print("-" * 50)
    for u in users:
        print(f"{u[0]:2}  | {u[1]:15} | {u[2][:10]}")

def delete_user_from_cli(user_id: int, username: str):
    if username != "admin":
        print(f"{Colors.RED}❌ Только администратор может удалять пользователей{Colors.RESET}")
        return
    
    show_users()
    try:
        target_id = int(input("\nID пользователя для удаления: "))
    except ValueError:
        print(f"{Colors.RED}❌ Введите число{Colors.RESET}")
        return
    
    if target_id == 1:
        print(f"{Colors.RED}❌ Нельзя удалить администратора{Colors.RESET}")
        return
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM task_history WHERE task_id IN (SELECT id FROM tasks WHERE user_id = ?)", (target_id,))
    cursor.execute("DELETE FROM tasks WHERE user_id = ?", (target_id,))
    cursor.execute("DELETE FROM users WHERE id = ?", (target_id,))
    
    if cursor.rowcount > 0:
        conn.commit()
        print(f"{Colors.GREEN}✅ Пользователь удалён!{Colors.RESET}")
    else:
        print(f"{Colors.RED}❌ Пользователь не найден{Colors.RESET}")
    conn.close()

def main():
    init_db()
    
    user_id, username = login_user()
    
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"{Colors.BOLD}{Colors.CYAN}=== 📋 TASKMANAGER CLI ==={Colors.RESET}")
        print(f"{Colors.BLUE}👤 {username}{Colors.RESET}")
        print()
        
        stats = get_stats(user_id)
        overdue = get_overdue_tasks(user_id)
        print(f"   Всего: {stats['total']} | 🟡 {stats['in_progress']} | ✅ {stats['done']} | 📦 {stats['archived']}")
        if overdue:
            print(f"{Colors.RED}⚠️ {len(overdue)} задач просрочено!{Colors.RESET}")
        print()
        
        print("1. Добавить задачу (с AI)")
        print("2. Показать все задачи")
        print("3. Показать 'В работе'")
        print("4. Показать 'Выполнено'")
        print("5. Поиск задач")
        print("6. Изменить статус")
        print("7. Удалить задачу")
        print("8. Экспорт в CSV/JSON")
        print("9. Управление пользователями (админ)")
        print("10. Выход")
        
        choice = input(f"\n{Colors.BOLD}Выбери действие: {Colors.RESET}").strip()
        
        if choice == "1":
            title = input("Название: ").strip()
            if not title:
                print(f"{Colors.RED}❌ Название не может быть пустым{Colors.RESET}")
                input("Нажми Enter...")
                continue
            desc = input("Описание: ").strip()
            print(f"{Colors.YELLOW}🧠 AI определяет приоритет...{Colors.RESET}")
            priority = ai_suggest_priority(desc or title)
            print(f"   Рекомендуемый приоритет: {priority}")
            user_priority = input("Приоритет (High/Medium/Low / Enter для AI): ").strip()
            if user_priority in ["High", "Medium", "Low"]:
                priority = user_priority
            add_task(user_id, title, desc, priority)
            print(f"{Colors.GREEN}✅ Задача добавлена!{Colors.RESET}")
            
        elif choice == "2":
            tasks = get_user_tasks(user_id)
            if not tasks:
                print(f"{Colors.YELLOW}📭 Задач нет{Colors.RESET}")
            else:
                print(f"\n{Colors.BOLD}{Colors.CYAN}=== Все задачи ({len(tasks)}) ==={Colors.RESET}\n")
                for t in tasks:
                    print_task(t)
                    
        elif choice == "3":
            tasks = get_user_tasks(user_id, "InProgress")
            if not tasks:
                print(f"{Colors.YELLOW}📭 Нет задач в работе{Colors.RESET}")
            else:
                print(f"\n{Colors.BOLD}{Colors.CYAN}=== В работе ({len(tasks)}) ==={Colors.RESET}\n")
                for t in tasks:
                    print_task(t)
                    
        elif choice == "4":
            tasks = get_user_tasks(user_id, "Done")
            if not tasks:
                print(f"{Colors.YELLOW}📭 Нет выполненных задач{Colors.RESET}")
            else:
                print(f"\n{Colors.BOLD}{Colors.CYAN}=== Выполнено ({len(tasks)}) ==={Colors.RESET}\n")
                for t in tasks:
                    print_task(t)
                    
        elif choice == "5":
            query = input("Поисковый запрос: ").strip()
            if not query:
                print(f"{Colors.YELLOW}⏳ Введите запрос{Colors.RESET}")
                input("Нажми Enter...")
                continue
            tasks = search_tasks(user_id, query)
            if not tasks:
                print(f"{Colors.YELLOW}📭 Ничего не найдено{Colors.RESET}")
            else:
                print(f"\n{Colors.BOLD}{Colors.CYAN}=== Результаты поиска: '{query}' ({len(tasks)}) ==={Colors.RESET}\n")
                for t in tasks:
                    print_task(t)
                    
        elif choice == "6":
            try:
                task_id = int(input("ID задачи: "))
            except ValueError:
                print(f"{Colors.RED}❌ Введите число{Colors.RESET}")
                input("Нажми Enter...")
                continue
            print("Статусы: InProgress, Done, Archived")
            status = input("Новый статус: ").strip()
            if update_task_status(task_id, user_id, status):
                print(f"{Colors.GREEN}✅ Статус обновлён!{Colors.RESET}")
            else:
                print(f"{Colors.RED}❌ Задача не найдена или неверный статус{Colors.RESET}")
                
        elif choice == "7":
            try:
                task_id = int(input("ID задачи для удаления: "))
            except ValueError:
                print(f"{Colors.RED}❌ Введите число{Colors.RESET}")
                input("Нажми Enter...")
                continue
            if delete_task(task_id, user_id):
                print(f"{Colors.GREEN}✅ Задача удалена!{Colors.RESET}")
            else:
                print(f"{Colors.RED}❌ Задача не найдена{Colors.RESET}")
                
        elif choice == "8":
            print("1. Экспорт в CSV")
            print("2. Экспорт в JSON")
            export_choice = input("Выбери: ")
            tasks = get_user_tasks(user_id)
            if not tasks:
                print(f"{Colors.YELLOW}📭 Нет задач для экспорта{Colors.RESET}")
            elif export_choice == "1":
                export_to_csv(tasks, f"tasks_{username}.csv")
            elif export_choice == "2":
                export_to_json(tasks, f"tasks_{username}.json")
            else:
                print(f"{Colors.RED}❌ Неверный выбор{Colors.RESET}")
                
        elif choice == "9":
            if username != "admin":
                print(f"{Colors.RED}❌ Только администратор имеет доступ к управлению пользователями{Colors.RESET}")
                input("Нажми Enter...")
                continue
            
            print("\n1. Показать всех пользователей")
            print("2. Удалить пользователя")
            print("3. Добавить нового пользователя (быстрая регистрация)")
            sub_choice = input("Выбери: ").strip()
            
            if sub_choice == "1":
                show_users()
            elif sub_choice == "2":
                delete_user_from_cli(user_id, username)
            elif sub_choice == "3":
                register_user()
            else:
                print(f"{Colors.RED}❌ Неверный выбор{Colors.RESET}")
                
        elif choice == "10":
            print(f"{Colors.BLUE}👋 До свидания, {username}!{Colors.RESET}")
            break
            
        else:
            print(f"{Colors.RED}❌ Неверный ввод{Colors.RESET}")
        
        input(f"\n{Colors.YELLOW}Нажми Enter для продолжения...{Colors.RESET}")

def export_to_csv(tasks, filename):
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Title", "Description", "Priority", "Status", "Created At", "Updated At"])
        for t in tasks:
            writer.writerow([t[0], t[2], t[3], t[4], t[5], t[6], t[7]])
    print(f"{Colors.GREEN}✅ Экспортировано в {filename}{Colors.RESET}")

def export_to_json(tasks, filename):
    data = []
    for t in tasks:
        data.append({
            "id": t[0],
            "title": t[2],
            "description": t[3],
            "priority": t[4],
            "status": t[5],
            "created_at": t[6],
            "updated_at": t[7],
            "deadline": t[8]
        })
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"{Colors.GREEN}✅ Экспортировано в {filename}{Colors.RESET}")

if __name__ == "__main__":
    main()
