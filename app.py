# app.py
from flask import Flask
from routes import configure_routes
from database import init_db
from datetime import datetime
import signal
import sys
import os

app = Flask(__name__)

@app.template_filter('datetimeformat')
def datetimeformat(value, fmt="default"):
    dt = datetime.fromisoformat(value)
    if fmt == "iso":
        return dt.isoformat()
    return dt.strftime('%Y年%m月%d日 %H:%M')

# Configure routes
configure_routes(app)


def handle_exit_signal(signum, frame):
    print(f"シグナル {signum} を受信しました。サーバーを終了します...")
    sys.exit(0)

if __name__ == "__main__":
    # メインプロセスでのみシグナルハンドリングを登録
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        signal.signal(signal.SIGINT, handle_exit_signal)  # Ctrl+C
        signal.signal(signal.SIGTERM, handle_exit_signal)  # 終了リクエスト

    try:
        app.run(debug=True)
    except Exception as e:
        print(f"エラーが発生しました: {e}")
    finally:
        print("サーバーが停止しました。ポートが解放されたか確認してください。")