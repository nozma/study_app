# utils.py
from datetime import datetime

def format_duration(minutes):
    """分を時間:分の形式にフォーマット"""
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{hours}時間{mins}分"

def format_start_time(start_time):
    """開始時刻を yyyy年mm月dd日 hh時mm分 の形式にフォーマット"""
    start = datetime.fromisoformat(start_time)
    return start.strftime("%Y年%m月%d日 %H時%M分")

def format_end_time(end_time):
    """終了時刻を hh時mm分 の形式にフォーマット"""
    if end_time:
        end = datetime.fromisoformat(end_time)
        return end.strftime("%H時%M分")
    return "未終了"

def format_datetime_for_input(dt_string):
    """Datetimeをinput[type=datetime-local]形式に変換"""
    if dt_string:
        dt = datetime.fromisoformat(dt_string)
        return dt.strftime('%Y-%m-%dT%H:%M')
    return None

