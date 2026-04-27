from sqlalchemy import Column, Integer, String, Date, Boolean
from app.database import Base
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy import DateTime
from datetime import datetime
from sqlalchemy import Float
from sqlalchemy.orm import relationship
import json
from sqlalchemy import Text


class Empresa(Base):

    __tablename__ = "empresas"

    id = Column(Integer, primary_key=True, index=True)

    nome = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)

    cnpj = Column(String, nullable=True)
    telefone = Column(String, nullable=True)
    endereco = Column(String, nullable=True)
    responsavel = Column(String, nullable=True)

    asaas_api_key = Column(String, nullable=True)

    pix_chave = Column(String, nullable=True)

    banco_nome = Column(String, nullable=True)
    banco_agencia = Column(String, nullable=True)
    banco_conta = Column(String, nullable=True)

    valor_hora = Column(Float, nullable=True)
    valor_diaria = Column(Float, nullable=True)

    valor_semanal_integral = Column(Float, nullable=True)
    valor_semanal_meio = Column(Float, nullable=True)

    valor_mensal_integral = Column(Float, nullable=True)
    valor_mensal_meio = Column(Float, nullable=True)

    valor_sabado = Column(Float, nullable=True)
    
    tipo_cobranca = Column(String, default="hora")

class Crianca(Base):
    __tablename__ = "criancas"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    data_nascimento = Column(Date)
    alergias = Column(String)
    observacoes = Column(String)
    autorizacao_imagem = Column(Boolean, default=False)
    dia_vencimento = Column(Integer, nullable=True)

    empresa_id = Column(Integer, ForeignKey("empresas.id"))
    ativo = Column(Boolean, default=True)
    
    asaas_customer_id = Column(String, nullable=True)

    tipo_cobranca = Column(String, default="hora")
    

    responsaveis = relationship(
        "Responsavel",
        back_populates="crianca",
        cascade="all, delete"
    )


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    senha_hash = Column(String, nullable=False)

    empresa_id = Column(Integer, ForeignKey("empresas.id"))
    empresa = relationship("Empresa")

    role = Column(String, default="atendente")

    telefone = Column(String, nullable=True)

    codigo_recuperacao = Column(String, nullable=True)

    codigo_expira = Column(DateTime, nullable=True)

class Presenca(Base):
    __tablename__ = "presencas"

    id = Column(Integer, primary_key=True, index=True)

    crianca_id = Column(Integer, ForeignKey("criancas.id"))
    empresa_id = Column(Integer, ForeignKey("empresas.id"))

    checkin = Column(DateTime, default=datetime.utcnow)
    checkout = Column(DateTime, nullable=True)

    crianca = relationship("Crianca")

from sqlalchemy import Float

class Mensalidade(Base):
    __tablename__ = "mensalidades"

    id = Column(Integer, primary_key=True, index=True)

    crianca_id = Column(Integer, ForeignKey("criancas.id"))
    empresa_id = Column(Integer, ForeignKey("empresas.id"))

    valor = Column(Float, nullable=False)
    mes = Column(String, nullable=False)  # exemplo: "02/2026"
    pago = Column(Boolean, default=False)

    crianca = relationship("Crianca")

class Cobranca(Base):
    __tablename__ = "cobrancas"

    id = Column(Integer, primary_key=True, index=True)

    crianca_id = Column(Integer, ForeignKey("criancas.id"))
    empresa_id = Column(Integer, ForeignKey("empresas.id"))

    valor = Column(Float, nullable=False)
    minutos = Column(Integer, nullable=True)
    tipo = Column(String)  # "hora" ou "mensal"
    pago = Column(Boolean, default=False)

    data_vencimento = Column(Date, nullable=True)
    data_pagamento = Column(DateTime, nullable=True)

    detalhes = Column(Text, nullable=True)

    mes = Column(String, nullable=True)
    
    metodo_pagamento = Column(String, nullable=True)  # pix, cartão
    gateway_id = Column(String, nullable=True)
    link_pagamento = Column(String, nullable=True)

    criado_em = Column(DateTime, default=datetime.utcnow)

    crianca = relationship("Crianca")
    motivo_desconto = Column(String, nullable=True)
    valor_original = Column(Float, nullable=True)

class Responsavel(Base):
    __tablename__ = "responsaveis"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    telefone = Column(String)
    cpf = Column(String)
    rg = Column(String)
    parentesco = Column(String)
    endereco = Column(String, nullable=True)

    crianca_id = Column(Integer, ForeignKey("criancas.id"))
    empresa_id = Column(Integer, ForeignKey("empresas.id"))

    crianca = relationship("Crianca", back_populates="responsaveis")

class HistoricoFinanceiro(Base):
    __tablename__ = "historico_financeiro"

    id = Column(Integer, primary_key=True, index=True)
    cobranca_id = Column(Integer, ForeignKey("cobrancas.id"))
    empresa_id = Column(Integer, ForeignKey("empresas.id"))
    descricao = Column(String)
    data = Column(DateTime, default=datetime.utcnow)

class Gasto(Base):
    __tablename__ = "gastos"

    id = Column(Integer, primary_key=True)
    descricao = Column(String)
    valor = Column(Float)
    mes = Column(String)
    empresa_id = Column(Integer)

class Fechamento(Base):
    __tablename__ = "fechamentos"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"))
    mes = Column(String)
    fechado = Column(Boolean, default=False)

class Faturamento(Base):
    __tablename__ = "faturamentos"

    id = Column(Integer, primary_key=True)
    descricao = Column(String)
    valor = Column(Float)
    mes = Column(String)  # 🔥 ESSENCIAL (04/2026)
    empresa_id = Column(Integer)