from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional

# ==============================
# EMPRESA
# ==============================

class ConfigEmpresa(BaseModel):

    # PERFIL EMPRESA
    nome: str | None = None
    responsavel: str | None = None
    cnpj: str | None = None
    telefone: str | None = None
    email: str | None = None
    endereco: str | None = None

    # FINANCEIRO
    pix_chave: str | None = None
    banco_nome: str | None = None
    banco_agencia: str | None = None
    banco_conta: str | None = None
    asaas_api_key: str | None = None

    valor_hora: float | None = None
    valor_diaria: float | None = None
    valor_semanal_integral: float | None = None
    valor_semanal_meio: float | None = None
    valor_mensal_integral: float | None = None
    valor_mensal_meio: float | None = None

    valor_sabado: float | None = None

    tipo_cobranca: str | None = None

    
class EmpresaPerfil(BaseModel):

    nome: str
    email: str | None = None
    cnpj: str | None = None
    telefone: str | None = None
    endereco: str | None = None
    responsavel: str | None = None

class RecuperarSenha(BaseModel):

    email: str | None = None
    telefone: str | None = None

class NovaSenha(BaseModel):

    codigo: str
    nova_senha: str
# ==============================
# RESPONSÁVEL
# ==============================

class ResponsavelCreate(BaseModel):
    nome: str
    telefone: str | None = None
    cpf: str | None = None
    rg: str | None = None
    parentesco: str | None = None
    endereco: str | None = None


class ResponsavelResponse(BaseModel):
    id: int
    nome: str
    telefone: str | None
    cpf: str | None
    rg: str | None
    parentesco: str | None
    endereco: str | None 

    class Config:
        from_attributes = True


# ==============================
# CRIANÇA
# ==============================

class CriancaCreate(BaseModel):
    nome: str
    data_nascimento: date | None = None
    alergias: str | None = None
    observacoes: str | None = None
    autorizacao_imagem: bool | None = None
    responsaveis: list[ResponsavelCreate] = []
    dia_vencimento: int | None = None

    valor_hora: float | None = None
    valor_diaria: float | None = None
    valor_semanal_integral: float | None = None
    valor_semanal_meio: float | None = None
    valor_mensal_integral: float | None = None
    valor_mensal_meio: float | None = None

    valor_sabado: float | None = None

    tipo_cobranca: str | None = None



class CriancaResponse(BaseModel):
    id: int
    nome: str
    data_nascimento: date | None
    alergias: str | None
    observacoes: str | None
    autorizacao_imagem: bool | None 
    tipo_cobranca: str | None   # 🔥 ADICIONA
    dia_vencimento: int | None  # 🔥 ADICIONA
    responsaveis: list[ResponsavelResponse]

    class Config:
        from_attributes = True


# ==============================
# USUÁRIO
# ==============================

class UsuarioResponse(BaseModel):
    id: int
    nome: str
    email: str
    empresa_id: int
    role: str

    class Config:
        from_attributes = True

class UsuarioCreate(BaseModel):
    nome: str
    email: str
    senha: str
    empresa_id: int


class Token(BaseModel):
    access_token: str
    token_type: str


# ==============================
# PRESENÇA
# ==============================

class PresencaResponse(BaseModel):
    id: int
    crianca: CriancaResponse 
    checkin: datetime
    checkout: datetime | None

    class Config:
        from_attributes = True

class ResumoDiario(BaseModel):
    total_hoje: int
    presentes_agora: int
    ja_sairam: int

class TempoHoje(BaseModel):
    crianca_id: int
    nome: str
    tempo_total_minutos: int



# ==============================
# MENSALIDADE
# ==============================

class MensalidadeCreate(BaseModel):
    crianca_id: int
    valor: float
    mes: str


class MensalidadeResponse(BaseModel):
    id: int
    crianca_id: int
    valor: float
    mes: str
    pago: bool

    class Config:
        from_attributes = True

class ResumoFinanceiro(BaseModel):
    mes: str
    total_mensalidades: int
    total_recebido: float
    total_pendente: float


class Inadimplente(BaseModel):
    crianca_id: int
    nome: str
    valor: float
    mes: str


# ==============================
# DASHBOARD
# ==============================

class DashboardFinanceiro(BaseModel):
    mes: str
    total_mensalidades: int
    total_recebido: float
    total_pendente: float
    percentual_pago: float

class CobrancaResponse(BaseModel):
    id: int
    crianca_id: int
    crianca_nome: str
    valor: float
    pago: bool

    data_pagamento: datetime | None = None
    data_vencimento: date | None = None
    telefone: str | None = None
    mes: str | None = None

class Config:
    from_attributes = True

class ConfiguracaoFinanceira(BaseModel):
    svalor_hora: float | None = None
    valor_diaria: float | None = None
    valor_semanal_integral: float | None = None
    valor_semanal_meio: float | None = None
    valor_mensal_integral: float | None = None
    valor_mensal_meio: float | None = None

    valor_sabado: float | None = None
    tipo_cobranca: str  # hora, diaria, mensal
    tipo_cobranca: str | None = None

