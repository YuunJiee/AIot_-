import json
import sqlite3
import requests
from bs4 import BeautifulSoup
from linebot.models import TemplateSendMessage, CarouselTemplate, CarouselColumn, URITemplateAction, TextSendMessage

class CookKeyword:
    def __init__(self, keyword):
        self.keyword = keyword
        self.recipes = []  # 初始化 recipes 属性
        db_path = '/tmp/icook.db'
        self.conn = sqlite3.connect(db_path)
        self.c = self.conn.cursor()
        self.c.execute('''CREATE TABLE IF NOT EXISTS recipes
                         (url TEXT, description TEXT, additionalType TEXT, name TEXT, image TEXT, keyword TEXT)''')

    def scrape(self):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        try:
            response = requests.get(f"https://icook.tw/search/{self.keyword}/", headers=headers)
            response.raise_for_status()
            html_content = response.text
        except requests.RequestException as e:
            print(f"请求错误：{e}")
            return []

        self.recipes = self.extract_recipes(html_content)[:5]  # 将爬取到的食谱存储在 self.recipes 中
        self.save_to_db(self.recipes)  # 将食谱存储到数据库
        return self.recipes

    def extract_recipes(self, html_content):
        recipes = []
        soup = BeautifulSoup(html_content, 'html.parser')
        script_tags = soup.find_all('script', type='application/ld+json')

        for script_tag in script_tags:
            try:
                json_data = json.loads(script_tag.string)
                if '@graph' in json_data:
                    for item in json_data['@graph']:
                        if '@type' in item and item['@type'] == 'ItemList' and 'itemListElement' in item:
                            for element in item['itemListElement']:
                                if '@type' in element and element['@type'] == 'ListItem':
                                    recipe = {
                                        'url': element.get('url', ''),
                                        'description': element.get('description', ''),
                                        'additionalType': json.dumps(element.get('additionalType', '')),  # 转换为 JSON 字符串
                                        'name': element.get('name', ''),
                                        'image': element.get('image', '')
                                    }
                                    recipes.append(recipe)
            except json.JSONDecodeError as e:
                print(f"解析 JSON 时出错：{e}")
                continue

        return recipes

    def save_to_db(self, recipes):
        for recipe in recipes:
            try:
                self.c.execute("INSERT INTO recipes VALUES (?, ?, ?, ?, ?, ?)",
                               (recipe['url'], recipe['description'], recipe['additionalType'], recipe['name'], recipe['image'], self.keyword))
            except sqlite3.Error as e:
                print(f"保存食谱到数据库时出错：{e}")
        self.conn.commit()

    def close_db(self):
        self.conn.close()

    def get_carousel_message(self):
        if not self.recipes:
            return TextSendMessage(text=f"未找到关于 '{self.keyword}' 的食谱。")

        columns = []
        for recipe in self.recipes:
            column = CarouselColumn(
                thumbnail_image_url=recipe.get('image', ''),
                title=recipe.get('name', '无标题'),
                text=recipe.get('description', '暂无描述')[:60] or '暂无描述',  # 使用默认文本当描述为空
                actions=[
                    URITemplateAction(
                        label='前往食谱',
                        uri=recipe.get('url', '')
                    )
                ]
            )
            columns.append(column)

        carousel_template = CarouselTemplate(columns=columns)
        return TemplateSendMessage(
            alt_text=f"与 '{self.keyword}' 相关的食谱",
            template=carousel_template
        )
