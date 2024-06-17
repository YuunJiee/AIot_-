# line_bot.py - 處理 LINE BOT 的訊息處理和回應

import os
import json
from dotenv import load_dotenv
from linebot import LineBotApi, WebhookHandler
from linebot.models import TextSendMessage, ImageSendMessage, TemplateSendMessage, ButtonsTemplate, MessageTemplateAction
import vertexai
from vertexai.generative_models import GenerativeModel
from models import db, User
from food_service import add_food, get_foods, get_expiring_foods

load_dotenv()  # 加載 .env 文件中的環境變數

line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# 初始化 Vertex AI
project_id = os.getenv('PROJECT_ID')
location = os.getenv('LOCATION')
vertexai.init(project=project_id, location=location)

# 加載 Gemini 模型
multimodal_model = GenerativeModel(model_name="gemini-1.5-flash-001")

def test_env():
    print(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
    print(os.getenv('LINE_CHANNEL_SECRET'))
    print(os.getenv('LOCATION'))


def handle_line_bot(body, signature):
    """處理來自 LINE BOT 的請求"""
    handler.handle(body, signature)
    json_data = json.loads(body)
    tk = json_data['events'][0]['replyToken']
    type = json_data['events'][0]['message']['type']
    user_id = json_data['events'][0]['source']['userId']
    user_name = line_bot_api.get_profile(user_id).display_name

    test_env()
    
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
        if msg == "新增食物":
            reply_message = []
            reply_message.append(
                TemplateSendMessage(
                    alt_text='Buttons template',
                    template=ButtonsTemplate(
                        title='新增食物',
                        text='你想用什麼方式增加呢?',
                        actions=[
                            MessageTemplateAction(
                                label='文字輸入',
                                text='文字輸入新增食物',
                            ),
                            MessageTemplateAction(
                                label='圖片辨識',
                                text='圖片辨識新增食物',
                            ),
                        ]
                    )
                )
            )
        elif msg == "查詢冰箱":
            foods = get_foods(user)
            if foods:
                food_list = '\n'.join([f"{food.name} - {food.quantity}" for food in foods])
                reply_message = TextSendMessage(text=f"你的冰箱裡有以下食材：\n{food_list}")
            else:
                reply_message = TextSendMessage(text="你的冰箱裡沒有食物。")
        elif msg == "查詢食譜":
            reply_message = TextSendMessage(text="請輸入: 查詢 食材1 食材2...")
        elif msg.startswith("查詢 "):
            user_message = msg.replace("食譜", "").strip()
            recipes = get_recipe_recommendation(user_message)
            if recipes:
                reply_message = TextSendMessage(text=recipes)
            else:
                reply_message = TextSendMessage(text="未找到相關食譜。")
        elif msg == "文字輸入新增食物":
            reply_message = TextSendMessage(text="請輸入: 新增 食物名稱 數量（數量為選填）")
        elif msg.startswith("新增 "):
            parts = msg.split()
            # 确保至少有两个元素：动作和食物名称
            if len(parts) >= 2:
                if len(parts) > 2 and parts[-1].isdigit():  # 检查是否有提供数量，且是数字
                    quantity = int(parts[-1])
                    food_name = ' '.join(parts[1:-1])
                else:
                    quantity = 1  # 默认数量
                    food_name = ' '.join(parts[1:])
                reply_text = add_food(food_name, user.id, quantity)
                reply_message = TextSendMessage(text=reply_text)
            else:
                reply_message = TextSendMessage(text="請輸入食物名稱。例如：'新增 蘋果 3'")
        elif msg == "圖片辨識新增食物":
            reply_message = TextSendMessage(text="請輸入一張圖片")
        else:
            reply_message = TextSendMessage(text="請輸入有效的指令！")
    elif type == 'image':
        # 下載圖片
        message_id = json_data['events'][0]['message']['id']
        message_content = line_bot_api.get_message_content(message_id)
        image_path = f'tempImg/{message_id}.jpg'
        with open(image_path, 'wb') as fd:
            for chunk in message_content.iter_content():
                fd.write(chunk)
        reply_message = TextSendMessage(text='食物辨識功能正在開發中。')
    else:
        reply_message = TextSendMessage(text='無法處理此類訊息。')
    
    line_bot_api.reply_message(tk, reply_message)

def send_expiration_reminders():
    """檢查即將過期的食物並提醒用戶"""
    expiring_foods = get_expiring_foods()
    for food in expiring_foods:
        user = User.query.get(food.user_id)
        if user:
            message = f"提醒：你的 {food.name} 即將在 {food.expiration_date.strftime('%Y-%m-%d')} 過期，請盡快食用。"
            line_bot_api.push_message(user.line_id, TextSendMessage(text=message))

def get_recipe_recommendation(ingredients):
    try:
        print(f"Generating recipe for ingredients: {ingredients}")
        
        # 查询 Vertex AI 的生成模型
        response = multimodal_model.generate_content(
            [f"我有以下食材：{ingredients}。請推薦2~5個常見又簡單的食譜，並標記可能需要購買的食材，用JSON格式輸出。"]
        )
        
        json_content = response.text
        print(json_content)
        
        # try:
            # 解析 JSON 内容
            # recipe_data = json.loads(json_content)
            
            # # 解析并格式化食谱信息
            # recipes = recipe_data.get("recipes", [])
            # formatted_recipes = ""
            # for recipe in recipes:
            #     name = recipe.get("name", "未知食譜")
            #     description = recipe.get("description", "")
            #     ingredients_list = recipe.get("ingredients", [])
            #     instructions = recipe.get("instructions", [])
                
            #     formatted_recipes += f"食譜名稱: {name}\n"
            #     formatted_recipes += f"描述: {description}\n"
            #     formatted_recipes += "材料:\n"
            #     for ingredient in ingredients_list:
            #         formatted_recipes += f"- {ingredient}\n"
            #     formatted_recipes += "步驟:\n"
            #     for step in instructions:
            #         formatted_recipes += f"{step}\n"
            #     formatted_recipes += "\n"

            # print(formatted_recipes)
            #return formatted_recipes
        # except json.JSONDecodeError as e:
        #     print(f"Error decoding JSON: {e}")
        #     return "無法解析生成的食譜。"
    
        # if response and response.responses:
        #     recipe = response.responses[0].text.strip()
        # else:
        #     recipe = "沒有找到相關的食譜建議。"
        
        # print(f"Gemini response: {recipe}")
        # return recipe
        
        return json_content
    except Exception as e:
        print(f"Error when calling Vertex AI: {e}")
        return "很抱歉，我無法生成食譜建議。"