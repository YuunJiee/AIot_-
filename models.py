from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# 用户模型
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    line_id = db.Column(db.String(50), unique=True, nullable=False)
    esp32_id = db.Column(db.String(50), db.ForeignKey('esp32_device.esp32_id'), nullable=True)

# 食品保质期模型
class FoodExpiration(db.Model):
    __tablename__ = 'food_expiration'
    id = db.Column(db.Integer, primary_key=True)
    food_name = db.Column(db.String(100), nullable=False)
    shelf_life_days = db.Column(db.Integer, nullable=False)

# 食品模型
class Food(db.Model):
    __tablename__ = 'food'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    added_date = db.Column(db.DateTime, default=datetime.utcnow)
    expiration_date = db.Column(db.DateTime, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    expiration_id = db.Column(db.Integer, db.ForeignKey('food_expiration.id'), nullable=True)

    def set_expiration_date(self):
        if self.expiration_id is not None:
            food_expiration = FoodExpiration.query.filter_by(id=self.expiration_id).first()
            if food_expiration:
                self.expiration_date = self.added_date + timedelta(days=food_expiration.shelf_life_days)

class SensorData(db.Model):
    __tablename__ = 'sensor_data'
    id = db.Column(db.Integer, primary_key=True)
    temperature = db.Column(db.Float, nullable=False)
    humidity = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    esp32_id = db.Column(db.String(50), db.ForeignKey('esp32_device.esp32_id'), nullable=False)

class ESP32Device(db.Model):
    __tablename__ = 'esp32_device'
    id = db.Column(db.Integer, primary_key=True)
    esp32_id = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(100), nullable=True)
    sensor_data = db.relationship('SensorData', backref='device', lazy=True)


def init_db():
    db.create_all()
    if FoodExpiration.query.first() is None:  # 检查表格是否已有数据
        foods = [
            {'food_name': '香蕉', 'shelf_life_days': 9},
            {'food_name': '麵包', 'shelf_life_days': 14},
            {'food_name': '雞蛋', 'shelf_life_days': 35},
            {'food_name': '牛奶', 'shelf_life_days': 7},
            {'food_name': '馬鈴薯', 'shelf_life_days': 35},
            {'food_name': '菠菜', 'shelf_life_days': 7},
            {'food_name': '番茄', 'shelf_life_days': 7},
            {'food_name': 'test', 'shelf_life_days': 1},
            {'food_name': 'test2', 'shelf_life_days': 1}
        ]
        for food in foods:
            new_food = FoodExpiration(**food)
            db.session.add(new_food)
        db.session.commit()
    if ESP32Device.query.first() is None:
        esp32_data = ESP32Device(
            esp32_id = "123456"
        )
        db.session.add(esp32_data)
        db.session.commit()

# 用于添加食物条目的函数
def add_food(name, quantity, user_id, expiration_id):
    # 检查expiration_id是否有效
    food_expiration = FoodExpiration.query.filter_by(id=expiration_id).first()
    if not food_expiration:
        print(f"错误: 无效的expiration_id {expiration_id}")
        return "错误: 提供的expiration_id无效"
    
    new_food = Food(name=name, quantity=quantity, user_id=user_id, expiration_id=expiration_id)
    new_food.set_expiration_date()
    db.session.add(new_food)
    db.session.commit()
    return "食品添加成功"
