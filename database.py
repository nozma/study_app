# database.py
import sqlite3
from datetime import datetime, timedelta

def init_db():
    with sqlite3.connect('study.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category_id INTEGER,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                material_id INTEGER,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                FOREIGN KEY (material_id) REFERENCES materials(id)
            )
        ''')
        conn.commit()

def get_categories():
    with sqlite3.connect('study.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM categories')
        return cursor.fetchall()

def get_materials():
    with sqlite3.connect('study.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT materials.id, materials.name, categories.name
            FROM materials
            JOIN categories ON materials.category_id = categories.id
        ''')
        return cursor.fetchall()

def get_sessions(session_id=None, order_by=None, start_date=None):
    """
    セッションを取得する関数。
    - session_id: 指定された場合、そのIDのセッションを取得
    - order_by: ソート条件を指定（例: "start_time DESC"）
    - start_date: 指定された日付以降のセッションを取得
    """
    with sqlite3.connect('study.db') as conn:
        cursor = conn.cursor()

        query = '''
            SELECT sessions.id, materials.name, sessions.start_time, sessions.end_time
            FROM sessions
            JOIN materials ON sessions.material_id = materials.id
        '''
        params = []

        # 特定のsession_idを取得
        if session_id:
            query += ' WHERE sessions.id = ?'
            params.append(session_id)

        # 開始日でフィルタリング
        elif start_date:
            query += ' WHERE sessions.start_time >= ?'
            params.append(start_date)

        # ソート条件を追加
        if order_by:
            query += f' ORDER BY {order_by}'

        cursor.execute(query, params)

        # session_idが指定された場合は1件、そうでない場合は複数件返す
        if session_id:
            return cursor.fetchone()
        return cursor.fetchall()

def add_category(name):
    with sqlite3.connect('study.db') as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO categories (name) VALUES (?)', (name,))
        conn.commit()

def add_material(name, category_id):
    with sqlite3.connect('study.db') as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO materials (name, category_id) VALUES (?, ?)', (name, category_id))
        conn.commit()

def start_session(material_id):
    with sqlite3.connect('study.db') as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO sessions (material_id, start_time) VALUES (?, ?)', (material_id, datetime.now()))
        conn.commit()

def stop_session():
    with sqlite3.connect('study.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM sessions WHERE end_time IS NULL LIMIT 1')
        ongoing_session = cursor.fetchone()
        if ongoing_session:
            cursor.execute('UPDATE sessions SET end_time = ? WHERE id = ?', (datetime.now(), ongoing_session[0]))
            conn.commit()

def update_session(session_id, material_id, start_time, end_time):
    with sqlite3.connect('study.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE sessions
            SET material_id = ?, start_time = ?, end_time = ?
            WHERE id = ?
        ''', (material_id, start_time, end_time, session_id))
        conn.commit()

def delete_session(session_id):
    with sqlite3.connect('study.db') as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM sessions WHERE id = ?', (session_id,))
        conn.commit()


def get_total_study_time(material_id):
    """
    指定された教材の累計勉強時間を取得（分単位）
    """
    with sqlite3.connect("study.db") as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT SUM(
                (JULIANDAY(end_time) - JULIANDAY(start_time)) * 24 * 60
            ) AS total_minutes
            FROM sessions
            WHERE material_id = ? AND end_time IS NOT NULL
        ''', (material_id,))
        result = cursor.fetchone()
        return int(result[0]) if result[0] else 0

def get_monthly_study_time(material_id):
    """
    指定された教材の今月の勉強時間を取得（分単位）
    """
    current_month_start = datetime.now().replace(day=1).isoformat()  # 今月の初日
    with sqlite3.connect("study.db") as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT SUM(
                (JULIANDAY(end_time) - JULIANDAY(start_time)) * 24 * 60
            ) AS total_minutes
            FROM sessions
            WHERE material_id = ? AND end_time IS NOT NULL AND start_time >= ?
        ''', (material_id, current_month_start))
        result = cursor.fetchone()
        return int(result[0]) if result[0] else 0

def get_past_days_study_time(material_id, days=30):
    """
    指定された教材の過去N日間の勉強時間を取得（分単位）
    :param material_id: 教材のID
    :param days: 何日間の勉強時間を取得するか（デフォルト: 30日）
    :return: 指定期間内の合計勉強時間（分単位）
    """
    past_days_start = (datetime.now() - timedelta(days=days)).isoformat()  # N日前の日時を取得
    with sqlite3.connect("study.db") as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT SUM(
                (JULIANDAY(end_time) - JULIANDAY(start_time)) * 24 * 60
            ) AS total_minutes
            FROM sessions
            WHERE material_id = ? AND end_time IS NOT NULL AND start_time >= ?
        ''', (material_id, past_days_start))
        result = cursor.fetchone()
        return int(result[0]) if result[0] else 0

def get_overall_past_days_study_time(days=30):
    """
    すべての教材の過去N日間の勉強時間を取得（分単位）
    :param days: 何日間の勉強時間を取得するか（デフォルト: 30日）
    :return: 指定期間内の合計勉強時間（分単位）
    """
    past_days_start = (datetime.now() - timedelta(days=days)).isoformat()  # N日前の日時を取得
    with sqlite3.connect("study.db") as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT SUM(
                (JULIANDAY(end_time) - JULIANDAY(start_time)) * 24 * 60
            ) AS total_minutes
            FROM sessions
            WHERE end_time IS NOT NULL AND start_time >= ?
        ''', (past_days_start, ))
        result = cursor.fetchone()
        return int(result[0]) if result[0] else 0

def get_material_image_key(material_id):
    """
    指定された教材のDiscord用画像キーを取得
    """
    with sqlite3.connect("study.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT discord_image_key FROM materials WHERE id = ?", (material_id,))
        result = cursor.fetchone()
        return result[0] if result and result[0] else ""
