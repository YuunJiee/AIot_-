import googlemaps
import json
import os
import matplotlib
import matplotlib.pyplot as plt
from linebot.models import TextSendMessage   
from linebot import LineBotApi, WebhookHandler
from linebot.models import *
from models import User, SensorData, ESP32Device, db
from food_service import add_food, get_foods, get_expiring_food, remove_food
from geminiAI import identify_food, read_image_as_base64, chat
from cook_keyword import CookKeyword
from dotenv import load_dotenv
from datetime import datetime, timedelta
import matplotlib.font_manager as fm

load_dotenv()  # 加載 .env 文件中的環境變量

line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))
gmaps = googlemaps.Client(key=os.getenv('PLACE_API_KEY'))

def handle_line_bot(body, signature):
    """處理來自 LINE BOT 的請求"""
    json_data = json.loads(body)
    tk = json_data['events'][0]['replyToken']
    type = json_data['events'][0]['message']['type']
    user_id = json_data['events'][0]['source']['userId']
    user_name = line_bot_api.get_profile(user_id).display_name

    # 檢查用戶是否存在
    user = User.query.filter_by(line_id=user_id).first()
    if not user:
        # 新增用戶
        new_user = User(name=user_name, line_id=user_id)
        db.session.add(new_user)
        db.session.commit()
        line_bot_api.reply_message(tk, TextSendMessage(text=f"Hello {user_name}, 您的虛擬冰箱剛建立完成，請重新選擇功能！"))
        return
    
    if type == 'text':
        msg = json_data['events'][0]['message']['text']
        if msg == "食物管理":
            reply_message = []
            reply_message.append(
                TemplateSendMessage(
                    alt_text='Buttons template',
                    template=ButtonsTemplate(
                        title='食物管理',
                        text='你想進行什麼操作？',
                        actions=[
                            MessageTemplateAction(
                                label='文字輸入新增食物',
                                text='文字輸入新增食物',
                            ),
                            MessageTemplateAction(
                                label='圖片辨識新增食物',
                                text='圖片辨識新增食物',
                            ),
                            MessageTemplateAction(
                                label='刪除食物',
                                text='刪除食物',
                            ),
                            MessageTemplateAction(
                                label='查詢即期品',
                                text='查詢即期品',
                            )
                        ]
                    )
                )
            )
        elif msg == "刪除食物":
            reply_message = TextSendMessage(text="請輸入: 刪除 食物名稱 數量（數量為選填）")
        elif msg.startswith("刪除 "):
            parts = msg[3:].split()
            foods = food_list(parts)
            try:
                foods = food_list(parts)
                reply_texts = []
                for food_name, quantity in foods:
                    result = remove_food(food_name, user.id, quantity)
                    reply_texts.append(result)
                reply_message = TextSendMessage(text="\n".join(reply_texts))
            except ValueError as e:
                reply_message = TextSendMessage(text="格式錯誤，請輸入: 刪除 食物名稱 數量（數量為選填）")
        elif msg == "查詢即期品":
            # 實現查詢即期品功能的地方
            expiring_foods = get_expiring_food(user.id)
            if expiring_foods:
                reply_message = TextSendMessage(text="即將到期的食物: \n" + "\n".join(expiring_foods))
            else:
                reply_message = TextSendMessage(text="沒有即將到期的食物。")

        elif msg == "看看冰箱":
            
            reply_message = []
            reply_message.append(
                TemplateSendMessage(
                    alt_text='Buttons template',
                    template=ButtonsTemplate(
                        title='看看冰箱',
                        text='你想進行什麼操作？',
                        actions=[
                            MessageTemplateAction(
                                label='冰箱現況',
                                text='冰箱現況',
                            ),
                            MessageTemplateAction(
                                label='查看庫存',
                                text='查看庫存',
                            ),
                        ]
                    )
                )
            )
        elif msg == "查看庫存":
            foods = get_foods(user)
            if foods:
                matplotlib.rc('font', family='Microsoft JhengHei')
                fig, ax = plt.subplots(figsize=(10, len(foods) * 0.6 + 2)) 
                ax.axis('tight')
                ax.axis('off')
                
                table_data = [["名稱", "數量", "有效期限"]]
                for food in foods:
                    table_data.append([food.name, food.quantity, food.expiration_date.strftime("%Y-%m-%d")])
                
                table = ax.table(cellText=table_data, cellLoc='center', loc='center', cellColours=[['#f5f5f5']*3]*len(table_data))
                table.auto_set_font_size(False)
                table.set_fontsize(16)
                table.scale(1, 2)
                
                for i in range(len(table_data)):
                    for j in range(3):
                        cell = table[(i, j)]
                        cell.set_edgecolor('#000000')  # 邊框顏色
                        cell.set_linewidth(0.5)  # 邊框寬度
                        cell.set_facecolor('#e0f7fa' if i == 0 else '#ffffff')  # 頭部背景色 & 行背景色
                        cell.set_text_props(weight='bold' if i == 0 else 'normal')  # 字體樣式

                plt.savefig('tmp/fridge.png')

                image_url = 'https://1e3c-2401-e180-88a0-121f-f07f-6413-8366-17b7.ngrok-free.app/tmp/fridge.png'
                reply_message = ImageSendMessage(
                    original_content_url=image_url,
                    preview_image_url=image_url
                )
            else:
                reply_message = TextSendMessage(text="你的冰箱裡沒有食物。")
        elif msg == "冰箱現況":
            esp32 = ESP32Device.query.filter_by(esp32_id=user.esp32_id).first()
            if user.esp32_id is None:
                reply_message = TextSendMessage(text="您還没有設置感應器ID，請查看機器上的id來連接，請輸入: 設定 123456")
            elif not esp32:
                reply_message = TextSendMessage(text="感應器ID設定錯誤，請查看機器上的id來重新連接，請輸入: 設定 123456")
            else:
                sensor_data = SensorData.query.filter_by(esp32_id=user.esp32_id).order_by(SensorData.timestamp.desc()).first()
                if sensor_data:
                    now = datetime.utcnow()
                    if now - sensor_data.timestamp < timedelta(minutes=10):
                        temperature = sensor_data.temperature
                        humidity = sensor_data.humidity
                        alert_messages = []
                        if temperature > 7:
                            alert_messages.append("您的冰箱溫度異常，正常應該是7度以下")
                        if humidity > 78:
                            alert_messages.append("您的冰箱濕度異常，正常應該是78%以下")
                        if alert_messages:
                            alert_text = "，".join(alert_messages)
                            reply_message = TextSendMessage(
                                text=f"警告：{alert_text}。目前溫度是 {temperature} 度，濕度是 {humidity}%。"
                            )
                        else:
                            reply_message = TextSendMessage(
                                text=f"你的冰箱目前溫度是 {temperature} 度，濕度是 {humidity}%。"
                            )
                    else:
                        reply_message = TextSendMessage(
                            text="感應器數據超過10分鐘未更新，可能存在連線問題。請檢查WiFi連接狀態。"
                        )
                else:
                    reply_message = TextSendMessage(text="目前没有檢測到冰箱到溫溼度數據。請確認您的感應器是否已正确連接。")
        elif msg.startswith("設定 "):
            esp32_id = msg[3:]
            esp32 = ESP32Device.query.filter_by(esp32_id=esp32_id).first()
            if not esp32:
                reply_message = TextSendMessage(text=f"找不到這個感應器ID，請重新確認。")
            else:
                user.esp32_id = esp32_id
                db.session.commit()
                reply_message = TextSendMessage(text=f"感應器ID 已設為 {esp32_id}")
        elif msg == "查詢食譜":
            foods = get_foods(user)
            if foods:
                food_items = [QuickReplyButton(action=MessageAction(label=f"{food.name} ({food.quantity})", text=f"查詢 {food.name} 食譜")) for food in foods[:13]]  # 确保项目数不超过13个
                reply_message = TextSendMessage(text="您可以輸入: 查詢 食物1 食物2，也可以點選您冰箱內食物來查詢：", quick_reply=QuickReply(items=food_items))
            else:
                reply_message = TextSendMessage(text="你的冰箱裡沒有食物。您可以輸入: 查詢 食物1 食物2...")
        elif msg == "文字輸入新增食物":
            reply_message = TextSendMessage(text="請輸入: 新增 食物名稱 數量（數量為選填），例如：新增 蘋果 3 香蕉 5")
        elif msg == "功能介紹":
            with open('static/txt/introduction.txt', 'r', encoding='utf-8') as file:
                text_content = file.read()
            reply_message = TextSendMessage(text=text_content)

        elif msg.startswith("新增 "):
            parts = msg[3:].split()
            try:
                foods = food_list(parts)
                reply_texts = []
                for food_name, quantity in foods:
                    result = add_food(food_name, user.id, quantity)
                    reply_texts.append(result)
                reply_message = TextSendMessage(text="\n".join(reply_texts))
            except ValueError as e:
                reply_message = TextSendMessage(text="格式錯誤，請輸入: 新增 食物名稱 數量（數量為選填）")
        elif msg == "圖片辨識新增食物":
            reply_message = TextSendMessage(text="請輸入一張圖片")
        elif msg.startswith("查詢 "):
            keywords = msg.split(" ")[1:]
            cook = CookKeyword(" ".join(keywords))
            recipes = cook.scrape()
            if recipes:
                columns = []
                for recipe in recipes:
                    column = CarouselColumn(
                        thumbnail_image_url=recipe.get('image', ''),
                        title=recipe.get('name', '無標題'),
                        text=recipe.get('description', '暫無描述')[:60] or '暫無描述',
                        actions=[
                            URITemplateAction(
                                label='前往食譜',
                                uri=recipe.get('url', '')
                            )
                        ]
                    )
                    columns.append(column)

                carousel_template = CarouselTemplate(columns=columns[:10])  # 只顯示前十個食譜
                reply_message = TemplateSendMessage(
                    alt_text=f"與 '{' '.join(keywords)}' 相關的食譜",
                    template=carousel_template
                )
            else:
                reply_message = TextSendMessage(text=f"未找到關於 '{' '.join(keywords)}' 的食譜。")
        else:
            try:
                return_message = chat(msg)
                reply_message = TextSendMessage(text=return_message)
            except Exception as e:
                reply_message = TextSendMessage(text=f"小冰不懂你的問題，請重新試試看")
    elif type == 'image':
        # 下載圖片
        message_id = json_data['events'][0]['message']['id']
        message_content = line_bot_api.get_message_content(message_id)
        image_path = f'tmp/image.jpg'
        with open(image_path, 'wb') as fd:
            for chunk in message_content.iter_content():
                fd.write(chunk)
        
        # 調用 Gemini API 進行圖片辨識
        image_data_base64 = read_image_as_base64(image_path)
        food_name = identify_food(image_data_base64)

        #print(food_name)
        if (food_name != '錯誤'):
            foods = food_list(food_name.split())
            reply_texts = []
            for food_name, quantity in foods:
                result = add_food(food_name, user.id, quantity)
                reply_texts.append(result)
            reply_message = TextSendMessage(text="\n".join(reply_texts))
        else:
            reply_message = TextSendMessage(text=f"無法辨識到食物，請重傳")
    elif type == 'location':
        lat = json_data['events'][0]['message']['latitude']
        long = json_data['events'][0]['message']['longitude']
        places_result = gmaps.places_nearby(location=(lat, long), radius=1000, type='restaurant')
        if places_result['results']:
            columns = []
            for place in places_result['results'][:10]:
                photo_reference = place.get('photos', [{}])[0].get('photo_reference', '')
                photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo_reference}&key={os.getenv('PLACE_API_KEY')}" if photo_reference else ''
                column = CarouselColumn(
                    thumbnail_image_url=photo_url,
                    title=place.get('name', '無標題'),
                    text=place.get('vicinity', '無地址'),
                    actions=[
                        URITemplateAction(
                            label='查看地圖',
                            uri=f"https://www.google.com/maps/search/?api=1&query={place['geometry']['location']['lat']},{place['geometry']['location']['lng']}"
                        )
                    ]
                )
                columns.append(column)
            
            carousel_template = CarouselTemplate(columns=columns)
            reply_message = TemplateSendMessage(
                alt_text="附近的餐廳",
                template=carousel_template
            )
        else:
            reply_message = TextSendMessage(text="未找到附近的餐廳。")
    
    else:
        reply_message = TextSendMessage(text='無法處理此類信息。')
    
    line_bot_api.reply_message(tk, reply_message)

def food_list(parts):
    foods = []
    i = 0
    while i < len(parts):
        if i < len(parts) - 1 and parts[i+1].isdigit():
            # 當前部分是食物名稱，下一部分是數量
            food_name = parts[i]
            quantity = int(parts[i+1])
            i += 2  # 跳過名稱和數量
        else:
            # 當前部分是食物名稱，數量為預設值1
            food_name = parts[i]
            quantity = 1
            i += 1  # 跳過名稱
        
        foods.append((food_name, quantity))
    return foods
