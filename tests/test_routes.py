import unittest
from expenses_tracker import app, db
from expenses_tracker.models import User, Category, Topic
from flask_bcrypt import Bcrypt
from flask_login import current_user

class TestRoutes(unittest.TestCase):
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

    def test_home_page(self):
        with self.app:
            response = self.app.get('/')
            self.assertEqual(response.status_code, 200)  # Should show landing page

    def test_register_route(self):
        with self.app:
            response = self.app.post('/register', data={
                'username': 'testuser',
                'email': 'test@example.com',
                'password': 'password123',
                'confirm_password': 'password123'
            }, follow_redirects=True)
            self.assertEqual(response.status_code, 200)

    def test_login_route(self):
        with self.app:
            # First create a user
            user = User(
                username='testuser',
                email='test@example.com',
                password=self.bcrypt.generate_password_hash('password123').decode('utf-8')
            )
            db.session.add(user)
            db.session.commit()

            # Then try to login
            response = self.app.post('/login', data={
                'email': 'test@example.com',
                'password': 'password123'
            }, follow_redirects=True)
            self.assertEqual(response.status_code, 200)

    def test_logout_route(self):
        with self.app:
            # First create and login a user
            user = User(
                username='testuser',
                email='test@example.com',
                password=self.bcrypt.generate_password_hash('password123').decode('utf-8')
            )
            db.session.add(user)
            db.session.commit()

            # Login
            self.app.post('/login', data={
                'email': 'test@example.com',
                'password': 'password123'
            })

            response = self.app.get('/logout', follow_redirects=True)
            self.assertEqual(response.status_code, 200)

    def test_dashboard_route(self):
        with self.app:
            # First create and login a user
            user = User(
                username='testuser',
                email='test@example.com',
                password=self.bcrypt.generate_password_hash('password123').decode('utf-8')
            )
            db.session.add(user)
            db.session.commit()

            # Login
            self.app.post('/login', data={
                'email': 'test@example.com',
                'password': 'password123'
            })

            # Then try to access dashboard
            response = self.app.get('/index')
            self.assertEqual(response.status_code, 302)  # Should redirect to login if not authenticated

if __name__ == '__main__':
    unittest.main() 