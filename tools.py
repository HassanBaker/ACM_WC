import random
import shutil
import string
from functools import wraps
import pandas as pd
import os
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from flask import flash, url_for, session, redirect
from config import csv_file_string_entries, ALLOWED_EXTENSIONS, submission_dir


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


# Change Password Form Class
class ChangePasswordForm(Form):
    token = StringField('token', [validators.Length(min=20, max=20)])
    password = PasswordField('password', [
        validators.DataRequired(),
        validators.EqualTo('confirmation_password', message='Passwords do not match'),
        validators.Length(min=6, max=30)
    ])
    confirmation_password = PasswordField('confirmation_password')


def protected(f: object) -> object:
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login')
            return redirect(url_for('register'))

    return wrap


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


class FileDoesNotParseToCSV(Exception):
    def __init__(self):
        Exception.__init__(self, "File is not correct csv format")


class WrongNumberOfRows(Exception):
    def __init__(self, number_of_rows):
        Exception.__init__(self, "Number of rows must be 7, instead got %d" % number_of_rows)


class WrongNumberOfColumns(Exception):
    def __init__(self, number_of_columns):
        Exception.__init__(self, "Number of columns must be 64, instead got %d" % number_of_columns)


def can_cast_to_int(string_input):
    try:
        int(string_input)
        return True
    except ValueError:
        return False


def string_is_in_list(string_input, check_list):
    return string_input in check_list


def errors_in_submission_file(file):
    """
    Parses a csv file submitted to make sure that it is of the correct format
    :param file:
    :return: list of errors, or else raises relevant exceptions
    """
    try:
        file_df = pd.read_csv(file, header=None)
    except Exception:
        raise FileDoesNotParseToCSV()

    values_matrix = file_df.values

    if values_matrix.shape[1] != 7:  # ensure there's only 7 rows
        raise WrongNumberOfRows(values_matrix.shape[1])
    if values_matrix.shape[0] != 64:
        if values_matrix.shape[0] == 65:
            values_matrix = values_matrix[1:]
        else:
            raise WrongNumberOfColumns(values_matrix.shape[0])

    errors = []
    row_index = 0
    while row_index < 64:
        row = values_matrix[row_index]
        column_index = 0
        while column_index < 7:
            if column_index in [0, 4, 5]:
                if not can_cast_to_int(row[column_index]):
                    errors.append("Value in row %d, column %d must be an integer" % (row_index + 1, column_index + 1))
            elif column_index is 1:
                if not string_is_in_list(row[column_index], csv_file_string_entries["LIST_OF_GROUPS"]):
                    errors.append("Illegal value in row %d, column %d, please check that its correct" %
                                  (row_index + 1, column_index + 1))
            elif column_index in [2, 3]:
                if not string_is_in_list(row[column_index], csv_file_string_entries["LIST_OF_COUNTRIES"]):
                    errors.append("Illegal value in row %d, column %d, please check that its correct" %
                                  (row_index + 1, column_index + 1))
            elif column_index == 6:
                if not string_is_in_list(row[column_index], csv_file_string_entries["WDL"]):
                    errors.append("Illegal value in row %d, column %d, please check that its correct" %
                                  (row_index + 1, column_index + 1))
            column_index += 1
        row_index += 1
    return errors


def delete_users_submission_directory(directory):
    if os.path.isdir(directory):
        shutil.rmtree(directory)


def create_submissions_directory():
    if not os.path.isdir(submission_dir):
        os.makedirs(submission_dir)
