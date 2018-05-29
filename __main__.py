from config import flask_config
from db import create_table, drop_table
from routes import app

if __name__ == "__main__":
    # drop_table()
    create_table()
    app.run(**flask_config)
