# food_service.py - 處理食物相關的業務邏輯

from sqlalchemy import func
from models import db, Food, FoodExpiration
from datetime import datetime, timedelta

def add_food(food_name, user_id, quantity=1):
    """添加食品到資料庫並設定正確的過期日期"""
    # 從 FoodExpiration 表中查找相應的食品保質期
    food_expiration = FoodExpiration.query.filter_by(food_name=food_name).first()
    
    # 如果找不到保質期資訊，預設為 7 天並保存新的食品保質期
    if not food_expiration:
        food_expiration = FoodExpiration(food_name=food_name, shelf_life_days=7)
        db.session.add(food_expiration)
        db.session.commit()

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
    return f"{food_name} 添加成功"


def remove_food(food_name, user_id, quantity=1):
    """從資料庫中刪除或減少食品的數量"""
    # 查找相應的食品項目
    food = Food.query.filter_by(name=food_name, user_id=user_id).first()
    if not food:
        return "錯誤: 您的冰箱中沒有這種食品。"

    # 檢查刪除的數量是否有效
    if quantity > food.quantity:
        return f"錯誤: 你不能刪除超過現有數量的 {food_name}。目前數量: {food.quantity}"

    # 減少食品數量或刪除記錄
    if quantity < food.quantity:
        food.quantity -= quantity
        message = f"已減少 {food_name} 的數量。剩餘數量: {food.quantity}"
    else:
        db.session.delete(food)
        message = f"已刪除 {food_name}。"

    db.session.commit()
    return message

def get_foods(user):
    """獲取用戶冰箱中的所有食物，並按有效期限排序"""
    return Food.query.filter_by(user_id=user.id).order_by(Food.expiration_date).all()

def get_expiring_food(user_id):
    """查詢一天內即將到期的食物，包括數量，並格式化日期"""
    now = datetime.now()
    one_day_later = now + timedelta(days=1)

    # 查詢即將到期的食品
    expiring_foods = Food.query.filter(
        Food.user_id == user_id,
        Food.expiration_date >= now,
        Food.expiration_date <= one_day_later
    ).all()

    # 生成食品名稱、數量及到期時間的列表，日期格式為 YYYY/MM/DD HH:MM
    food_list = [f"{food.name}, 剩餘數量：{food.quantity} \n到期時間：{food.expiration_date.strftime('%Y/%m/%d %H:%M')}" for food in expiring_foods]
    return food_list
