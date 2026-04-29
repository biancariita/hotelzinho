from sqlalchemy.orm import Session
from app import models, schemas
from app.security import gerar_hash_senha, verificar_senha
from app.models import Crianca, Usuario
from app.models import Presenca
from datetime import datetime, date, timedelta
from datetime import date
import calendar
from app.models import Mensalidade
from sqlalchemy import func
from app import models


import requests

def criar_usuario(db: Session, usuario: schemas.UsuarioCreate):
    senha_hash = gerar_hash_senha(usuario.senha)

    db_usuario = Usuario(
        nome=usuario.nome,
        email=usuario.email,
        senha_hash=senha_hash,
        empresa_id=usuario.empresa_id,
        role="admin"
    )

    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario

def fazer_checkin(db: Session, crianca_id: int, empresa_id: int):

    # 1️⃣ Verifica se já está presente (sem checkout)
    presenca_aberta = db.query(Presenca)\
        .filter(
            Presenca.crianca_id == crianca_id,
            Presenca.empresa_id == empresa_id,
            Presenca.checkout == None
        )\
        .first()

    if presenca_aberta:
        return None

    # 2️⃣ Verifica se já teve check-in hoje
    hoje = date.today()

    presenca_hoje = db.query(Presenca)\
    .filter(
        Presenca.crianca_id == crianca_id,
        Presenca.empresa_id == empresa_id,
        Presenca.checkin >= datetime.combine(hoje, datetime.min.time()),
        Presenca.checkin <= datetime.combine(hoje, datetime.max.time())
    )\
    .first()

    if presenca_hoje:
        return None

    # 3️⃣ Se passou nas validações, cria check-in
    nova_presenca = Presenca(
        crianca_id=crianca_id,
        empresa_id=empresa_id,
        checkin=datetime.now()
    )
    inadimplente = db.query(models.Mensalidade)\
    .filter(
        models.Mensalidade.crianca_id == crianca_id,
        models.Mensalidade.empresa_id == empresa_id,
        models.Mensalidade.pago == False
    )\
    .first()

    if inadimplente:
        print("⚠ criança inadimplente")

    db.add(nova_presenca)
    db.commit()
    db.refresh(nova_presenca)
    print("CHECKIN SALVO:", datetime.now())

    return nova_presenca

def fazer_checkin_manual(db, crianca_id, empresa_id, data_checkin):

    presenca_aberta = db.query(Presenca)\
        .filter(
            Presenca.crianca_id == crianca_id,
            Presenca.empresa_id == empresa_id,
            Presenca.checkout == None
        ).first()

    if presenca_aberta:
        return None

    nova = Presenca(
        crianca_id=crianca_id,
        empresa_id=empresa_id,
        checkin=data_checkin
    )

    db.add(nova)
    db.commit()
    db.refresh(nova)

    return nova

import json

def adicionar_detalhe(cobranca, tipo, valor):

    detalhes = []

    if cobranca.detalhes:
        detalhes = json.loads(cobranca.detalhes)

    detalhes.append({
        "tipo": tipo,
        "valor": valor
    })

    cobranca.detalhes = json.dumps(detalhes)


def fazer_checkout(db: Session, presenca_id: int):

    presenca = db.query(models.Presenca).filter(models.Presenca.id == presenca_id).first()

    if not presenca:
        return None

    presenca.checkout = datetime.now()

    crianca = presenca.crianca

    # 🔥 cálculo extra
    valor_extra = calcular_valor_extra(
        presenca.checkin,
        presenca.checkout,
        crianca.horas_contratadas,
        crianca.tolerancia_minutos
    )

    # 🔥 formato padrão (IMPORTANTE)
    mes = datetime.now().strftime("%m/%Y")

    # 🔥 tenta buscar cobrança
    cobranca = db.query(models.Cobranca)\
        .filter(
            models.Cobranca.crianca_id == crianca.id,
            models.Cobranca.mes == mes
        )\
        .first()

    # 🔥 SE NÃO EXISTIR → CRIA
    if not cobranca:
        cobranca = models.Cobranca(
            crianca_id=crianca.id,
            empresa_id=crianca.empresa_id,
            valor=crianca.valor or 0,
            mes=mes
        )
        db.add(cobranca)
        db.flush()  # 🔥 ESSENCIAL

    # 🔥 soma valor
    ja_tem = db.query(models.CobrancaItem)\
    .filter(
        models.CobrancaItem.cobranca_id == cobranca.id,
        models.CobrancaItem.descricao == f"Hora extra - {presenca.checkin.strftime('%d/%m')}"
    )\
    .first()

    if valor_extra > 0 and not ja_tem:
        cobranca.valor += valor_extra

        item = models.CobrancaItem(
            cobranca_id=cobranca.id,
            descricao=f"Hora extra - {presenca.checkin.strftime('%d/%m')}",
            valor=valor_extra
        )
        db.add(item)

    db.commit()

    return presenca

def fechar_presencas_antigas(db):

    presencas = db.query(models.Presenca)\
        .filter(models.Presenca.checkout == None)\
        .all()

    for p in presencas:
        p.checkout = datetime.now()

    db.commit()


def listar_presentes(db: Session, empresa_id: int):
    return db.query(Presenca)\
    .filter(Presenca.empresa_id == empresa_id)\
    .filter(Presenca.checkout == None)\
    .all()

def autenticar_usuario(db: Session, email: str, senha: str):

    usuario = db.query(Usuario).filter(Usuario.email == email).first()

    if not usuario:
            return None

    if not verificar_senha(senha, usuario.senha_hash):
            return None

    return usuario

def criar_crianca(db: Session, crianca: schemas.CriancaCreate, empresa_id: int):

    db_crianca = models.Crianca(
        nome=crianca.nome,
        data_nascimento=crianca.data_nascimento,
        alergias=crianca.alergias,
        observacoes=crianca.observacoes,
        dia_vencimento=crianca.dia_vencimento,
        autorizacao_imagem=crianca.autorizacao_imagem,
        empresa_id=empresa_id,
        plano=crianca.plano,
        valor=crianca.valor,
        horas_contratadas=crianca.horas_contratadas,
        tolerancia_minutos=crianca.tolerancia_minutos,
        
    )
    db.add(db_crianca)
    db.commit()
    db.refresh(db_crianca)

    # Criar responsáveis vinculados
    for resp in crianca.responsaveis:
        db_responsavel = models.Responsavel(
            nome=resp.nome,
            telefone=resp.telefone,
            cpf=resp.cpf,
            parentesco=resp.parentesco,
            endereco=resp.endereco,
            crianca_id=db_crianca.id,
            empresa_id=empresa_id
        )
        db.add(db_responsavel)

    db.add(db_crianca)
    db.commit()
    db.refresh(db_crianca)

    valor = 0
    db.commit()
    db.refresh(db_crianca)

    return db_crianca




def listar_criancas(db: Session, empresa_id: int):
    return db.query(models.Crianca)\
        .filter(models.Crianca.empresa_id == empresa_id)\
        .all()

def buscar_crianca(db: Session, crianca_id: int, empresa_id: int):
    return db.query(models.Crianca)\
        .filter(
            models.Crianca.id == crianca_id,
            models.Crianca.empresa_id == empresa_id
        )\
        .first()


def atualizar_crianca(
    db: Session,
    crianca_id: int,
    empresa_id: int,
    dados: schemas.CriancaCreate
):
    crianca = buscar_crianca(db, crianca_id, empresa_id)

    if not crianca:
        return None

    # Atualiza campos básicos
    crianca.nome = dados.nome
    crianca.data_nascimento = dados.data_nascimento
    crianca.alergias = dados.alergias
    crianca.observacoes = dados.observacoes
    crianca.plano = dados.plano
    crianca.valor = dados.valor
    if dados.dia_vencimento is not None:
        crianca.dia_vencimento = dados.dia_vencimento
    if dados.autorizacao_imagem is not None:
        crianca.autorizacao_imagem = dados.autorizacao_imagem
    crianca.horas_contratadas = dados.horas_contratadas
    crianca.tolerancia_minutos = dados.tolerancia_minutos
    
    # Remove responsáveis antigos
    db.query(models.Responsavel)\
        .filter(models.Responsavel.crianca_id == crianca.id)\
        .delete()

    # Cria novos responsáveis
    for resp in dados.responsaveis:
        novo_resp = models.Responsavel(
            nome=resp.nome,
            telefone=resp.telefone,
            cpf=resp.cpf,
            parentesco=resp.parentesco,
            endereco=resp.endereco,
            crianca_id=crianca.id,
            empresa_id=empresa_id
        )
        db.add(novo_resp)

    db.commit()
    db.refresh(crianca)

    return crianca

def deletar_crianca(db: Session, crianca_id: int, empresa_id: int):

    crianca = db.query(models.Crianca)\
        .filter(
            models.Crianca.id == crianca_id,
            models.Crianca.empresa_id == empresa_id
        ).first()

    if not crianca:
        return None

    # apagar responsáveis
    db.query(models.Responsavel)\
        .filter(models.Responsavel.crianca_id == crianca_id)\
        .delete()

    # apagar presenças
    db.query(models.Presenca)\
        .filter(models.Presenca.crianca_id == crianca_id)\
        .delete()

    # apagar cobranças
    db.query(models.Cobranca)\
        .filter(models.Cobranca.crianca_id == crianca_id)\
        .delete()

    db.delete(crianca)

    db.commit()

    return True

def relatorio_hoje(db: Session, empresa_id: int):
    hoje = date.today()

    presencas = db.query(Presenca)\
        .filter(Presenca.empresa_id == empresa_id)\
        .all()

    resultado = []

    for p in presencas:
        if p.checkin.date() == hoje:
            resultado.append(p)

    return resultado

def resumo_diario(db: Session, empresa_id: int):
    hoje = date.today()

    presencas = db.query(Presenca)\
        .filter(Presenca.empresa_id == empresa_id)\
        .all()

    total_hoje = 0
    presentes_agora = 0
    ja_sairam = 0

    for p in presencas:
        if p.checkin.date() == hoje:
            total_hoje += 1
            if p.checkout is None:
                presentes_agora += 1
            else:
                ja_sairam += 1

    return {
        "total_hoje": total_hoje,
        "presentes_agora": presentes_agora,
        "ja_sairam": ja_sairam
    }

def tempo_total_hoje(db: Session, empresa_id: int):
    hoje = date.today()

    presencas = db.query(Presenca)\
        .filter(Presenca.empresa_id == empresa_id)\
        .all()

    resultado = {}

    for p in presencas:
        if p.checkin.date() == hoje:

            # Se ainda não fez checkout, considera agora
            checkout = p.checkout or datetime.now()

            minutos = int((checkout - p.checkin).total_seconds() / 60)

            if p.crianca_id not in resultado:
                resultado[p.crianca_id] = {
                    "crianca_id": p.crianca_id,
                    "nome": p.crianca.nome,
                    "tempo_total_minutos": 0
                }

            resultado[p.crianca_id]["tempo_total_minutos"] += minutos

    return list(resultado.values())

def calcular_valor_extra(checkin, checkout, horas_contratadas, tolerancia_minutos=0):

    if not checkout or not horas_contratadas:
        return 0

    #  diferença total em horas
    diferenca = checkout - checkin
    horas_total = diferenca.total_seconds() / 3600

    #  aplica tolerância
    tolerancia_horas = (tolerancia_minutos or 0) / 60

    if horas_total <= (horas_contratadas + tolerancia_horas):
        return 0

    #  calcula horas extras
    horas_extras = horas_total - horas_contratadas

    #  valor por hora
    valor_hora_extra = 5

    valor_extra = horas_extras * valor_hora_extra

    return round(valor_extra, 2)

def criar_mensalidade(db: Session, dados: schemas.MensalidadeCreate, empresa_id: int):
    mensalidade = Mensalidade(
        crianca_id=dados.crianca_id,
        empresa_id=empresa_id,
        valor=dados.valor,
        mes=dados.mes
    )

    db.add(mensalidade)
    db.commit()
    db.refresh(mensalidade)
    return mensalidade

def listar_mensalidades(db: Session, empresa_id: int):
    return db.query(Mensalidade)\
        .filter(Mensalidade.empresa_id == empresa_id)\
        .all()


def marcar_como_pago(db: Session, mensalidade_id: int, empresa_id: int):
    mensalidade = db.query(Mensalidade)\
        .filter(
            Mensalidade.id == mensalidade_id,
            Mensalidade.empresa_id == empresa_id
        )\
        .first()

    if not mensalidade:
        return None

    mensalidade.pago = True
    mensalidade.data_pagamento = datetime.now()

    db.commit()
    db.refresh(mensalidade)
    return mensalidade

def gerar_cobrancas_whatsapp(db: Session):

    hoje = date.today()

    mensalidades = db.query(models.Mensalidade)\
        .filter(models.Mensalidade.pago == False)\
        .all()

    resultado = []

    for m in mensalidades:

        if not m.data_vencimento:
            continue

        # só no dia do vencimento
        if m.data_vencimento != hoje:
            continue

        crianca = db.query(models.Crianca)\
            .filter(models.Crianca.id == m.crianca_id)\
            .first()

        if not crianca or not crianca.responsaveis:
            continue

        resp = crianca.responsaveis[0]

        mensagem = f"""
        Olá!

        Cobrança do Hotelzinho:

        {crianca.nome}
        R$ {m.valor:.2f}

        Vencimento: {m.data_vencimento.strftime('%d/%m')}

        Escolha como pagar:

        PIX:
        http://localhost:8000/cobrancas/{m.id}/pix

        Cartão:
        http://localhost:8000/cobrancas/{m.id}/asaas
        """

        resultado.append({
            "telefone": resp.telefone,
            "mensagem": mensagem
        })

    return resultado
            
def resumo_financeiro_mes(db: Session, empresa_id: int, mes: str):
    mensalidades = db.query(Mensalidade)\
        .filter(
            Mensalidade.empresa_id == empresa_id,
            Mensalidade.mes == mes
        )\
        .all()

    total_mensalidades = len(mensalidades)
    total_recebido = 0.0
    total_pendente = 0.0

    for m in mensalidades:
        if m.pago:
            total_recebido += m.valor
        else:
            total_pendente += m.valor

    return {
        "mes": mes,
        "total_mensalidades": total_mensalidades,
        "total_recebido": total_recebido,
        "total_pendente": total_pendente
    }

def listar_gastos(db, empresa_id, mes):

    gastos = db.query(models.Gasto)\
        .filter(
            models.Gasto.empresa_id == empresa_id,
            models.Gasto.mes == mes
        )\
        .all()

    total = sum((g.valor or 0) for g in gastos)

    return {
        "lista": gastos,
        "total": total
    }

def listar_inadimplentes(db: Session, empresa_id: int, mes: str):
    mensalidades = db.query(Mensalidade)\
        .filter(
            Mensalidade.empresa_id == empresa_id,
            Mensalidade.mes == mes,
            Mensalidade.pago == False
        )\
        .all()

    resultado = []

    for m in mensalidades:
        resultado.append({
            "crianca_id": m.crianca_id,
            "nome": m.crianca.nome,
            "valor": m.valor,
            "mes": m.mes
        })

    return resultado

def dashboard_financeiro(db: Session, empresa_id: int, mes: str):

    cobrancas = db.query(models.Cobranca)\
        .filter(
            models.Cobranca.empresa_id == empresa_id,
            models.Cobranca.mes == mes
        )\
        .all()

    total_recebido = 0.0

    for c in cobrancas:
        if c.pago:
            total_recebido += c.valor

    return {
        "mes": mes,
        "total_recebido": total_recebido
    }

def listar_cobrancas(db, empresa_id):
    cobrancas = db.query(models.Cobranca)\
    .filter(
        models.Cobranca.empresa_id == empresa_id,
        models.Cobranca.pago == False  # 🔥 só pendentes
    )\
    .all()

    resultado = []

    for c in cobrancas:
        resultado.append({
            "id": c.id,
            "crianca_id": c.crianca_id,
            "crianca_nome": c.crianca.nome if c.crianca else "",
            "valor": c.valor,
            "pago": c.pago,
            "data_pagamento": c.data_pagamento,
            "data_vencimento": c.data_vencimento,
            "telefone": c.crianca.responsaveis[0].telefone if c.crianca and c.crianca.responsaveis else "",
            "mes": c.mes
        })

    return resultado


def marcar_cobranca_como_paga(db: Session, cobranca_id: int, empresa_id: int):
    cobranca = db.query(models.Cobranca)\
        .filter(
            models.Cobranca.id == cobranca_id,
            models.Cobranca.empresa_id == empresa_id
        )\
        .first()

    if not cobranca:
        return None

    cobranca.pago = True
    cobranca.data_pagamento = datetime.now()  # 🔥 ESSENCIAL

    db.commit()
    db.refresh(cobranca)

    return cobranca
