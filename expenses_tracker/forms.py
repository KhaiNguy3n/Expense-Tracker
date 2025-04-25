from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, DecimalField, DateField, SelectField, FloatField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, NumberRange
from expenses_tracker.models import User, Category, Topic
from flask_login import current_user

class RegistrationForm(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is already taken.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is already taken.')

class LoginForm(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class UpdateAccountForm(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    picture = FileField('Update Profile Picture', validators=[FileAllowed(['jpg', 'png'])])
    submit = SubmitField('Update')

    def validate_username(self, username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('That username is already taken.')
    
    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('That email is already taken.')

# Updated Expense Form to handle category and timestamps
class ExpenseForm(FlaskForm):
    topic = SelectField('Topic', choices=[('income', 'Income'), ('expense', 'Expense')], coerce=str)
    category = SelectField('Category', choices=[], coerce=int, validators=[DataRequired()])
    amount = DecimalField('Amount', validators=[DataRequired(), NumberRange(min=0.01, message="Amount must be greater than 0")])
    date = DateField('Date', validators=[DataRequired()])
    description = StringField('Description', validators=[])  # ✅ Remove `DataRequired()`
    submit = SubmitField('Add Expense')

class TransactionForm(FlaskForm):
    amount = FloatField('Amount', validators=[DataRequired()])
    type = SelectField('Type', choices=[('income', 'Income'), ('expense', 'Expense')], validators=[DataRequired()])
    category = SelectField('Category', choices=[
        ('groceries', 'Groceries'),
        ('dining', 'Dining'),
        ('utilities', 'Utilities'),
        ('shopping', 'Shopping'),
        ('entertainment', 'Entertainment'),
        ('transportation', 'Transportation'),
        ('health', 'Health'),
        ('other', 'Other')
    ])
    description = StringField('Description')
    date = DateField('Date', validators=[DataRequired()])

class RequestResetForm(FlaskForm):
    email = StringField('Email',
        validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is None:
            raise ValidationError('There is no account with that email. You must register first.')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password',
        validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')

class CustomCategoryForm(FlaskForm):
    name = StringField('Category Name', 
        validators=[DataRequired(), Length(min=2, max=100)])
    description = StringField('Description', 
        validators=[Length(max=500)])
    type = SelectField('Type', 
        choices=[('income', 'Income'), ('expense', 'Expense')], 
        validators=[DataRequired()])
    submit = SubmitField('Create Category')