from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db
from app.models.funcionario import PeriodoMensal, DiaTrabalhado, Funcionario

from datetime import datetime, date, timedelta

# Se você já tem um Blueprint 'main', pode adicionar estas rotas nele
# ou criar um novo blueprint específico para períodos

periodo = Blueprint("periodo", __name__)


@periodo.route("/periodos")
def periodos():
    """Lista todos os períodos com filtros e paginação"""
    
    busca = request.args.get("busca", "")
    page = request.args.get("page", 1, type=int)
    
    # Filtros adicionais
    filtro_ano = request.args.get("ano", "")
    filtro_mes = request.args.get("mes", "")

    query = PeriodoMensal.query

    if busca:
        query = query.filter(PeriodoMensal.nome.ilike(f"%{busca}%"))
    
    if filtro_ano and filtro_ano.isdigit():
        query = query.filter(PeriodoMensal.ano == int(filtro_ano))
    
    if filtro_mes and filtro_mes.isdigit():
        query = query.filter(PeriodoMensal.mes_referencia == int(filtro_mes))

    # Ordenar por data (mais recentes primeiro)
    paginacao = query.order_by(PeriodoMensal.ano.desc(), 
                               PeriodoMensal.mes_referencia.desc()).paginate(page=page, per_page=10)

    # Dados para os filtros
    anos_disponiveis = db.session.query(PeriodoMensal.ano).distinct().order_by(PeriodoMensal.ano.desc()).all()
    anos_disponiveis = [ano[0] for ano in anos_disponiveis]
    
    meses = [
        (1, 'Janeiro'), (2, 'Fevereiro'), (3, 'Março'), (4, 'Abril'),
        (5, 'Maio'), (6, 'Junho'), (7, 'Julho'), (8, 'Agosto'),
        (9, 'Setembro'), (10, 'Outubro'), (11, 'Novembro'), (12, 'Dezembro')
    ]

    return render_template(
        "periodos.html",
        periodos=paginacao,
        busca=busca,
        anos_disponiveis=anos_disponiveis,
        meses=meses,
        filtro_ano=filtro_ano,
        filtro_mes=filtro_mes,
        now=datetime.now()
    )


@periodo.route("/periodos/novo", methods=["GET", "POST"])
def novo_periodo():
    """Cria um novo período mensal"""
    
    if request.method == "GET":
        # Para o formulário, precisamos dos anos e meses disponíveis
        ano_atual = datetime.now().year
        anos = range(ano_atual - 2, ano_atual + 3)  # 2 anos antes, 2 depois
        
        meses = [
            (1, 'Janeiro'), (2, 'Fevereiro'), (3, 'Março'), (4, 'Abril'),
            (5, 'Maio'), (6, 'Junho'), (7, 'Julho'), (8, 'Agosto'),
            (9, 'Setembro'), (10, 'Outubro'), (11, 'Novembro'), (12, 'Dezembro')
        ]
        
        return render_template("novo_periodo.html", anos=anos, meses=meses)
    
    # Método POST
    try:
        ano = int(request.form["ano"])
        mes = int(request.form["mes"])
        
        # Verificar se já existe período para este mês/ano
        existente = PeriodoMensal.query.filter_by(ano=ano, mes_referencia=mes).first()
        if existente:
            flash(f"Já existe um período para {mes}/{ano}", "error")
            return redirect(url_for("periodo.periodos"))
        
        # Criar o período usando o método da classe
        novo_periodo = PeriodoMensal.criar_periodo(ano, mes)
        
        db.session.add(novo_periodo)
        db.session.commit()
        flash("Período criado com sucesso!", "success")
        
    except ValueError as e:
        flash(str(e), "error")
        db.session.rollback()
    except Exception as e:
        flash(f"Erro ao criar período: {str(e)}", "error")
        db.session.rollback()

    return redirect(url_for("periodo.periodos"))


@periodo.route("/periodos/escala/<int:id>")
def escala_periodo(id):
    """Mostra a escala de serviço do período"""
    
    periodo = PeriodoMensal.query.get_or_404(id)
    
    # Buscar todos os funcionários ativos
    funcionarios = Funcionario.query.filter_by(ativo=True).order_by(Funcionario.nome).all()
    
    # Gerar lista de datas do período
    datas = []
    data_atual = periodo.data_inicio
    while data_atual <= periodo.data_fim:
        datas.append({
            'data': data_atual,
            'dia': data_atual.strftime('%d'),
            'dia_semana': data_atual.weekday(),  # 0=segunda, 5=sábado, 6=domingo
            'nome_dia': data_atual.strftime('%A').capitalize()
        })
        data_atual += timedelta(days=1)
    
    # Mapeamento de escala para dias de trabalho
    # 0=segunda, 1=terça, 2=quarta, 3=quinta, 4=sexta, 5=sábado, 6=domingo
    escala_dias = {
        'A': [0, 1, 2, 3, 4],      # Segunda a Sexta
        'B': [1, 2, 3, 4, 5],      # Terça a Sábado
        'C': [6, 0, 1, 2, 3],      # Domingo a Quinta
        'D': [2, 3, 4, 5, 6]       # Quarta a Domingo
    }
    
    return render_template(
        "escala_periodo.html",
        periodo=periodo,
        funcionarios=funcionarios,
        datas=datas,
        escala_dias=escala_dias,
        enumerate=enumerate  # Passar enumerate para o template
    )



@periodo.route("/periodos/detalhes/<int:id>")
def detalhes_periodo(id):
    """Mostra detalhes de um período específico, incluindo dias trabalhados"""
    
    periodo = PeriodoMensal.query.get_or_404(id)
    
    # Estatísticas do período
    total_dias = (periodo.data_fim - periodo.data_inicio).days + 1
    
    # CORREÇÃO AQUI: Alterar a sintaxe do case()
    dias_por_funcionario = db.session.query(
        Funcionario,
        db.func.count(DiaTrabalhado.id).label('total_dias'),
        db.func.sum(db.case(
            (DiaTrabalhado.tipo == 'normal', 1),  # Argumento posicional 1
            else_=0
        )).label('dias_normais'),
        db.func.sum(db.case(
            (DiaTrabalhado.tipo == 'extra', 1),   # Argumento posicional 1
            else_=0
        )).label('dias_extras')
    ).join(
        DiaTrabalhado, DiaTrabalhado.funcionario_id == Funcionario.id
    ).filter(
        DiaTrabalhado.periodo_id == periodo.id
    ).group_by(
        Funcionario.id
    ).all()
    
    # Buscar todos os funcionários ativos (para incluir quem não trabalhou)
    todos_funcionarios = Funcionario.query.filter_by(ativo=True).all()
    
    # Criar um dicionário com os dados dos que trabalharam
    dados_funcionarios = {}
    for f in todos_funcionarios:
        dados_funcionarios[f.id] = {
            'funcionario': f,
            'total_dias': 0,
            'dias_normais': 0,
            'dias_extras': 0
        }
    
    # Atualizar com quem trabalhou
    for f, total, normais, extras in dias_por_funcionario:
        dados_funcionarios[f.id] = {
            'funcionario': f,
            'total_dias': total,
            'dias_normais': normais or 0,
            'dias_extras': extras or 0
        }
    
    return render_template(
        "detalhes_periodo.html",
        periodo=periodo,
        dados_funcionarios=dados_funcionarios.values(),
        total_dias=total_dias
    )

@periodo.route("/periodos/editar/<int:id>", methods=["GET", "POST"])
def editar_periodo(id):
    """Edita um período existente"""
    
    periodo = PeriodoMensal.query.get_or_404(id)
    
    if request.method == "GET":
        # Preparar dados para o formulário
        ano_atual = datetime.now().year
        anos = range(ano_atual - 2, ano_atual + 3)
        
        meses = [
            (1, 'Janeiro'), (2, 'Fevereiro'), (3, 'Março'), (4, 'Abril'),
            (5, 'Maio'), (6, 'Junho'), (7, 'Julho'), (8, 'Agosto'),
            (9, 'Setembro'), (10, 'Outubro'), (11, 'Novembro'), (12, 'Dezembro')
        ]
        
        return render_template(
            "editar_periodo.html",
            periodo=periodo,
            anos=anos,
            meses=meses
        )
    
    # Método POST
    try:
        # Atualizar dados
        periodo.nome = request.form["nome"]
        periodo.ano = int(request.form["ano"])
        periodo.mes_referencia = int(request.form["mes"])
        
        # Atualizar datas se fornecidas
        if request.form.get("data_inicio"):
            periodo.data_inicio = datetime.strptime(request.form["data_inicio"], '%Y-%m-%d').date()
        if request.form.get("data_fim"):
            periodo.data_fim = datetime.strptime(request.form["data_fim"], '%Y-%m-%d').date()
        
        # Recalcular estatísticas
        periodo.calcular_estatisticas()
        
        db.session.commit()
        flash("Período atualizado com sucesso!", "success")
        
    except ValueError as e:
        flash(str(e), "error")
        db.session.rollback()
    except Exception as e:
        flash(f"Erro ao atualizar período: {str(e)}", "error")
        db.session.rollback()

    return redirect(url_for("periodo.periodos"))


@periodo.route("/periodos/excluir/<int:id>", methods=["POST"])
def excluir_periodo(id):
    """Exclui um período (apenas se não tiver dias trabalhados associados)"""
    
    periodo = PeriodoMensal.query.get_or_404(id)
    
    try:
        # Verificar se há dias trabalhados associados
        if periodo.dias_trabalhados.count() > 0:
            flash("Não é possível excluir um período que possui dias trabalhados registrados.", "error")
            return redirect(url_for("periodo.detalhes_periodo", id=id))
        
        db.session.delete(periodo)
        db.session.commit()
        flash("Período excluído com sucesso!", "success")
        
    except Exception as e:
        flash(f"Erro ao excluir período: {str(e)}", "error")
        db.session.rollback()

    return redirect(url_for("periodo.periodos"))


@periodo.route("/periodos/recalcular/<int:id>")
def recalcular_periodo(id):
    """Recalcula as estatísticas de um período"""
    
    periodo = PeriodoMensal.query.get_or_404(id)
    
    try:
        periodo.calcular_estatisticas()
        db.session.commit()
        flash("Estatísticas recalculadas com sucesso!", "success")
    except Exception as e:
        flash(f"Erro ao recalcular estatísticas: {str(e)}", "error")
        db.session.rollback()
    
    return redirect(url_for("periodo.detalhes_periodo", id=id))


@periodo.route("/api/periodos/verificar_disponibilidade")
def verificar_disponibilidade_periodo():
    """API para verificar se um período já existe (útil para validação AJAX)"""
    
    ano = request.args.get("ano", type=int)
    mes = request.args.get("mes", type=int)
    
    if not ano or not mes:
        return jsonify({"error": "Ano e mês são obrigatórios"}), 400
    
    existente = PeriodoMensal.query.filter_by(ano=ano, mes_referencia=mes).first()
    
    return jsonify({
        "disponivel": existente is None,
        "mensagem": f"Período para {mes}/{ano} já existe" if existente else "Período disponível"
    })