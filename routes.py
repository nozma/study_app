import sqlite3
from datetime import datetime, timedelta

from flask import render_template, request, redirect, flash
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
    get_total_study_time,
    get_monthly_study_time,
    get_overall_past_days_study_time,
    get_past_days_study_time
)
from utils import format_duration, format_start_time, format_start_date, format_end_time
from utils import format_datetime_for_input
from discord_presence import update_status, clear_status

def configure_routes(app):
    @app.route('/')
    def home():
        return redirect('/study') # デフォルトは勉強ページ

    @app.route('/study')
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

        # 昨日の日付を取得
        yesterday = datetime.now() - timedelta(days=1)

        # 昨日以降のセッションを取得（降順でソート）
        all_sessions = get_sessions(order_by="start_time DESC")
        recent_sessions = [
            session for session in all_sessions
            if datetime.fromisoformat(session[2]) >= yesterday
        ]

        enriched_sessions = []
        for session in recent_sessions:
            session_id, material_name, start_time, end_time = session
            formatted_start_time = format_start_time(start_time)
            formatted_start_date = format_start_date(start_time)
            if end_time:
                formatted_end_time = format_end_time(end_time)
                duration = format_duration(
                    (datetime.fromisoformat(end_time) - datetime.fromisoformat(start_time)).total_seconds() / 60
                )
            else:
                formatted_end_time = "未終了"
                duration = "進行中"

            enriched_sessions.append((formatted_start_date, material_name, formatted_start_time, formatted_end_time, duration, session_id))

        return render_template(
            'study.html',
            active_page='study',
            categories=categories,
            materials=materials,
            sessions=enriched_sessions,
            material_totals=formatted_material_totals,
            category_totals=formatted_category_totals,
            ongoing_session=ongoing_session,
        )

    @app.route('/history')
    def history():
        # 昨日より前のセッションを取得（降順でソート）
        yesterday = datetime.now() - timedelta(days=1)
        all_sessions = get_sessions(order_by="start_time DESC")
        old_sessions = [
            session for session in all_sessions
            if datetime.fromisoformat(session[2]) < yesterday
        ]

        enriched_sessions = []
        for session in old_sessions:
            session_id, material_name, start_time, end_time = session
            formatted_start_time = format_start_time(start_time)
            formatted_start_date = format_start_date(start_time)
            if end_time:
                formatted_end_time = format_end_time(end_time)
                duration = format_duration(
                    (datetime.fromisoformat(end_time) - datetime.fromisoformat(start_time)).total_seconds() / 60
                )
            else:
                formatted_end_time = "未終了"
                duration = "進行中"

            enriched_sessions.append((formatted_start_date, material_name, formatted_start_time, formatted_end_time, duration, session_id))

        return render_template('history.html', sessions=enriched_sessions, active_page='history')

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
            cursor.execute("SELECT name, discord_image_key FROM materials WHERE id = ?", (material_id,))
            material = cursor.fetchone()
            material_name = material[0]
            image_key = material[1] if material[1] else "image"  # 画像キーが設定されていない場合はデフォルトを使用
        # 過去30日の勉強時間を取得
        overall_recent_time = get_overall_past_days_study_time(days=30)
        # 教材ごとの累計時間と過去30日間の時間を取得
        material_total_time = get_total_study_time(material_id)
        material_recent_time = get_past_days_study_time(material_id, days=30)
        # セッション開始
        start_session(material_id)
        # Discordステータスを更新
        update_status(material_name, material_total_time, material_recent_time, overall_recent_time, image_key)
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
        clear_status()
        return redirect('/')

    @app.route('/edit_session/<int:session_id>')
    def edit_session(session_id):
        session = get_sessions(session_id=session_id)
        materials = get_materials()
        session = {
            "id": session[0],  # ID
            "material": session[1],  # 教材名
            "start_time": format_datetime_for_input(session[2]),  # 開始時刻
            "end_time": format_datetime_for_input(session[3]) if session[3] else None,  # 終了時刻
        }
        return render_template('edit_session.html', session=session, materials=materials)
    
    @app.route('/update_session', methods=['POST'])
    def update_session_route():
        session_id = request.form['session_id']
        material_id = request.form['material_id']
        start_time = request.form['start_time']
        end_time = request.form['end_time'] or None  # 空の場合はNoneに設定
        update_session(session_id, material_id, start_time, end_time)
        next_page = request.args.get('next') or '/'
        return redirect(next_page)

    @app.route('/delete_session', methods=['POST'])
    def delete_session_route():
        session_id = request.form['session_id']
        delete_session(session_id)
        next_page = request.args.get('next') or '/'
        return redirect(next_page)

    @app.route('/categories', methods=['GET', 'POST'])
    def manage_categories():
        with sqlite3.connect("study.db") as conn:
            cursor = conn.cursor()

            # POSTリクエストでカテゴリを追加
            if request.method == 'POST':
                name = request.form['name']
                cursor.execute("INSERT INTO categories (name, is_active) VALUES (?, 1)", (name,))
                conn.commit()
            
            # カテゴリの一覧を取得
            cursor.execute("SELECT id, name, is_active FROM categories")
            categories = cursor.fetchall()

        return render_template('categories.html', categories=categories, active_page='categories')

    @app.route('/categories/edit/<int:category_id>', methods=['POST'])
    def edit_category(category_id):
        name = request.form['name']
        is_active = request.form.get('is_active', '0') == '1'
        with sqlite3.connect("study.db") as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE categories SET name = ?, is_active = ? WHERE id = ?", (name, int(is_active), category_id))
            conn.commit()
        return redirect('/categories')

    @app.route('/categories/delete/<int:category_id>', methods=['POST'])
    def delete_category(category_id):
        with sqlite3.connect("study.db") as conn:
            cursor = conn.cursor()
            # 該当カテゴリが教材に使用されているか確認
            cursor.execute("SELECT COUNT(*) FROM materials WHERE category_id = ?", (category_id,))
            if cursor.fetchone()[0] == 0:
                cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
                conn.commit()
                flash("カテゴリを削除しました。", "success")
            else:
                flash("このカテゴリは教材に使用されているため削除できません。")
        return redirect('/categories')

    @app.route('/materials', methods=['GET', 'POST'])
    def manage_materials():
        with sqlite3.connect("study.db") as conn:
            cursor = conn.cursor()

            # POSTリクエストで教材を追加
            if request.method == 'POST':
                name = request.form['name']
                category_id = request.form['category_id']
                discord_image_key = request.form['discord_image_key'] if 'discord_image_key' in request.form else ""
                cursor.execute("INSERT INTO materials (name, category_id, discord_image_key, is_active) VALUES (?, ?, ?, 1)", (name, category_id, discord_image_key))
                conn.commit()

            # 教材の一覧を取得
            cursor.execute("""
                SELECT materials.id, materials.name, materials.is_active, materials.discord_image_key, categories.name AS category_name
                FROM materials
                JOIN categories ON materials.category_id = categories.id
            """)
            materials = cursor.fetchall()

            # カテゴリの一覧を取得（教材追加用）
            cursor.execute("SELECT id, name FROM categories WHERE is_active = 1")
            categories = cursor.fetchall()

        return render_template('materials.html', materials=materials, categories=categories, active_page='materials')

    @app.route('/materials/edit/<int:material_id>', methods=['POST'])
    def edit_material(material_id):
        name = request.form['name']
        category_id = request.form['category_id']
        discord_image_key = request.form['discord_image_key']
        is_active = request.form.get('is_active', '0') == '1'
        with sqlite3.connect("study.db") as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE materials SET name = ?, category_id = ?, discord_image_key = ?, is_active = ? WHERE id = ?", (name, category_id, discord_image_key, int(is_active), material_id))
            conn.commit()
        return redirect('/materials')

    @app.route('/materials/delete/<int:material_id>', methods=['POST'])
    def delete_material(material_id):
        with sqlite3.connect("study.db") as conn:
            cursor = conn.cursor()
            # 該当教材がセッションに使用されているか確認
            cursor.execute("SELECT COUNT(*) FROM sessions WHERE material_id = ?", (material_id,))
            if cursor.fetchone()[0] == 0:
                cursor.execute("DELETE FROM materials WHERE id = ?", (material_id,))
                conn.commit()
                flash("教材を削除しました。", "success")
            else:
                flash("この教材はセッションに使用されているため削除できません。")
        return redirect('/materials')

    @app.route('/exercise')
    def exercise_page():
        """運動の記録ページ（直近 7 日の記録を含む）"""
        with sqlite3.connect("study.db") as conn:
            cursor = conn.cursor()
            
            # 運動メニュー一覧を取得
            cursor.execute('''
                SELECT exercises.id, exercises.name, exercise_categories.name, exercises.value_type
                FROM exercises
                JOIN exercise_categories ON exercises.category_id = exercise_categories.id
                WHERE exercises.is_active = 1
            ''')
            exercises = cursor.fetchall()

            # 直近 7 日間の運動記録を取得
            cursor.execute("""
                SELECT 
                    DATE(exercise_sessions.record_time),  -- 記録時間（日付のみ）
                    exercise_categories.name,            -- 部位カテゴリ
                    exercises.name,                      -- 運動メニュー
                    exercise_sessions.value,             -- 記録値
                    exercise_sessions.value_type         -- 記録タイプ（回 or 分）
                FROM exercise_sessions
                JOIN exercises ON exercise_sessions.exercise_id = exercises.id
                JOIN exercise_categories ON exercises.category_id = exercise_categories.id
                WHERE DATE(exercise_sessions.record_time) >= DATE('now', '-6 days')  -- 直近7日間
                ORDER BY exercise_sessions.record_time DESC
            """)
            recent_logs = cursor.fetchall()

        return render_template("exercise.html", exercises=exercises, recent_logs=recent_logs, active_page="exercise")

    @app.route('/exercises')
    def exercises():
        """運動メニュー一覧を表示"""
        with sqlite3.connect("study.db") as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT exercises.id, exercises.name, exercise_categories.name, exercises.value_type
                FROM exercises
                JOIN exercise_categories ON exercises.category_id = exercise_categories.id
                WHERE exercises.is_active = 1
            ''')
            exercises = cursor.fetchall()

            cursor.execute("SELECT id, name FROM exercise_categories WHERE is_active = 1")
            categories = cursor.fetchall()

        return render_template("exercises.html", exercises=exercises, categories=categories, active_page="exercises")

    @app.route('/add_exercise', methods=['POST'])
    def add_exercise():
        """新しい運動メニューを追加"""
        name = request.form['name']
        category_id = request.form['category_id']
        value_type = request.form['value_type']  # 'reps' or 'minutes'

        with sqlite3.connect("study.db") as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO exercises (name, category_id, value_type) VALUES (?, ?, ?)", (name, category_id, value_type))
            conn.commit()

        return redirect('/exercises')

    @app.route('/exercise_categories')
    def exercise_categories():
        """運動の部位カテゴリ一覧を表示"""
        with sqlite3.connect("study.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM exercise_categories WHERE is_active = 1")
            categories = cursor.fetchall()
        return render_template("exercise_categories.html", categories=categories, active_page="exercise_categories")

    @app.route('/add_exercise_category', methods=['POST'])
    def add_exercise_category():
        """新しい部位カテゴリを追加"""
        name = request.form['name']
        with sqlite3.connect("study.db") as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO exercise_categories (name) VALUES (?)", (name,))
            conn.commit()
        return redirect('/exercise_categories')

    @app.route('/log_exercise', methods=['POST'])
    def log_exercise():
        """運動の記録を追加"""
        exercise_id = request.form['exercise_id']
        value = request.form['value']
        value_type = request.form['value_type']

        with sqlite3.connect("study.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO exercise_sessions (exercise_id, value, value_type)
                VALUES (?, ?, ?)
            """, (exercise_id, value, value_type))
            conn.commit()

        return redirect('/exercise')

    @app.route('/exercise_log')
    def exercise_log():
        """運動の記録一覧を表示"""
        with sqlite3.connect("study.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    DATE(exercise_sessions.record_time),  -- 記録時間（日付のみ）
                    exercise_categories.name,            -- 部位カテゴリ
                    exercises.name,                      -- 運動メニュー
                    exercise_sessions.value,             -- 記録値
                    exercise_sessions.value_type,        -- 記録タイプ（回 or 分）
                    exercise_sessions.id                 -- 運動の記録 ID（編集用）
                FROM exercise_sessions
                JOIN exercises ON exercise_sessions.exercise_id = exercises.id
                JOIN exercise_categories ON exercises.category_id = exercise_categories.id
                ORDER BY exercise_sessions.record_time DESC
            """)
            logs = cursor.fetchall()
        return render_template("exercise_log.html", logs=logs, active_page="exercise_log")

    @app.route('/edit_exercise_log/<int:log_id>', methods=['GET', 'POST'])
    def edit_exercise_log(log_id):
        """運動の記録を編集"""
        with sqlite3.connect("study.db") as conn:
            cursor = conn.cursor()
            
            if request.method == 'POST':
                new_date = request.form['record_date']
                new_exercise_id = request.form['exercise_id']
                new_value = request.form['value']
                
                cursor.execute("""
                    UPDATE exercise_sessions
                    SET record_time = ?, exercise_id = ?, value = ?
                    WHERE id = ?
                """, (new_date, new_exercise_id, new_value, log_id))
                conn.commit()
                
                return redirect('/exercise_log')

            else:
                # 編集する記録を取得（記録日を YYYY-MM-DD 形式に変換）
                cursor.execute("""
                    SELECT 
                        exercise_sessions.id, 
                        STRFTIME('%Y-%m-%d', exercise_sessions.record_time),  -- 日付を YYYY-MM-DD 形式で取得
                        exercise_sessions.exercise_id, 
                        exercise_sessions.value, 
                        exercises.value_type,
                        exercises.name, 
                        exercise_categories.name  -- カテゴリ名も取得
                    FROM exercise_sessions
                    JOIN exercises ON exercise_sessions.exercise_id = exercises.id
                    JOIN exercise_categories ON exercises.category_id = exercise_categories.id
                    WHERE exercise_sessions.id = ?
                """, (log_id,))
                log = cursor.fetchone()

                # データが取得できなかった場合のエラーハンドリング
                if log is None:
                    flash("指定された記録が見つかりません。", "error")
                    return redirect('/exercise_log')

                # 運動メニューのリストを取得
                cursor.execute("""
                    SELECT exercises.id, exercises.name, exercise_categories.name
                    FROM exercises
                    JOIN exercise_categories ON exercises.category_id = exercise_categories.id
                """)
                exercises = cursor.fetchall()

        return render_template("edit_exercise_log.html", log=log, exercises=exercises)

    @app.route('/edit_exercise_category/<int:category_id>', methods=['GET', 'POST'])
    def edit_exercise_category(category_id):
        """運動カテゴリの編集"""
        with sqlite3.connect("study.db") as conn:
            cursor = conn.cursor()
            if request.method == 'POST':
                new_name = request.form['name']
                cursor.execute("UPDATE exercise_categories SET name = ? WHERE id = ?", (new_name, category_id))
                conn.commit()
                return redirect('/exercise_categories')
            else:
                cursor.execute("SELECT id, name FROM exercise_categories WHERE id = ?", (category_id,))
                category = cursor.fetchone()
        return render_template("edit_exercise_category.html", category=category)

    @app.route('/delete_exercise_category/<int:category_id>', methods=['POST'])
    def delete_exercise_category(category_id):
        """運動カテゴリの削除（カテゴリを使用しているメニューがある場合は削除不可）"""
        with sqlite3.connect("study.db") as conn:
            cursor = conn.cursor()
            # 関連する運動メニューがあるか確認
            cursor.execute("SELECT COUNT(*) FROM exercises WHERE category_id = ?", (category_id,))
            count = cursor.fetchone()[0]

            if count > 0:
                flash("このカテゴリを使用している運動メニューがあるため削除できません。", "error")
            else:
                cursor.execute("DELETE FROM exercise_categories WHERE id = ?", (category_id,))
                conn.commit()

        return redirect('/exercise_categories')

    @app.route('/edit_exercise/<int:exercise_id>', methods=['GET', 'POST'])
    def edit_exercise(exercise_id):
        """運動メニューの編集"""
        with sqlite3.connect("study.db") as conn:
            cursor = conn.cursor()
            if request.method == 'POST':
                new_name = request.form['name']
                category_id = request.form['category_id']
                value_type = request.form['value_type']
                cursor.execute("UPDATE exercises SET name = ?, category_id = ?, value_type = ? WHERE id = ?", 
                            (new_name, category_id, value_type, exercise_id))
                conn.commit()
                return redirect('/exercises')
            else:
                cursor.execute("SELECT id, name, category_id, value_type FROM exercises WHERE id = ?", (exercise_id,))
                exercise = cursor.fetchone()

                cursor.execute("SELECT id, name FROM exercise_categories")
                categories = cursor.fetchall()

        return render_template("edit_exercise.html", exercise=exercise, categories=categories)

    @app.route('/delete_exercise/<int:exercise_id>', methods=['POST'])
    def delete_exercise(exercise_id):
        """運動メニューの削除（このメニューを記録しているセッションがある場合は削除不可）"""
        with sqlite3.connect("study.db") as conn:
            cursor = conn.cursor()
            # 関連するセッションがあるか確認
            cursor.execute("SELECT COUNT(*) FROM exercise_sessions WHERE exercise_id = ?", (exercise_id,))
            count = cursor.fetchone()[0]

            if count > 0:
                flash("この運動メニューを使用している記録があるため削除できません。", "error")
            else:
                cursor.execute("DELETE FROM exercises WHERE id = ?", (exercise_id,))
                conn.commit()

        return redirect('/exercises')