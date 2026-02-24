from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate


db = SQLAlchemy()
migrate = Migrate()



def create_app():
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///banco.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = "Guerra Aos Senhores!"

    db.init_app(app)
    migrate.init_app(app, db)


    from app.routes.main_routes import main
    from app.routes.periodo_routes import periodo

    app.register_blueprint(main)
    app.register_blueprint(periodo)

    return app