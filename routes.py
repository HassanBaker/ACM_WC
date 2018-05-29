from flask import Flask, flash, url_for, render_template, request, session, redirect
from passlib.hash import sha256_crypt
import tools
import db
import config
from email_client import Email_Client

app = Flask("ACM_WC")
app.secret_key = config.SECRET_KEY
app.config["SESSION_REFRESH_EACH_REQUEST"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 10  # seconds

mail_client = Email_Client(**config.email_config)


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
        password = sha256_crypt.hash(str(form.password.data))
        token = tools.token_generator()
        try:
            db.create_user(first_name, surname, email, password, token)
            print("created user")
            link = config.url + "/register-confirmation?t=" + token
            subject, body = mail_client.create_registration_completion_email(first_name, surname, link)
            email_sent = mail_client.send_email(subject, body, [email])
            print(email_sent)
        except Exception as e:
            print(e)
            flash("User email already registered, sign in?")
            return redirect(url_for('register'))

        flash("""We have sent a verification email to you, please confirm so you can access your account""")
        return render_template("register.html")


@app.route('/register-confirmation', methods=["GET"])
def confirm_registration():
    token = request.args.get("t")
    print(token)
    try:
        db.confirm_token(token)
        print("confirmed token")
        flash("Congratulations you are now fully registered, login to make a submission")
        return render_template("register.html")
    except Exception as e:
        print(e)
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
                if sha256_crypt.verify(password, user['password']):
                    print("here")
                    session['logged_in'] = True
                    session['id'] = user['id']
                    session['email'] = email
                    # flash("Welcome")
                    return redirect(url_for('admin'))
                else:
                    flash("Failed to login, please check both email and password are correct")
                    return render_template('register.html', FORGOT_PASS=True)
            except Exception as e:
                flash("Failed to login, please check both email and password are correct")
                return redirect(url_for('register'))
    else:
        return render_template('register.html')


@app.route('/forgotten-password', methods=["GET", "POST"])
def forgotten_password():
    if request.method == "GET":
        pass
    return render_template('forgotten_password.html')


@app.route("/admin", methods=["GET"])
@tools.protected
def admin():
    try:
        user = db.get_user_with_email(session['email'])
        return render_template("admin.html",
                               FIRST_NAME=user['first_name'],
                               SUBMITTED=user["file_submitted"])

    except Exception as e:
        print(e)
        flash("An issue has occured")
        return redirect(url_for('register'))


@app.route("/logout", methods=["POST"])
@tools.protected
def logout():
    session.clear()
    flash('You are now logged out')
    return redirect(url_for('register'))


def file_format_is_correct(file):
    return file


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
        return render_template("admin.html",
                               FIRST_NAME=user['first_name'],
                               SUBMITTED=user["file_submitted"])

    except Exception as e:
        print(e)
        flash("An issue has occured")
        return redirect(url_for('register'))
