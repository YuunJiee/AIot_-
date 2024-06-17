from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 用户模型
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    line_id = db.Column(db.String(50), unique=True, nullable=False)

# 食品保质期模型
class FoodExpiration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    food_name = db.Column(db.String(100), nullable=False)
    shelf_life_days = db.Column(db.Integer, nullable=False)

# 食品模型
class Food(db.Model):
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


# 初始化数据库和填充食品保质期表
def init_db():
    with app.app_context():
        db.create_all()
        if FoodExpiration.query.first() is None:  # 检查表格是否已有数据
            foods = [
                {'food_name': '香蕉', 'shelf_life_days': 9},
                {'food_name': '麵包', 'shelf_life_days': 14},
                {'food_name': '雞蛋', 'shelf_life_days': 35},
                {'food_name': '牛奶', 'shelf_life_days': 7},
                {'food_name': '馬鈴薯', 'shelf_life_days': 35},
                {'food_name': '菠菜', 'shelf_life_days': 7},
                {'food_name': '番茄', 'shelf_life_days': 7}
            ]
            for food in foods:
                new_food = FoodExpiration(**food)
                db.session.add(new_food)
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

# 调用初始化数据库函数
init_db()
