# routes.py
import sqlite3  # SQLiteデータベース操作
from datetime import datetime  # 時間計算

from flask import render_template, request, redirect
from database import (
    get_categories,
    get_materials,
    get_sessions,
    add_category,
    add_material,
    start_session,
    stop_session,
    update_session,
    delete_session,
)
from utils import format_duration, format_start_time, format_end_time
from utils import format_datetime_for_input


def configure_routes(app):
    @app.route('/')
    def index():
        categories = get_categories()
        materials = get_materials()
        sessions = get_sessions()

        # 累計時間の計算
        with sqlite3.connect('study.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT materials.name, SUM(
                    CASE 
                        WHEN sessions.end_time IS NOT NULL THEN 
                            (julianday(sessions.end_time) - julianday(sessions.start_time)) * 24 * 60
                        ELSE 0
                    END
                ) AS total_minutes
                FROM sessions
                JOIN materials ON sessions.material_id = materials.id
                GROUP BY materials.name
            ''')
            material_totals = cursor.fetchall()

            cursor.execute('''
                SELECT categories.name, SUM(
                    CASE 
                        WHEN sessions.end_time IS NOT NULL THEN 
                            (julianday(sessions.end_time) - julianday(sessions.start_time)) * 24 * 60
                        ELSE 0
                    END
                ) AS total_minutes
                FROM sessions
                JOIN materials ON sessions.material_id = materials.id
                JOIN categories ON materials.category_id = categories.id
                GROUP BY categories.name
            ''')
            category_totals = cursor.fetchall()

        # フォーマット済み累計時間
        formatted_material_totals = [
            (material, format_duration(total)) for material, total in material_totals
        ]
        formatted_category_totals = [
            (category, format_duration(total)) for category, total in category_totals
        ]
        # 進行中のセッションを取得
        with sqlite3.connect('study.db') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT sessions.id, materials.name, sessions.start_time FROM sessions JOIN materials ON sessions.material_id = materials.id WHERE sessions.end_time IS NULL LIMIT 1')
            ongoing_session = cursor.fetchone()

        enriched_sessions = []
        for session in sessions:
            session_id, material_name, start_time, end_time = session
            formatted_start_time = format_start_time(start_time)
            if end_time:
                formatted_end_time = format_end_time(end_time)
                duration = format_duration(
                    (datetime.fromisoformat(end_time) - datetime.fromisoformat(start_time)).total_seconds() / 60
                )
            else:
                formatted_end_time = "未終了"
                duration = "進行中"

            enriched_sessions.append((session_id, material_name, formatted_start_time, formatted_end_time, duration))

        return render_template(
            'index.html',
            categories=categories,
            materials=materials,
            sessions=enriched_sessions,
            material_totals=formatted_material_totals,
            category_totals=formatted_category_totals,
            ongoing_session=ongoing_session,
        )

    @app.route('/add_category', methods=['POST'])
    def add_category_route():
        name = request.form['name']
        add_category(name)
        return redirect('/')

    @app.route('/add_material', methods=['POST'])
    def add_material_route():
        name = request.form['name']
        category_id = request.form['category_id']
        add_material(name, category_id)
        return redirect('/')

    @app.route('/start_session', methods=['POST'])
    def start_session_route():
        material_id = request.form['material_id']
        with sqlite3.connect('study.db') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM sessions WHERE end_time IS NULL LIMIT 1')
            ongoing_session = cursor.fetchone()
            if ongoing_session:
                return "進行中のセッションが既に存在します。", 400
            start_session(material_id)
        return redirect('/')

    @app.route('/stop_session', methods=['POST'])
    def stop_session_route():
        with sqlite3.connect('study.db') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM sessions WHERE end_time IS NULL LIMIT 1')
            ongoing_session = cursor.fetchone()
            if not ongoing_session:
                return "進行中のセッションがありません。", 400
            stop_session()
        return redirect('/')

    @app.route('/edit_session/<int:session_id>')
    def edit_session(session_id):
        session = get_sessions(session_id=session_id)
        materials = get_materials()
        session = (
            session[0],  # ID
            session[1],  # 教材名
            format_datetime_for_input(session[2]),  # 開始時刻
            format_datetime_for_input(session[3]) if session[3] else None,  # 終了時刻
        )
        return render_template('edit_session.html', session=session, materials=materials)
    
    @app.route('/update_session', methods=['POST'])
    def update_session_route():
        session_id = request.form['session_id']
        material_id = request.form['material_id']
        start_time = request.form['start_time']
        end_time = request.form['end_time'] or None  # 空の場合はNoneに設定
        update_session(session_id, material_id, start_time, end_time)
        return redirect('/')

    @app.route('/delete_session', methods=['POST'])
    def delete_session_route():
        session_id = request.form['session_id']
        delete_session(session_id)
        return redirect('/')