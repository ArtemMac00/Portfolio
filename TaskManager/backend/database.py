import sqlite3
import datetime
from typing import Optional, List, Tuple, Dict

DB_NAME = "tasks.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            priority TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            deadline TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            old_status TEXT,
            new_status TEXT,
            changed_at TEXT NOT NULL,
            FOREIGN KEY (task_id) REFERENCES tasks (id)
        )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            ("admin", "admin123", datetime.datetime.now().isoformat())
        )
    
    conn.commit()
    conn.close()

def get_user(username: str) -> Optional[Tuple]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    return user

def create_user(username: str, password: str) -> bool:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, password, datetime.datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def add_task(user_id: int, title: str, description: str, priority: str, deadline: str = None) -> bool:
    if priority not in ["High", "Medium", "Low"]:
        priority = "Medium"
    
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO tasks (user_id, title, description, priority, status, created_at, updated_at, deadline)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, title, description, priority, "InProgress", now, now, deadline))
    task_id = cursor.lastrowid
    
    cursor.execute('''
        INSERT INTO task_history (task_id, old_status, new_status, changed_at)
        VALUES (?, ?, ?, ?)
    ''', (task_id, None, "InProgress", now))
    
    conn.commit()
    conn.close()
    return True

def get_user_tasks(user_id: int, status: str = None) -> List[Tuple]:
    conn = get_connection()
    cursor = conn.cursor()
    if status:
        cursor.execute(
            "SELECT * FROM tasks WHERE user_id = ? AND status = ? ORDER BY created_at DESC",
            (user_id, status)
        )
    else:
        cursor.execute(
            "SELECT * FROM tasks WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def search_tasks(user_id: int, query: str) -> List[Tuple]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM tasks 
        WHERE user_id = ? AND (title LIKE ? OR description LIKE ?)
        ORDER BY created_at DESC
    ''', (user_id, f'%{query}%', f'%{query}%'))
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def update_task_status(task_id: int, user_id: int, new_status: str) -> bool:
    if new_status not in ["InProgress", "Done", "Archived"]:
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now().isoformat()
    
    cursor.execute("SELECT status FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
    old_status = row[0]
    
    cursor.execute('''
        UPDATE tasks SET status = ?, updated_at = ? WHERE id = ? AND user_id = ?
    ''', (new_status, now, task_id, user_id))
    
    cursor.execute('''
        INSERT INTO task_history (task_id, old_status, new_status, changed_at)
        VALUES (?, ?, ?, ?)
    ''', (task_id, old_status, new_status, now))
    
    conn.commit()
    conn.close()
    return True

def delete_task(task_id: int, user_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success

def get_stats(user_id: int) -> Dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ?", (user_id,))
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'InProgress'", (user_id,))
    in_progress = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'Done'", (user_id,))
    done = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'Archived'", (user_id,))
    archived = cursor.fetchone()[0]
    conn.close()
    return {"total": total, "in_progress": in_progress, "done": done, "archived": archived}

def get_overdue_tasks(user_id: int) -> List[Tuple]:
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now()
    three_days_ago = (now - datetime.timedelta(days=3)).isoformat()
    cursor.execute('''
        SELECT * FROM tasks 
        WHERE user_id = ? AND status = 'InProgress' AND created_at < ?
        ORDER BY created_at ASC
    ''', (user_id, three_days_ago))
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def get_avg_completion_time(user_id: int) -> float:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT created_at, updated_at FROM tasks 
        WHERE user_id = ? AND status = 'Done'
    ''', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return 0
    
    total_days = 0
    for row in rows:
        created = datetime.datetime.fromisoformat(row[0])
        updated = datetime.datetime.fromisoformat(row[1])
        total_days += (updated - created).days
    return round(total_days / len(rows), 1)

def get_priority_distribution(user_id: int) -> Dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT priority, COUNT(*) FROM tasks WHERE user_id = ?
        GROUP BY priority
    ''', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}

def get_status_timeline(user_id: int) -> List[Tuple]:
    conn = get_connection()
    cursor = conn.cursor()
    week_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()
    cursor.execute('''
        SELECT date(changed_at), new_status, COUNT(*) 
        FROM task_history 
        WHERE task_id IN (SELECT id FROM tasks WHERE user_id = ?) 
        AND changed_at > ?
        GROUP BY date(changed_at), new_status
        ORDER BY date(changed_at)
    ''', (user_id, week_ago))
    rows = cursor.fetchall()
    conn.close()
    return rows
