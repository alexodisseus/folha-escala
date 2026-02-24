from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db
from app.models import Funcionario  # Apenas o Funcionario

main = Blueprint("main", __name__)

@main.route("/")
def index():
    return render_template("index.html")


@main.route("/funcionarios")
def funcionarios():

    busca = request.args.get("busca", "")
    page = request.args.get("page", 1, type=int)
    
    # Filtros adicionais
    filtro_periodo = request.args.get("periodo", "")
    filtro_escala = request.args.get("escala", "")
    filtro_ativo = request.args.get("ativo", "")

    query = Funcionario.query

    if busca:
        query = query.filter(Funcionario.nome.ilike(f"%{busca}%"))
    
    if filtro_periodo:
        query = query.filter(Funcionario.periodo == filtro_periodo)
    
    if filtro_escala:
        query = query.filter(Funcionario.escala == filtro_escala)
    
    if filtro_ativo:
        ativo = filtro_ativo.lower() == 'true'
        query = query.filter(Funcionario.ativo == ativo)

    paginacao = query.order_by(Funcionario.nome).paginate(page=page, per_page=5)

    total_ativos = Funcionario.query.filter_by(ativo=True).count()
    
    # Para os selects do filtro
    periodos = ['manhã', 'tarde', 'noite']
    escalas = ['A', 'B', 'C', 'D']

    return render_template(
        "funcionarios.html",
        funcionarios=paginacao,
        total_ativos=total_ativos,
        busca=busca,
        periodos=periodos,
        escalas=escalas,
        filtro_periodo=filtro_periodo,
        filtro_escala=filtro_escala,
        filtro_ativo=filtro_ativo
    )


@main.route("/funcionarios/novo", methods=["POST"])
def novo_funcionario():
    
    try:
        novo = Funcionario(
            nome=request.form["nome"],
            matricula=request.form["matricula"],
            periodo=request.form["periodo"],
            escala=request.form["escala"].upper(),  # Garante maiúsculo
            ativo=True
        )
        
        db.session.add(novo)
        db.session.commit()
        flash("Funcionário cadastrado com sucesso!", "success")
        
    except ValueError as e:
        flash(str(e), "error")
        db.session.rollback()
    except Exception as e:
        flash("Erro ao cadastrar funcionário.", "error")
        db.session.rollback()

    return redirect(url_for("main.funcionarios"))


@main.route("/funcionarios/editar/<int:id>", methods=["POST"])
def editar_funcionario(id):

    f = Funcionario.query.get_or_404(id)

    try:
        f.nome = request.form["nome"]
        f.matricula = request.form["matricula"]
        f.periodo = request.form["periodo"]
        f.escala = request.form["escala"].upper()
        
        db.session.commit()
        flash("Funcionário atualizado com sucesso!", "success")
        
    except ValueError as e:
        flash(str(e), "error")
        db.session.rollback()
    except Exception as e:
        flash("Erro ao atualizar funcionário.", "error")
        db.session.rollback()

    return redirect(url_for("main.funcionarios"))


@main.route("/funcionarios/toggle/<int:id>")
def toggle_funcionario(id):

    f = Funcionario.query.get_or_404(id)
    f.ativo = not f.ativo
    
    try:
        db.session.commit()
        status = "ativado" if f.ativo else "desativado"
        flash(f"Funcionário {status} com sucesso!", "success")
    except:
        flash("Erro ao alterar status do funcionário.", "error")
        db.session.rollback()

    return redirect(url_for("main.funcionarios"))


@main.route("/funcionarios/detalhes/<int:id>")
def detalhes_funcionario(id):
    """Rota opcional para ver detalhes de um funcionário"""
    funcionario = Funcionario.query.get_or_404(id)
    return render_template("detalhes_funcionario.html", funcionario=funcionario)