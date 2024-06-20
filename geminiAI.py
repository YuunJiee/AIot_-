import os
import base64
import vertexai
from vertexai.generative_models import GenerativeModel, Part
import vertexai.preview.generative_models as generative_models
from dotenv import load_dotenv

def identify_food(image_base64):
    
    load_dotenv()
    # 初始化 Vertex AI
    project_id = os.getenv('PROJECT_ID')
    location = os.getenv('LOCATION')
    vertexai.init(project=project_id, location=location)
    model = GenerativeModel("gemini-1.5-flash-001")

    image = Part.from_data(
        mime_type="image/jpeg",
        data=image_base64
    )

    responses = model.generate_content(
        ["""#zh-tw，請繁體中文說明，請辨識以下食物，我要將食物名稱與數量存進資料庫，例如: 蘋果 2 香蕉 5等等，如果是便當、湯麵之類的複合食物，只要告訴是哪種口味的，像是 雞腿便當 1 海鮮湯麵 1，如果沒有食物或是不是食物，請回傳 錯誤""", image],
        generation_config=generation_config,
        safety_settings=safety_settings,
        stream=True,
    )

    result = ""
    for response in responses:
        result += response.text

    return result.strip()

def chat(msg):
    
    load_dotenv()
    # 初始化 Vertex AI
    project_id = os.getenv('PROJECT_ID')
    location = os.getenv('LOCATION')
    vertexai.init(project=project_id, location=location)
    model = GenerativeModel("gemini-1.5-flash-001")
    
    responses = model.generate_content(
        ["""#zh-tw，請繁體中文回答，你現在是可愛的智能冰箱小冰，以下是使用者問你的問題，請回答""", msg],
        generation_config=generation_config,
        safety_settings=safety_settings,
        stream=True,
    )

    result = ""
    for response in responses:
        result += response.text

    return result.strip()

def read_image_as_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# 配置生成参数
generation_config = {
    "max_output_tokens": 8192,
    "temperature": 1,
    "top_p": 0.95,
}

# 配置安全设置
safety_settings = {
    generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
}



