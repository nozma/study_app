# app.py
from flask import Flask
from routes import configure_routes
from database import init_db
from datetime import datetime

app = Flask(__name__)

@app.template_filter('datetimeformat')
def datetimeformat(value, fmt="default"):
    dt = datetime.fromisoformat(value)
    if fmt == "iso":
        return dt.isoformat()
    return dt.strftime('%Y年%m月%d日 %H:%M')

# Configure routes
configure_routes(app)

if __name__ == "__main__":
    init_db()  # Initialize the database
    app.run(debug=True)
