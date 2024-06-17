# cook_keyword.py - 爬取食譜並返回結果

import asyncio
import json
import sqlite3
from bs4 import BeautifulSoup
from pyppeteer import launch

class CookKeyword:
    def __init__(self, keyword):
        self.keyword = keyword
        self.conn = sqlite3.connect('icook.db')
        self.c = self.conn.cursor()
        self.c.execute('''CREATE TABLE IF NOT EXISTS recipes
                         (url TEXT, description TEXT, additionalType TEXT, name TEXT, image TEXT)''')

    async def scrape(self):
        try:
            browser = await launch(headless=True)
            page = await browser.newPage()
            await page.goto(f"https://icook.tw/search/{self.keyword}/")
            await page.waitForSelector('script[type="application/ld+json"]')
            html_content = await page.content()
            await browser.close()
        except Exception as e:
            print(f"Error during scraping: {e}")
            return []

        recipes = self.extract_recipes(html_content)[:5]  # 只取前五個相關食譜
        self.save_to_db(recipes)
        return recipes

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
                                        'additionalType': element.get('additionalType', ''),
                                        'name': element.get('name', ''),
                                        'image': element.get('image', '')
                                    }
                                    recipes.append(recipe)
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON: {e}")
                continue

        return recipes

    def save_to_db(self, recipes):
        for recipe in recipes:
            try:
                self.c.execute("INSERT INTO recipes VALUES (?, ?, ?, ?, ?)",
                               (recipe['url'], recipe['description'], recipe['additionalType'], recipe['name'], recipe['image']))
            except sqlite3.Error as e:
                print(f"Error saving recipe to database: {e}")
        self.conn.commit()

    def close_db(self):
        self.conn.close()

def fetch_recipes(keyword):
    cook = CookKeyword(keyword)
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(cook.scrape())
    cook.close_db()
    return result