import unittest
from expenses_tracker import app, db
from expenses_tracker.models import User, Category, Topic
from flask_bcrypt import Bcrypt

class TestModels(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
        app.config['WTF_CSRF_ENABLED'] = False
        self.app = app.test_client()
        self.ctx = app.app_context()
        self.ctx.push()
        db.create_all()
        self.bcrypt = Bcrypt(app)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_user_creation(self):
        with self.app:
            user = User(
                username='testuser',
                email='test@example.com',
                password=self.bcrypt.generate_password_hash('password123').decode('utf-8')
            )
            db.session.add(user)
            db.session.commit()

            self.assertEqual(user.username, 'testuser')
            self.assertEqual(user.email, 'test@example.com')
            self.assertTrue(self.bcrypt.check_password_hash(user.password, 'password123'))

    def test_category_creation(self):
        with self.app:
            user = User(
                username='testuser',
                email='test@example.com',
                password=self.bcrypt.generate_password_hash('password123').decode('utf-8')
            )
            db.session.add(user)
            db.session.commit()

            topic = Topic(name='Expense', type='expense')
            db.session.add(topic)
            db.session.commit()

            category = Category(
                name='Food',
                type='expense',
                description='Food expenses',
                user_id=user.id,
                topic_id=topic.id
            )
            db.session.add(category)
            db.session.commit()

            self.assertEqual(category.name, 'Food')
            self.assertEqual(category.type, 'expense')
            self.assertEqual(category.user_id, user.id)
            self.assertEqual(category.topic_id, topic.id)

    def test_topic_creation(self):
        with self.app:
            topic = Topic(name='Income', type='income')
            db.session.add(topic)
            db.session.commit()

            self.assertEqual(topic.name, 'Income')
            self.assertEqual(topic.type, 'income')

if __name__ == '__main__':
    unittest.main() 