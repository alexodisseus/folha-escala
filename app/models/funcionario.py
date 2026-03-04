from app import db
from sqlalchemy.orm import validates
from datetime import datetime, date, timedelta
import calendar




class Funcionario(db.Model):
    __tablename__ = "funcionarios"
    
    PERIODOS_VALIDOS = ['manhã', 'tarde', 'noite']
    ESCALAS_VALIDAS = ['A', 'B', 'C', 'D']

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    matricula = db.Column(db.String(50), nullable=False, unique=True)
    ativo = db.Column(db.Boolean, default=True)
    periodo = db.Column(db.String(20), nullable=False)
    escala = db.Column(db.String(1), nullable=False)
    
    # Relacionamentos
    dias_trabalhados = db.relationship('DiaTrabalhado', backref='funcionario', lazy='dynamic', cascade='all, delete-orphan')
    
    @validates('periodo')
    def validate_periodo(self, key, periodo):
        periodo = periodo.lower()
        if periodo not in self.PERIODOS_VALIDOS:
            raise ValueError(f"Período deve ser um de: {', '.join(self.PERIODOS_VALIDOS)}")
        return periodo
    
    @validates('escala')
    def validate_escala(self, key, escala):
        escala = escala.upper()
        if escala not in self.ESCALAS_VALIDAS:
            raise ValueError(f"Escala deve ser um de: {', '.join(self.ESCALAS_VALIDAS)}")
        return escala
    
    def __repr__(self):
        status = "Ativo" if self.ativo else "Inativo"
        return f"<Funcionario {self.nome} - {self.periodo} - Escala {self.escala} [{status}]>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'matricula': self.matricula,
            'periodo': self.periodo,
            'escala': self.escala,
            'ativo': self.ativo
        }


class PeriodoMensal(db.Model):
    """
    Período de apuração mensal
    Inicia dia 10 de um mês e termina dia 09 do mês seguinte
    """
    __tablename__ = "periodos_mensais"
    __table_args__ = (
        db.UniqueConstraint('ano', 'mes_referencia', name='uq_periodo_ano_mes'),
        db.Index('idx_periodo_datas', 'data_inicio', 'data_fim'),
    )

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)  # Ex: "Período Jan/Fev 2024"
    ano = db.Column(db.Integer, nullable=False)
    mes_referencia = db.Column(db.Integer, nullable=False)  # Mês de referência (1-12)
    data_inicio = db.Column(db.Date, nullable=False)
    data_fim = db.Column(db.Date, nullable=False)
    
    # Estatísticas calculadas
    qtd_sabados = db.Column(db.Integer, default=0)
    qtd_domingos = db.Column(db.Integer, default=0)
    qtd_feriados = db.Column(db.Integer, default=0)
    
    # Relacionamentos
    dias_trabalhados = db.relationship('DiaTrabalhado', backref='periodo', lazy='dynamic')
    
    @validates('data_inicio', 'data_fim')
    def validate_datas(self, key, value):
        if key == 'data_fim' and hasattr(self, 'data_inicio') and self.data_inicio:
            if value <= self.data_inicio:
                raise ValueError("Data fim deve ser posterior à data início")
        return value
    
    @classmethod
    def criar_periodo(cls, ano, mes):
        """
        Cria um período para o mês específico
        Ex: mes=1 -> período de 10/01/ano até 09/02/ano
        """
        data_inicio = date(ano, mes, 10)
        
        # Calcula data fim (dia 09 do mês seguinte)
        if mes == 12:
            data_fim = date(ano + 1, 1, 9)
        else:
            data_fim = date(ano, mes + 1, 9)
        
        nome = f"Período {mes:02d}/{ano}"
        mes_referencia = mes
        
        # Criar período
        periodo = cls(
            nome=nome,
            ano=ano,
            mes_referencia=mes_referencia,
            data_inicio=data_inicio,
            data_fim=data_fim
        )
        
        # Calcular estatísticas
        periodo.calcular_estatisticas()
        
        return periodo
    
    def calcular_estatisticas(self):
        """Calcula quantidade de sábados, domingos e feriados no período"""
        qtd_sabados = 0
        qtd_domingos = 0
        
        data_atual = self.data_inicio
        while data_atual <= self.data_fim:
            dia_semana = data_atual.weekday()  # 0=segunda, 5=sábado, 6=domingo
            if dia_semana == 5:  # Sábado
                qtd_sabados += 1
            elif dia_semana == 6:  # Domingo
                qtd_domingos += 1
            data_atual += timedelta(days=1)
        
        self.qtd_sabados = qtd_sabados
        self.qtd_domingos = qtd_domingos
        # Nota: Feriados precisariam de uma tabela ou API externa para calcular
    
    def get_dias_uteis(self):
        """Retorna quantidade de dias úteis no período"""
        dias_total = (self.data_fim - self.data_inicio).days + 1
        return dias_total - self.qtd_sabados - self.qtd_domingos - self.qtd_feriados
    
    def __repr__(self):
        return f"<Periodo {self.nome}: {self.data_inicio} a {self.data_fim}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'ano': self.ano,
            'mes_referencia': self.mes_referencia,
            'data_inicio': self.data_inicio.strftime('%Y-%m-%d'),
            'data_fim': self.data_fim.strftime('%Y-%m-%d'),
            'dias_total': (self.data_fim - self.data_inicio).days + 1,
            'sabados': self.qtd_sabados,
            'domingos': self.qtd_domingos,
            'feriados': self.qtd_feriados,
            'dias_uteis': self.get_dias_uteis()
        }


class DiaTrabalhado(db.Model):
    """
    Registro de dias trabalhados por funcionário em um período
    Funcionário trabalha 5 dias e folga 2 (escala 5x2)
    """
    __tablename__ = "dias_trabalhados"
    __table_args__ = (
        db.UniqueConstraint('funcionario_id', 'data', name='uq_funcionario_data'),
        db.Index('idx_dia_data', 'data'),
        db.Index('idx_dia_funcionario_periodo', 'funcionario_id', 'periodo_id'),
    )

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False)
    dia_semana = db.Column(db.String(20), nullable=False)  # segunda, terça, etc.
    tipo = db.Column(db.String(20), nullable=False, default='normal')  # normal, extra
    
    # Chaves estrangeiras
    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionarios.id'), nullable=False)
    periodo_id = db.Column(db.Integer, db.ForeignKey('periodos_mensais.id'), nullable=False)
    
    @validates('data')
    def validate_data(self, key, data):
        if data > date.today():
            raise ValueError("Não é possível registrar dias futuros")
        return data
    
    @validates('dia_semana')
    def validate_dia_semana(self, key, dia_semana):
        dias_validos = ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo']
        dia_semana = dia_semana.lower()
        if dia_semana not in dias_validos:
            raise ValueError(f"Dia da semana deve ser um de: {', '.join(dias_validos)}")
        return dia_semana
    
    @validates('tipo')
    def validate_tipo(self, key, tipo):
        tipos_validos = ['normal', 'extra']
        tipo = tipo.lower()
        if tipo not in tipos_validos:
            raise ValueError(f"Tipo deve ser um de: {', '.join(tipos_validos)}")
        return tipo
    
    @classmethod
    def registrar_dia(cls, funcionario, data, tipo='normal'):
        """Registra um dia trabalhado para um funcionário"""
        from app import db
        
        # Determinar dia da semana
        dias_map = {0: 'segunda', 1: 'terça', 2: 'quarta', 3: 'quinta', 
                   4: 'sexta', 5: 'sábado', 6: 'domingo'}
        dia_semana = dias_map[data.weekday()]
        
        # Encontrar período correspondente
        periodo = PeriodoMensal.query.filter(
            PeriodoMensal.data_inicio <= data,
            PeriodoMensal.data_fim >= data
        ).first()
        
        if not periodo:
            raise ValueError(f"Não há período definido para a data {data}")
        
        # Verificar se já existe registro para este dia
        existente = cls.query.filter_by(
            funcionario_id=funcionario.id,
            data=data
        ).first()
        
        if existente:
            raise ValueError(f"Já existe registro para {funcionario.nome} em {data}")
        
        # Criar registro
        dia = cls(
            data=data,
            dia_semana=dia_semana,
            tipo=tipo,
            funcionario_id=funcionario.id,
            periodo_id=periodo.id
        )
        
        return dia
    
    def __repr__(self):
        return f"<Dia {self.data} - {self.funcionario.nome} - {self.tipo}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'data': self.data.strftime('%Y-%m-%d'),
            'dia_semana': self.dia_semana,
            'tipo': self.tipo,
            'funcionario': self.funcionario.nome,
            'funcionario_id': self.funcionario_id,
            'periodo': self.periodo.nome if self.periodo else None
        }


class Feriado(db.Model):
    """
    Tabela opcional para gerenciar feriados
    """
    __tablename__ = "feriados"
    
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False, unique=True)
    nome = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(20), default='nacional')  # nacional, estadual, municipal
    recorrente = db.Column(db.Boolean, default=False)  # Se se repete todo ano
    
    def __repr__(self):
        return f"<Feriado {self.data}: {self.nome}>"



class HoraExtra(db.Model):
    __tablename__ = 'horas_extras'
    
    id = db.Column(db.Integer, primary_key=True)
    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionarios.id'), nullable=False)
    periodo_id = db.Column(db.Integer, db.ForeignKey('periodos_mensais.id'), nullable=False)
    data = db.Column(db.Date, nullable=False)
    descricao = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    funcionario = db.relationship('Funcionario', backref=db.backref('horas_extras', lazy='dynamic', cascade='all, delete-orphan'))
    periodo = db.relationship('PeriodoMensal', backref=db.backref('horas_extras', lazy='dynamic', cascade='all, delete-orphan'))
    
    # Garantir que não haja duplicatas (mesmo funcionário não pode ter duas horas extras no mesmo dia/período)
    __table_args__ = (
        db.UniqueConstraint('funcionario_id', 'data', 'periodo_id', name='unique_hora_extra'),
    )
    
    def __repr__(self):
        return f'<HoraExtra {self.funcionario.nome} - {self.data}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'funcionario_id': self.funcionario_id,
            'funcionario_nome': self.funcionario.nome if self.funcionario else None,
            'periodo_id': self.periodo_id,
            'data': self.data.strftime('%Y-%m-%d'),
            'data_formatada': self.data.strftime('%d/%m/%Y'),
            'descricao': self.descricao,
            'created_at': self.created_at.strftime('%d/%m/%Y %H:%M') if self.created_at else None
        }