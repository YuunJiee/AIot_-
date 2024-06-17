# app.py - 主應用入口，處理 Flask 路由和啟動應用

from flask import Flask, request
from models import app, init_db
from line_bot import handle_line_bot, send_expiration_reminders
from apscheduler.schedulers.background import BackgroundScheduler
from linebot.exceptions import InvalidSignatureError
import os

@app.route("/", methods=['POST'])
def linebot():
    """處理來自 LINE 的請求"""
    body = request.get_data(as_text=True)
    signature = request.headers.get('X-Line-Signature')
    if not signature:
        return 'Missing signature', 400
    try:
        handle_line_bot(body, signature)
    except:
        print(body) # 如果發生錯誤，印出收到的內容
    return 'OK'

if __name__ == "__main__":
    # 只在資料庫不存在時初始化資料庫
    if not os.path.exists('database.db'):
        init_db()

    # 設置定時任務，檢查即將過期的食物並提醒用戶
    scheduler = BackgroundScheduler()
    scheduler.add_job(send_expiration_reminders, 'interval', days=1)
    scheduler.start()

    app.run()










