from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_migrate import Migrate

app = Flask(__name__)
app.config['SECRET_KEY'] = 'adc184bf5a300e53354d8bf219d6a19d'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'

db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

from expenses_tracker import routes
from expenses_tracker.models import Category, Topic, User, db
import logging

app.logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
app.logger.addHandler(handler)

def insert_predefined_data():
    # Create or get a system user
    system_user = User.query.filter_by(username='system').first()
    if not system_user:
        system_user = User(
            username='system',
            email='system@example.com',
            password=bcrypt.generate_password_hash('systempassword').decode('utf-8')
        )
        db.session.add(system_user)
        try:
            db.session.commit()
            app.logger.info("System user created successfully")
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error creating system user: {str(e)}")
            raise

    # Define only two topics
    predefined_topics = [
        ('Income', 'income'),
        ('Expense', 'expense')
    ]

    for topic_name, topic_type in predefined_topics:
        topic = Topic.query.filter_by(name=topic_name).first()
        if not topic:
            new_topic = Topic(name=topic_name, type=topic_type)
            db.session.add(new_topic)
    try:
        db.session.commit()
        app.logger.info("Predefined topics inserted successfully")
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error inserting predefined topics: {str(e)}")
        raise

    # Define categories associated with topics
    predefined_categories = [
        ('Salary', 'income', 'Monthly salary', 'Income'),
        ('Investments', 'income', 'Investment returns and growth', 'Income'),
        ('Utilities', 'expense', 'Recurring expenses like rent, electricity, water', 'Expense'),
        ('Food', 'expense', 'Restaurants, groceries, etc.', 'Expense'),
        ('Transport', 'expense', 'Car, public transit, fuel', 'Expense'),
        ('Entertainment', 'expense', 'Movies, games, hobbies', 'Expense'),
        ('Shopping', 'expense', 'Clothing, electronics, etc.', 'Expense'),
        ('Personal Care', 'expense', 'Haircuts, gym, health products', 'Expense'),
        ('Health & Medical', 'expense', 'Doctor visits, medicine', 'Expense'),
    ]

    for category_name, category_type, category_desc, topic_name in predefined_categories:
        topic = Topic.query.filter_by(name=topic_name).first()
        category = Category.query.filter_by(name=category_name, user_id=system_user.id).first()
        if not category and topic:
            new_category = Category(
                name=category_name,
                type=category_type,
                description=category_desc,
                user_id=system_user.id,  # Assign to system user
                topic_id=topic.id
            )
            db.session.add(new_category)
    try:
        db.session.commit()
        app.logger.info("Predefined categories inserted successfully")
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error inserting predefined categories: {str(e)}")
        raise

with app.app_context():
    db.create_all()
    insert_predefined_data()