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

def update_status(material_name, material_total_time, material_recent_time, overall_recent_time, image_key):
    """
    Discord のステータスを更新
    :param material_name: 教材名
    :param material_total_time: 教材ごとの累計時間（分単位）
    :param material_recent_time: 教材ごとの過去30日間の勉強時間（分単位）
    :param overall_recent_time: 全体の過去30日間の時間（分単位）
    :param image_key: Discord Art Assets に登録された画像のアセットキー
    """
    state_text = f"勉強中:{material_name}"
    details_text = f"{int(material_recent_time // 60)}時間/30日 ({int(material_total_time // 60)}時間/合計)"

    rpc.update(
        state=state_text,
        details=details_text,
        large_image=image_key if image_key else "default_image",  # 画像キーが設定されていない場合はデフォルトを使用
        large_text=f"勉強中: {material_name}",
        start=time.time()
    )
    print(f"Discordステータスを更新しました:\n{state_text}\n{details_text}\n画像: {image_key}")

def clear_status():
    """Discordのステータスをクリア"""
    rpc.clear()
    print("Discordステータスをクリアしました")