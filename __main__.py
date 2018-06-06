from config import flask_config
from db import create_table, drop_table
from routes import app
from tools import create_submissions_directory

if __name__ == "__main__":
    create_submissions_directory()
    # drop_table()
    create_table()
    app.run(**flask_config)
