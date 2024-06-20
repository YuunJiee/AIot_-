# app.py - 主應用入口，處理 Flask 路由和啟動應用
from flask import Flask, request, jsonify, render_template, send_from_directory
from models import init_db, db, SensorData
from line_bot import handle_line_bot
from apscheduler.schedulers.background import BackgroundScheduler
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

@app.route("/", methods=['GET'])
def home():
    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

@app.route('/tmp/<filename>')
def uploaded_file(filename):
    return send_from_directory('tmp', filename)

@app.route("/webhook", methods=['POST'])
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

@app.route('/post_data', methods=['POST'])
def post_data():
    data = request.json
    temperature = data.get('temperature')
    humidity = data.get('humidity')
    esp32_id = data.get('esp32_id')
    
    sensor_data = SensorData(
        temperature=temperature,
        humidity=humidity,
        esp32_id=esp32_id
    )
    db.session.add(sensor_data)
    db.session.commit()
    
    return jsonify({"status": "success", "message": "Data received"}), 200

# 初始化数据库和填充食品保质期表

if __name__ == "__main__":
    with app.app_context():
        init_db()

    # 設置定時任務，檢查即將過期的食物並提醒用戶
    scheduler = BackgroundScheduler()
    scheduler.start()

    app.run(port=5000, debug=True)
