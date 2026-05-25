from sqlalchemy.orm import Session
from app import models, schemas
from app.security import gerar_hash_senha, verificar_senha
from app.models import Cobranca, Crianca, Usuario
from app.models import Presenca
from datetime import datetime, date, timedelta
from datetime import date
import calendar
from app.models import Mensalidade
from sqlalchemy import func
from app import models
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from calendar import monthrange

datetime.now(timezone.utc)

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

    presenca_aberta = db.query(Presenca)\
        .filter(
            Presenca.crianca_id == crianca_id,
            Presenca.empresa_id == empresa_id,
            Presenca.checkout == None
        ).first()

    if presenca_aberta:
        return None

    # 🔥 calcula início e fim do dia (Brasil → UTC)
    inicio = datetime.now(ZoneInfo("America/Sao_Paulo"))\
        .replace(hour=0, minute=0, second=0, microsecond=0)

    inicio = inicio.astimezone(timezone.utc)
    fim = inicio + timedelta(days=1)

    presenca_hoje = db.query(Presenca)\
        .filter(
            Presenca.crianca_id == crianca_id,
            Presenca.empresa_id == empresa_id,
            Presenca.checkin >= inicio,
            Presenca.checkin < fim
        ).first()

    if presenca_hoje:
        return None

    nova_presenca = Presenca(
        crianca_id=crianca_id,
        empresa_id=empresa_id,
        checkin=datetime.now(timezone.utc)
    )

    db.add(nova_presenca)
    db.commit()
    db.refresh(nova_presenca)

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

    presenca.checkout = datetime.now(timezone.utc)

    crianca = presenca.crianca

    # 🔥 cálculo extra
    valor_extra = calcular_valor_extra(
        presenca.checkin,
        presenca.checkout,
        crianca.horas_contratadas,
        crianca.tolerancia_minutos
    )

    # 🔥 formato padrão (IMPORTANTE)
    mes = datetime.now(timezone.utc).strftime("%m/%Y")

   # 🔥 pega última cobrança da criança
    ultima_cobranca = db.query(Cobranca)\
        .filter(
            Cobranca.crianca_id == crianca.id
        )\
        .order_by(Cobranca.id.desc())\
        .first()

    cobranca = None

    # 🔥 se última cobrança estiver pendente
    if ultima_cobranca and not ultima_cobranca.pago:
        cobranca = ultima_cobranca

    # 🔥 se não existir → cria nova cobrança
    if not cobranca:

        hoje_br = datetime.now(
            ZoneInfo("America/Sao_Paulo")
        )

        dia_vencimento = crianca.dia_vencimento or 10

        # 🔥 calcula próximo vencimento
        if hoje_br.day > dia_vencimento:

            if hoje_br.month == 12:
                mes_num = 1
                ano = hoje_br.year + 1
            else:
                mes_num = hoje_br.month + 1
                ano = hoje_br.year

        else:
            mes_num = hoje_br.month
            ano = hoje_br.year

        ultimo_dia = monthrange(ano, mes_num)[1]

        dia_final = min(
            dia_vencimento,
            ultimo_dia
        )

        vencimento = datetime(
            ano,
            mes_num,
            dia_final,
            0,
            0,
            0,
            tzinfo=ZoneInfo("America/Sao_Paulo")
        )

        cobranca = models.Cobranca(
            crianca_id=crianca.id,
            empresa_id=crianca.empresa_id,
            valor=crianca.valor or 0,
            mes=vencimento.strftime("%m/%Y"),
            data_vencimento=vencimento.date(),
            pago=False
        )

        db.add(cobranca)

        db.flush()

    # 🔥 soma valor
    ja_tem = db.query(models.CobrancaItem)\
    .filter(
        models.CobrancaItem.cobranca_id == cobranca.id,
        models.CobrancaItem.descricao == f"Hora extra - {presenca.checkin.strftime('%d/%m %H:%M')}"
    )\
    .first()

    if valor_extra > 0 and not ja_tem:
        

        item = models.CobrancaItem(
            cobranca_id=cobranca.id,
            descricao=f"Hora extra - {presenca.checkin.strftime('%d/%m %H:%M')}",
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
        p.checkout = datetime.now(timezone.utc)

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
    hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).date()

    presencas = db.query(Presenca)\
        .filter(Presenca.empresa_id == empresa_id)\
        .all()

    resultado = []

    for p in presencas:
        if p.checkin.astimezone(ZoneInfo("America/Sao_Paulo")).date() == hoje:
            resultado.append(p)

    return resultado

def resumo_diario(db: Session, empresa_id: int):
    hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).date()

    presencas = db.query(Presenca)\
        .filter(Presenca.empresa_id == empresa_id)\
        .all()

    total_hoje = 0
    presentes_agora = 0
    ja_sairam = 0

    for p in presencas:

        # 🔥 converte para horário BR
        data_checkin = p.checkin.astimezone(
            ZoneInfo("America/Sao_Paulo")
        ).date()

        # 🔥 somente hoje
        if data_checkin == hoje:

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
    hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).date()

    presencas = db.query(Presenca)\
        .filter(Presenca.empresa_id == empresa_id)\
        .all()

    resultado = {}

    for p in presencas:
        
        data_checkin = p.checkin.astimezone(
            ZoneInfo("America/Sao_Paulo")
        ).date()

        if data_checkin == hoje:

            # Se ainda não fez checkout, considera agora
            checkout = p.checkout or datetime.now(timezone.utc)

            minutos = int((checkout - p.checkin).total_seconds() / 60)

            if p.crianca_id not in resultado:
                resultado[p.crianca_id] = {
                    "crianca_id": p.crianca_id,
                    "nome": p.crianca.nome,
                    "tempo_total_minutos": 0
                }

            resultado[p.crianca_id]["tempo_total_minutos"] += minutos

    return list(resultado.values())

def processar_financeiro_checkout(
    db: Session,
    presenca
):

    if not presenca.checkout:
        return

    crianca = db.query(models.Crianca)\
        .filter(
            models.Crianca.id == presenca.crianca_id
        )\
        .first()

    if not crianca:
        return

    valor_extra = calcular_valor_extra(
        presenca.checkin,
        presenca.checkout,
        crianca.horas_contratadas,
        crianca.tolerancia_minutos
    )

    hoje_br = presenca.checkin.astimezone(
        ZoneInfo("America/Sao_Paulo")
    )

    mes = hoje_br.strftime("%m/%Y")

    # 🔥 pega última cobrança da criança
    ultima_cobranca = db.query(Cobranca)\
        .filter(
            Cobranca.crianca_id == crianca.id
        )\
        .order_by(Cobranca.id.desc())\
        .first()

    cobranca = None

    # 🔥 se última cobrança estiver pendente
    if ultima_cobranca and not ultima_cobranca.pago:
        cobranca = ultima_cobranca

    if not cobranca:

        hoje_br = datetime.now(
            ZoneInfo("America/Sao_Paulo")
        )

        dia_vencimento = crianca.dia_vencimento or 10

        if hoje_br.day > dia_vencimento:

            if hoje_br.month == 12:
                mes_num = 1
                ano = hoje_br.year + 1
            else:
                mes_num = hoje_br.month + 1
                ano = hoje_br.year

        else:
            mes_num = hoje_br.month
            ano = hoje_br.year

        ultimo_dia = monthrange(ano, mes_num)[1]

        dia_final = min(
            dia_vencimento,
            ultimo_dia
        )

        vencimento = datetime(
            ano,
            mes_num,
            dia_final,
            0,
            0,
            0,
            tzinfo=ZoneInfo("America/Sao_Paulo")
        )

        cobranca = models.Cobranca(
            crianca_id=crianca.id,
            empresa_id=crianca.empresa_id,
            valor=crianca.valor or 0,
            mes=vencimento.strftime("%m/%Y"),
            data_vencimento=vencimento.date(),
            pago=False
        )

        db.add(cobranca)

        db.flush()

    if valor_extra > 0:

        descricao = (
            f"Hora extra - "
            f"{presenca.checkin.strftime('%d/%m %H:%M')}"
        )

        existe = db.query(models.CobrancaItem)\
            .filter(
                models.CobrancaItem.cobranca_id == cobranca.id,
                models.CobrancaItem.descricao == descricao
            )\
            .first()

        if not existe:

            item = models.CobrancaItem(
                cobranca_id=cobranca.id,
                descricao=descricao,
                valor=valor_extra,
                data=presenca.checkin
            )

            db.add(item)

    db.commit()

def calcular_valor_extra(
    checkin,
    checkout,
    horas_contratadas,
    tolerancia_minutos=0
):

    if not checkout or not horas_contratadas:
        return 0

    # 🔥 timezone seguro
    if checkin.tzinfo is None:
        checkin = checkin.replace(tzinfo=timezone.utc)

    if checkout.tzinfo is None:
        checkout = checkout.replace(tzinfo=timezone.utc)

    # 🔥 total em minutos
    minutos_total = (
        (checkout - checkin).total_seconds() / 60
    )

    # 🔥 contratado em minutos
    minutos_contratados = (
        float(horas_contratadas) * 60
    )

    # 🔥 limite final
    limite = (
        minutos_contratados +
        (tolerancia_minutos or 0)
    )

    # 🔥 dentro da tolerância
    if minutos_total <= limite:
        return 0

    # 🔥 apenas excedente REAL
    minutos_extras = minutos_total - limite

    # 🔥 proporcional
    valor_extra = (
        minutos_extras / 60
    ) * 5

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
    mensalidade.data_pagamento = datetime.now(timezone.utc)

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

def listar_cobrancas(db: Session, empresa_id: int):

    hoje = datetime.now(
        ZoneInfo("America/Sao_Paulo")
    )

    limite_pago = hoje - timedelta(days=10)

    cobrancas = db.query(models.Cobranca)\
        .filter(
            models.Cobranca.empresa_id == empresa_id
        )\
        .order_by(models.Cobranca.id.desc())\
        .all()

    resultado = []

    for c in cobrancas:

        # 🔥 cobrança paga antiga → ocultar
        if c.pago and c.data_pagamento:

            data_pagamento = c.data_pagamento

            # 🔥 se veio sem timezone
            if data_pagamento.tzinfo is None:
                data_pagamento = data_pagamento.replace(
                    tzinfo=timezone.utc
                )

            # 🔥 oculta após 10 dias
            if data_pagamento < limite_pago:
                continue

       # 🔥 soma extras
        extras = sum(
            (item.valor or 0)
            for item in c.itens
        )

        # 🔥 total final
        valor_total = (
            (c.valor or 0)
            + extras
        )

        resultado.append({
            "id": c.id,

            "crianca_id": c.crianca_id,

            "crianca_nome": (
                c.crianca.nome
                if c.crianca else ""
            ),

            # 🔥 total exibido
            "valor": round(valor_total, 2),

            # 🔥 mensalidade fixa
            "mensalidade": c.valor or 0,

            # 🔥 extras separados
            "extras": round(extras, 2),

            "pago": c.pago,

            "data_pagamento": c.data_pagamento,

            "data_vencimento": c.data_vencimento,

            "telefone": (
                c.crianca.responsaveis[0].telefone
                if c.crianca
                and c.crianca.responsaveis
                else ""
            )
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
    cobranca.data_pagamento = datetime.now(timezone.utc)  # 🔥 ESSENCIAL

    db.commit()
    db.refresh(cobranca)

    return cobranca
