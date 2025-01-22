# discord_presence.py
import os
import time
from pypresence import Presence
from dotenv import load_dotenv

load_dotenv()
CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")

if not CLIENT_ID:
    raise ValueError("DISCORD_CLIENT_IDが設定されていません。")

# Discord Rich Presenceの初期化
rpc = Presence(CLIENT_ID)
rpc.connect()

def update_status(material_name, material_total_time, material_monthly_time, overall_monthly_time):
    """
    Discordのステータスを更新
    :param material_name: 教材名
    :param material_total_time: 教材ごとの累計時間（分単位）
    :param material_monthly_time: 教材ごとの今月の時間（分単位）
    :param overall_monthly_time: 全体の今月の時間（分単位）
    """
    rpc.update(
        details=f"{material_name}",
        state=f"累計:{int(material_total_time // 60)}時間{int(material_total_time % 60)}分(うち今月:{int(material_monthly_time // 60)}時間{int(material_monthly_time % 60)}分)",
        large_image="image",  # Discord Developer Portalで設定したアセットキー
        large_text=f"今月の総計:{int(overall_monthly_time // 60)}時間{int(overall_monthly_time % 60)}分",
        start=time.time()  # セッションの開始時間
    )
    print(f"Discordステータスを更新しました: {material_name}, 累計:{int(material_total_time)}分, 今月: {int(material_monthly_time)}分, 全体今月: {int(overall_monthly_time)}分")

def clear_status():
    """Discordのステータスをクリア"""
    rpc.clear()
    print("Discordステータスをクリアしました")