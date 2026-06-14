import os
from flask import Flask
from dotenv import load_dotenv

load_dotenv()


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ['FLASK_SECRET_KEY']

    from .routes import auth, main
    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)

    return app
