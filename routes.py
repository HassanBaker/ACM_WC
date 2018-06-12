import os

from flask import Flask, flash, url_for, render_template, request, session, redirect
from passlib.hash import bcrypt_sha256
from werkzeug.utils import secure_filename

import tools
import db
import config
from email_client import Email_Client
import pandas as pd

# Flask app configuration
app = Flask("ACM_WC", static_folder=config.STATIC_DIR, template_folder=config.TEMPLATES_DIR)
app.secret_key = config.SECRET_KEY
app.config["SESSION_REFRESH_EACH_REQUEST"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config['UPLOAD_FOLDER'] = config.SUBMISSION_DIR

mail_client = Email_Client(**config.email_config)


@app.route("/netsoc-policy", methods=["GET"])
def netsoc_policy():
    return render_template("netsoc_policy.html")


@app.route("/cookies-policy", methods=["GET"])
def cookies_policy():
    return render_template("cookies_policy.html",
                           COOKIES_NOTIFICATION=tools.show_cookies_policy(),
                           LOGGED_IN=tools.is_logged_in())


@app.route("/data-protection", methods=["GET"])
def data_protection():
    return render_template("privacy.html",
                           COOKIES_NOTIFICATION=tools.show_cookies_policy(),
                           LOGGED_IN=tools.is_logged_in()
                           )


@app.route('/accept-policy', methods=["GET"])
def accept_policy():
    session["accepted_policy"] = True
    return redirect(request.referrer)


@app.route('/', methods=["GET"])
def home():
    return render_template("index.html",
                           COOKIES_NOTIFICATION=tools.show_cookies_policy(),
                           LOGGED_IN=tools.is_logged_in()
                           )


@app.route('/register', methods=["GET"])
def register():
    return render_template("register.html",
                           COOKIES_NOTIFICATION=tools.show_cookies_policy(),
                           LOGGED_IN=tools.is_logged_in()
                           )


@app.route('/register-form', methods=["POST"])
def register_form():
    form = tools.RegisterForm(request.form)
    if form.validate():
        first_name = form.first_name.data
        surname = form.surname.data
        email = form.email.data
        password = bcrypt_sha256.using(salt=config.salt).hash(str(form.password.data))
        token = tools.token_generator()
        try:
            db.create_user(first_name, surname, email, password, token, "photo-opt-in" in request.form)
            link = config.url + "/register-confirmation?t=" + token
            subject, body = mail_client.create_registration_completion_email(first_name, surname, link)
            email_sent = mail_client.send_email(subject, body, email)
        except Exception as e:
            flash("User email already registered, sign in?")
            return redirect(url_for('register',
                                    COOKIES_NOTIFICATION=tools.show_cookies_policy(),
                                    LOGGED_IN=tools.is_logged_in()
                                    ))

        flash("""We have sent a verification email to you, please confirm so you can access your account""")
        return render_template("register.html",
                               COOKIES_NOTIFICATION=tools.show_cookies_policy(),
                               LOGGED_IN=tools.is_logged_in()
                               )


@app.route('/register-confirmation', methods=["GET"])
def confirm_registration():
    token = request.args.get("t")
    try:
        db.confirm_token(token)
        flash("Congratulations you are now fully registered, login to make a submission")
        return render_template("register.html",
                               COOKIES_NOTIFICATION=tools.show_cookies_policy(),
                               LOGGED_IN=tools.is_logged_in()
                               )
    except Exception as e:
        return render_template("register.html",
                               COOKIES_NOTIFICATION=tools.show_cookies_policy(),
                               LOGGED_IN=tools.is_logged_in()
                               )


@app.route('/login', methods=["POST", "GET"])
def login():
    if request.method == "POST":
        form = tools.LoginForm(request.form)
        if form.validate():
            email = form.email.data
            password = form.password.data
            try:
                user = db.get_user_with_email(email)
                if bcrypt_sha256.verify(password, user['password']):
                    session['logged_in'] = True
                    session['id'] = user['id']
                    session['email'] = email
                    return redirect(url_for('admin',
                                            COOKIES_NOTIFICATION=tools.show_cookies_policy(),
                                            LOGGED_IN=tools.is_logged_in()
                                            ))
                else:
                    flash("Failed to login, please check both email and password are correct")
                    return render_template('register.html', FORGOT_PASS=True)
            except Exception as e:
                flash("Failed to login, please check both email and password are correct")
                return redirect(url_for('register',
                                        COOKIES_NOTIFICATION=tools.show_cookies_policy(),
                                        LOGGED_IN=tools.is_logged_in()
                                        ))
    else:
        return render_template('register.html',
                               COOKIES_NOTIFICATION=tools.show_cookies_policy(),
                               LOGGED_IN=tools.is_logged_in()
                               )


@app.route("/logout", methods=["POST"])
@tools.protected
def logout():
    accepted_policy = tools.show_cookies_policy()
    session.clear()
    session['accepted_policy'] = accepted_policy
    flash('You are now logged out')
    return redirect(url_for('register',
                            COOKIES_NOTIFICATION=tools.show_cookies_policy(),
                            LOGGED_IN=tools.is_logged_in()
                            ))


@app.route('/forgotten-password', methods=["POST"])
def forgotten_password():
    if request.method == "POST":
        email = request.form["email"]
        token = tools.token_generator()
        try:
            db.add_change_password_token(email, token)
            user = db.get_user_with_email(email)
            link = config.url + "/change-password?t=" + token
            subject, body = mail_client.create_change_password_email(
                user['first_name'], user['surname'], link)
            email_sent = mail_client.send_email(subject, body, email)
            flash("We have sent emailed you a link to change your password")
            return render_template('register.html',
                                   COOKIES_NOTIFICATION=tools.show_cookies_policy(),
                                   LOGGED_IN=tools.is_logged_in()
                                   )
        except db.FailedToAddChangePasswordToken as e:
            flash("An issue has occured, make sure you have inputted the correct email")
            return render_template('register.html',
                                   COOKIES_NOTIFICATION=tools.show_cookies_policy(),
                                   LOGGED_IN=tools.is_logged_in()
                                   )


@app.route('/change-password', methods=["GET", "POST"])
def change_password():
    if request.method == "GET":
        token = request.args.get("t")
        if token is None:
            return render_template('register.html')
        return render_template('change_password.html',
                               TOKEN=token,
                               COOKIES_NOTIFICATION=tools.show_cookies_policy(),
                               LOGGED_IN=tools.is_logged_in())
    elif request.method == "POST":
        try:
            form = tools.ChangePasswordForm(request.form)
            password = bcrypt_sha256.using(salt=config.salt).hash(str(form.password.data))
            db.change_password(form.token.data, password)
            flash("You have successfully changed your password")
            return render_template("register.html",
                                   COOKIES_NOTIFICATION=tools.show_cookies_policy(),
                                   LOGGED_IN=tools.is_logged_in()
                                   )
        except Exception as e:
            flash("Your password was not changed, please contact us at %s and we will assist you promptly." %
                  config.email_config["admin_email"])
            return render_template('change_password.html',
                                   COOKIES_NOTIFICATION=tools.show_cookies_policy(),
                                   LOGGED_IN=tools.is_logged_in()
                                   )


@app.route('/send-verification-code', methods=["GET"])
@tools.protected
def send_verification_code():
    email = session['email']
    token = tools.token_generator()
    link = config.url + "/register-confirmation?t=" + token
    user = db.get_user_with_email(email)
    subject, body = mail_client.create_registration_completion_email(user['first_name'], user['surname'], link)
    db.add_confirmation_token(email, token)
    email_sent = mail_client.send_email(subject, body, email)
    flash("Verification link is sent to your email.")
    return render_template('admin.html', CONFIRMED=db.is_confirmed(email),
                           COOKIES_NOTIFICATION=tools.show_cookies_policy(),
                           LOGGED_IN=tools.is_logged_in()
                           )


@app.route("/admin", methods=["GET"])
@tools.protected
def admin():
    try:
        user = db.get_user_with_email(session['email'])
        return render_template("admin.html",
                               CONFIRMED=db.is_confirmed(session['email']),
                               FIRST_NAME=user['first_name'],
                               SUBMITTED=user["file_submitted"],
                               COOKIES_NOTIFICATION=tools.show_cookies_policy(),
                               LOGGED_IN=tools.is_logged_in())

    except Exception as e:
        flash("An issue has occurred")
        return redirect(url_for('register',
                                COOKIES_NOTIFICATION=tools.show_cookies_policy(),
                                LOGGED_IN=tools.is_logged_in()
                                ))


@app.route("/upload-file", methods=["POST"])
@tools.protected
def upload_file():
    if 'file' not in request.files:
        flash('No file submitted')
        return redirect(url_for("admin",
                                COOKIES_NOTIFICATION=tools.show_cookies_policy(),
                                LOGGED_IN=tools.is_logged_in()
                                ))
    else:
        file = request.files['file']
        if file.filename == '':
            flash('No file submitted')
            return redirect(url_for("admin"))
        elif len(file.filename) > 100:
            flash('Filename is too long, must be less than 100 characters')
            return redirect(url_for("admin",
                                    COOKIES_NOTIFICATION=tools.show_cookies_policy(),
                                    LOGGED_IN=tools.is_logged_in()
                                    ))
    try:
        user = db.get_user_with_email(session['email'])
        if not tools.allowed_file(file.filename):
            flash("File must have .csv extension!")
            return redirect(url_for('admin',
                                    CONFIRMED=db.is_confirmed(session['email']),
                                    FIRST_NAME=user['first_name'],
                                    SUBMITTED=user["file_submitted"],
                                    COOKIES_NOTIFICATION=tools.show_cookies_policy(),
                                    LOGGED_IN=tools.is_logged_in()))
        try:
            errors_in_file, file_df = tools.errors_in_submission_file(file)
            if len(errors_in_file) is not 0:
                flash("File contains errors, please fix them:")
                for error in errors_in_file:
                    flash(error)
                return redirect(url_for('admin',
                                        CONFIRMED=db.is_confirmed(session['email']),
                                        FIRST_NAME=user['first_name'],
                                        SUBMITTED=user["file_submitted"],
                                        COOKIES_NOTIFICATION=tools.show_cookies_policy(),
                                        LOGGED_IN=tools.is_logged_in()))
        except Exception as e:
            flash("File contains errors, please fix them:")
            flash(str(e))
            return redirect(url_for('admin',
                                    CONFIRMED=db.is_confirmed(session['email']),
                                    FIRST_NAME=user['first_name'],
                                    SUBMITTED=user["file_submitted"],
                                    COOKIES_NOTIFICATION=tools.show_cookies_policy(),
                                    LOGGED_IN=tools.is_logged_in()))

        if file:
            filename = secure_filename(file.filename)
            user_directory = app.config['UPLOAD_FOLDER'] + "/" + str(user["id"])
            tools.delete_users_submission_directory(user_directory)
            os.makedirs(user_directory)
            file_df.to_csv(os.path.join(user_directory + "/", filename))
            db.add_file_submitted(session["email"], filename)
            return redirect(url_for("admin",
                                    CONFIRMED=db.is_confirmed(session['email']),
                                    FIRST_NAME=user['first_name'],
                                    SUBMITTED=file.filename,
                                    COOKIES_NOTIFICATION=tools.show_cookies_policy(),
                                    LOGGED_IN=tools.is_logged_in()
                                    ))
    except Exception as e:
        flash("An issue has occurred, please try another time, or contact us at %s" % config.email_config["admin_email"])
        return redirect(url_for('admin',
                                COOKIES_NOTIFICATION=tools.show_cookies_policy(),
                                LOGGED_IN=tools.is_logged_in()
                                ))


@app.route("/delete-submission", methods=["GET"])
@tools.protected
def delete_submission():
    user = db.get_user_with_email(session['email'])
    try:
        user_directory = app.config['UPLOAD_FOLDER'] + "/" + str(user["id"])
        db.remove_file_entry(session['email'])
        tools.delete_users_submission_directory(user_directory)
        flash("Successfully deleted your submission")
        return redirect(url_for('admin',
                                CONFIRMED=db.is_confirmed(session['email']),
                                FIRST_NAME=user['first_name'],
                                SUBMITTED=user["file_submitted"],
                                COOKIES_NOTIFICATION=tools.show_cookies_policy(),
                                LOGGED_IN=tools.is_logged_in()))
    except Exception as e:
        flash("Experienced an error processing your request, please contact us at %s" % config.email_config["admin_email"])
        return render_template('admin.html',
                               CONFIRMED=db.is_confirmed(session['email']),
                               FIRST_NAME=user['first_name'],
                               SUBMITTED=user["file_submitted"],
                               COOKIES_NOTIFICATION=tools.show_cookies_policy(),
                               LOGGED_IN=tools.is_logged_in())


@app.route("/delete-account", methods=["GET"])
@tools.protected
def delete_account():
    try:
        user = db.get_user_with_email(session['email'])
        user_directory = app.config['UPLOAD_FOLDER'] + "/" + str(user["id"])
        db.remove_file_entry(session['email'])
        tools.delete_users_submission_directory(user_directory)
        flash("Successfully deleted your submission")
        db.delete_user_given_email(session['email'])
        flash("Successfully deleted your account")
        accepted_policy = tools.show_cookies_policy()
        session.clear()
        session['accepted_policy'] = accepted_policy
        return redirect(url_for('register'))
    except Exception as e:
        flash("We apologise, and issue has occured, please contact us at %s" % config.email_config["admin_email"])
        return redirect(url_for('admin',
                                CONFIRMED=db.is_confirmed(session['email']),
                                FIRST_NAME=user['first_name'],
                                SUBMITTED=user["file_submitted"],
                                COOKIES_NOTIFICATION=tools.show_cookies_policy(),
                                LOGGED_IN=tools.is_logged_in()))
