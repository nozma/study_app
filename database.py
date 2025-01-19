# database.py
import sqlite3
from datetime import datetime

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

def get_sessions(session_id=None):
    with sqlite3.connect('study.db') as conn:
        cursor = conn.cursor()
        if session_id:
            cursor.execute('''
                SELECT sessions.id, materials.name, sessions.start_time, sessions.end_time
                FROM sessions
                JOIN materials ON sessions.material_id = materials.id
                WHERE sessions.id = ?
            ''', (session_id,))
            return cursor.fetchone()
        else:
            cursor.execute('''
                SELECT sessions.id, materials.name, sessions.start_time, sessions.end_time
                FROM sessions
                JOIN materials ON sessions.material_id = materials.id
            ''')
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