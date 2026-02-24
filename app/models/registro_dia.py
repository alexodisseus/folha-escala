from app import db


class RegistroDia(db.Model):
    __tablename__ = "registro_dia"

    id = db.Column(db.Integer, primary_key=True)
    funcionario_id = db.Column(db.Integer, db.ForeignKey("funcionarios.id"))
    data = db.Column(db.Date)

    trabalhou = db.Column(db.Boolean)
    horas_extras = db.Column(db.Float)