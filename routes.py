import os
import jinja2

from flask import Flask, flash, url_for, render_template, request, session, redirect
from passlib.hash import bcrypt_sha256
from werkzeug.utils import secure_filename

import tools
import db
import config
from email_client import Email_Client

# Flask app configuration
app = Flask("ACM_WC")
app.secret_key = config.SECRET_KEY
app.config["SESSION_REFRESH_EACH_REQUEST"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 10  # seconds
app.config['UPLOAD_FOLDER'] = config.submission_dir

mail_client = Email_Client(**config.email_config)

my_loader = jinja2.ChoiceLoader([
    app.jinja_loader,
    jinja2.FileSystemLoader(config.TEMPLATES_LOCATION),
])
app.jinja_loader = my_loader


@app.route('/', methods=["GET"])
def home():
    return render_template("index.html")


@app.route('/register', methods=["GET"])
def register():
    return render_template("register.html")


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
            db.create_user(first_name, surname, email, password, token)
            link = config.url + "/register-confirmation?t=" + token
            subject, body = mail_client.create_registration_completion_email(first_name, surname, link)
            email_sent = mail_client.send_email(subject, body, [email])
        except Exception as e:
            flash("User email already registered, sign in?")
            return redirect(url_for('register'))

        flash("""We have sent a verification email to you, please confirm so you can access your account""")
        return render_template("register.html")


@app.route('/register-confirmation', methods=["GET"])
def confirm_registration():
    token = request.args.get("t")
    try:
        db.confirm_token(token)
        flash("Congratulations you are now fully registered, login to make a submission")
        return render_template("register.html")
    except Exception as e:
        return render_template("register.html")


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
                    return redirect(url_for('admin'))
                else:
                    flash("Failed to login, please check both email and password are correct")
                    return render_template('register.html', FORGOT_PASS=True)
            except Exception as e:
                flash("Failed to login, please check both email and password are correct")
                return redirect(url_for('register'))
    else:
        return render_template('register.html')


@app.route("/logout", methods=["POST"])
@tools.protected
def logout():
    session.clear()
    flash('You are now logged out')
    return redirect(url_for('register'))


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
            email_sent = mail_client.send_email(subject, body, [email])
            flash("We have sent emailed you a link to change your password")
            return render_template('register.html')
        except db.FailedToAddChangePasswordToken as e:
            flash("An issue has occured, make sure you have inputted the correct email")
            return render_template('register.html')


@app.route('/change-password', methods=["GET", "POST"])
def change_password():
    if request.method == "GET":
        token = request.args.get("t")
        if token is None:
            return render_template('register.html')
        return render_template('change_password.html', TOKEN=token)
    elif request.method == "POST":
        try:
            form = tools.ChangePasswordForm(request.form)
            password = bcrypt_sha256.using(salt=config.salt).hash(str(form.password.data))
            db.change_password(form.token.data, password)
            flash("You have successfully changed your password")
            return render_template("register.html")
        except Exception as e:
            flash("Your password was not changed, please contact us at [email] and we will assist you promptly.")
            return render_template('change_password.html')


@app.route('/send-verification-code', methods=["GET"])
@tools.protected
def send_verification_code():
    email = session['email']
    token = tools.token_generator()
    link = config.url + "/register-confirmation?t=" + token
    user = db.get_user_with_email(email)
    subject, body = mail_client.create_registration_completion_email(user['first_name'], user['surname'], link)
    db.add_confirmation_token(email, token)
    email_sent = mail_client.send_email(subject, body, [email])
    flash("Verification link is sent to your email")
    return render_template('admin.html', CONFIRMED=db.is_confirmed(email))


@app.route("/admin", methods=["GET"])
@tools.protected
def admin():
    try:
        user = db.get_user_with_email(session['email'])
        return render_template("admin.html",
                               CONFIRMED=db.is_confirmed(session['email']),
                               FIRST_NAME=user['first_name'],
                               SUBMITTED=user["file_submitted"])

    except Exception as e:
        flash("An issue has occurred")
        return redirect(url_for('register'))


@app.route("/upload-file", methods=["POST"])
@tools.protected
def upload_file():
    if 'file' not in request.files:
        flash('No file submitted')
        return redirect(url_for("admin"))
    else:
        file = request.files['file']
        if file.filename == '':
            flash('No file submitted')
            return redirect(url_for("admin"))
        elif len(file.filename) > 100:
            flash('Filename is too long, must be less than 100 characters')
            return redirect(url_for("admin"))
    try:
        user = db.get_user_with_email(session['email'])
        if not tools.allowed_file(file.filename):
            flash("File must have .csv extension!")
            return redirect(url_for('admin',
                                    CONFIRMED=db.is_confirmed(session['email']),
                                    FIRST_NAME=user['first_name'],
                                    SUBMITTED=user["file_submitted"]))
        try:
            errors_in_file = tools.errors_in_submission_file(file)
            if len(errors_in_file) is not 0:
                flash("File contains errors, please fix them:")
                for error in errors_in_file:
                    flash(error)
                return redirect(url_for('admin',
                                        CONFIRMED=db.is_confirmed(session['email']),
                                        FIRST_NAME=user['first_name'],
                                        SUBMITTED=user["file_submitted"]))
        except Exception as e:
            flash("File contains errors, please fix them:")
            flash(str(e))
            return redirect(url_for('admin',
                                    CONFIRMED=db.is_confirmed(session['email']),
                                    FIRST_NAME=user['first_name'],
                                    SUBMITTED=user["file_submitted"]))

        if file:
            filename = secure_filename(file.filename)
            user_directory = app.config['UPLOAD_FOLDER'] + "/" + str(user["id"])
            tools.delete_users_submission_directory(user_directory)
            os.makedirs(user_directory)
            file.save(os.path.join(user_directory + "/", filename))
            db.add_file_submitted(session["email"], filename)
            return redirect(url_for("admin",
                                    CONFIRMED=db.is_confirmed(session['email']),
                                    FIRST_NAME=user['first_name'],
                                    SUBMITTED=file.filename))
    except Exception as e:
        flash("An issue has occurred, please try another time, or contact us at [email]")
        return redirect(url_for('admin'))


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
                                SUBMITTED=user["file_submitted"]))
    except Exception as e:
        flash("Experienced an error processing your request, please contact us at [email]")
        return render_template('admin.html',
                               CONFIRMED=db.is_confirmed(session['email']),
                               FIRST_NAME=user['first_name'],
                               SUBMITTED=user["file_submitted"]
                               )


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
        return redirect(url_for('register'))
    except Exception as e:
        flash("We apologise, and issue has occured, please contact us at [email]")
        return redirect(url_for('admin',
                                CONFIRMED=db.is_confirmed(session['email']),
                                FIRST_NAME=user['first_name'],
                                SUBMITTED=user["file_submitted"]
                                ))
