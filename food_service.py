# food_service.py - 處理食物相關的業務邏輯

from models import db, Food, FoodExpiration
from datetime import datetime, timedelta

def add_food(food_name, user_id, quantity=1):
    """添加食品到資料庫並設定正確的過期日期"""
    # 從 FoodExpiration 表中查找相應的食品保質期
    food_expiration = FoodExpiration.query.filter_by(food_name=food_name).first()
    if not food_expiration:
        print(f"錯誤: 無法找到名為 {food_name} 的食品保質期信息")
        return "錯誤: 提供的食品名稱無效"

    # 檢查是否已經有相同的食品
    existing_food = Food.query.filter_by(name=food_name, user_id=user_id).first()
    if existing_food:
        existing_food.quantity += quantity  # 累加數量
        db.session.commit()
        return f"已更新 {food_name} 的數量。現有數量: {existing_food.quantity}"

    # 計算過期日期
    expiration_date = datetime.now() + timedelta(days=food_expiration.shelf_life_days)

    # 創建新的食品項目
    new_food = Food(name=food_name, quantity=quantity, added_date=datetime.now(), expiration_date=expiration_date, user_id=user_id)
    db.session.add(new_food)
    db.session.commit()
    return "食品添加成功"


def get_foods(user):
    """獲取用戶冰箱中的所有食物"""
    return Food.query.filter_by(user_id=user.id).all()

def get_expiring_foods():
    """獲取即將過期的食物（前一天）"""
    tomorrow = datetime.now() + timedelta(days=1)
    return Food.query.filter(Food.expiration_date == tomorrow).all()
