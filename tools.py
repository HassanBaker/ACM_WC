import random
import string
from functools import wraps
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from flask import flash, url_for, session, redirect


def token_generator(size=20, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


# Register Form Class
class RegisterForm(Form):
    first_name = StringField('first_name', [validators.Length(min=1, max=25)])
    surname = StringField('surname', [validators.Length(min=1, max=25)])
    email = StringField('email', [validators.Length(min=6, max=40)])
    password = PasswordField('password', [
        validators.DataRequired(),
        validators.EqualTo('confirmation_password', message='Passwords do not match'),
        validators.Length(min=6, max=30)
    ])
    confirmation_password = PasswordField('confirmation_password')


# Login Form Class
class LoginForm(Form):
    email = StringField('email', [validators.Length(min=6, max=40)])
    password = PasswordField('password', [
        validators.DataRequired(),
        validators.Length(min=6, max=30)
    ])


def protected(f: object) -> object:
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login')
            return redirect(url_for('register'))

    return wrap
