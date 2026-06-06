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
    
    #cálculo extra
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

    # 🔥 PRIMEIRA COBRANÇA DA CRIANÇA
    if not ultima_cobranca:

        hoje_br = datetime.now(
            ZoneInfo("America/Sao_Paulo")
        )

        dia_vencimento = crianca.dia_vencimento or 10

        vencimento = datetime(
            hoje_br.year,
            hoje_br.month,
            min(
                dia_vencimento,
                monthrange(
                    hoje_br.year,
                    hoje_br.month
                )[1]
            ),
            0,
            0,
            0
        )

        cobranca = models.Cobranca(
            crianca_id=crianca.id,
            empresa_id=crianca.empresa_id,
            valor=crianca.valor or 0,
            mes=hoje_br.strftime("%m/%Y"),
            data_vencimento=vencimento.date(),
            pago=False
        )

        db.add(cobranca)
        db.flush()

    # 🔥 usa cobrança pendente existente
    elif not ultima_cobranca.pago:

        cobranca = ultima_cobranca

    # 🔥 última cobrança já paga
    # cria nova mensalidade automaticamente
    else:

        hoje_br = datetime.now(
            ZoneInfo("America/Sao_Paulo")
        )

        dia_vencimento = crianca.dia_vencimento or 10

        # 🔥 próximo mês da cobrança paga
        mes_atual = int(
            ultima_cobranca.mes.split("/")[0]
        )

        ano_atual = int(
            ultima_cobranca.mes.split("/")[1]
        )

        if mes_atual == 12:
            novo_mes = 1
            novo_ano = ano_atual + 1
        else:
            novo_mes = mes_atual + 1
            novo_ano = ano_atual

        ultimo_dia = monthrange(
            novo_ano,
            novo_mes
        )[1]

        dia_final = min(
            dia_vencimento,
            ultimo_dia
        )

        vencimento = datetime(
            novo_ano,
            novo_mes,
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
            mes=f"{novo_mes:02d}/{novo_ano}",
            data_vencimento=vencimento.date(),
            pago=False
        )

        db.add(cobranca)
        db.flush()

    if not cobranca:
        db.commit()
        return presenca

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

    # 🔥 PRIMEIRA MENSALIDADE JÁ PAGA
    if hasattr(crianca, "primeira_mensalidade_paga"):

        if crianca.primeira_mensalidade_paga:

            if crianca.mes_pago:

                ano, mes = crianca.mes_pago.split("-")

                ultimo_dia = monthrange(
                    int(ano),
                    int(mes)
                )[1]

                dia_final = min(
                    db_crianca.dia_vencimento or 10,
                    ultimo_dia
                )

                vencimento_pago = datetime(
                    int(ano),
                    int(mes),
                    dia_final
                ).date()

                cobranca_paga = models.Cobranca(

                    crianca_id=db_crianca.id,

                    empresa_id=empresa_id,

                    valor=db_crianca.valor or 0,

                    mes=f"{mes}/{ano}",

                    tipo="mensal",

                    pago=True,

                    data_pagamento=datetime.now(
                        ZoneInfo("America/Sao_Paulo")
                    ),

                    data_vencimento=vencimento_pago
                )
                db.add(cobranca_paga)

                # 🔥 próximo mês
                if int(mes) == 12:
                    prox_mes = 1
                    prox_ano = int(ano) + 1
                else:
                    prox_mes = int(mes) + 1
                    prox_ano = int(ano)

                ultimo_dia_prox = monthrange(
                    prox_ano,
                    prox_mes
                )[1]

                dia_final_prox = min(
                    db_crianca.dia_vencimento or 10,
                    ultimo_dia_prox
                )

                vencimento_proximo = datetime(
                    prox_ano,
                    prox_mes,
                    dia_final_prox
                ).date()

                nova_cobranca = models.Cobranca(
                    crianca_id=db_crianca.id,
                    empresa_id=empresa_id,
                    valor=db_crianca.valor or 0,
                    mes=f"{prox_mes:02d}/{prox_ano}",
                    pago=False,
                    data_vencimento=vencimento_proximo
                )

                db.add(nova_cobranca)

                db.commit()

    db.refresh(db_crianca)

    return db_crianca

def listar_criancas(db: Session, empresa_id: int):
    return db.query(models.Crianca)\
        .filter(models.Crianca.empresa_id == empresa_id)\
        .order_by(models.Crianca.nome)\
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
    # 🔥 recalcula horas extras antigas

    presencas = db.query(models.Presenca)\
        .filter(
            models.Presenca.crianca_id == crianca.id,
            models.Presenca.checkout != None
        )\
        .all()

    for p in presencas:

        novo_valor = calcular_valor_extra(
            p.checkin,
            p.checkout,
            crianca.horas_contratadas,
            crianca.tolerancia_minutos
        )

        descricao = (
            f"Hora extra - "
            f"{p.checkin.strftime('%d/%m %H:%M')}"
        )

        item = db.query(models.CobrancaItem)\
            .filter(
                models.CobrancaItem.descricao == descricao
            )\
            .first()

        if item:

        # 🔥 NÃO TEM MAIS EXTRA
            if novo_valor <= 0:

                db.delete(item)

            # 🔥 TEM EXTRA
            else:

                item.valor = novo_valor
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

   
    if ultima_cobranca and not ultima_cobranca.pago:

        cobranca = ultima_cobranca

    # 🔥 última cobrança já paga
    # cria nova mensalidade automaticamente
    elif ultima_cobranca and ultima_cobranca.pago:

        hoje_br = datetime.now(
            ZoneInfo("America/Sao_Paulo")
        )

        dia_vencimento = crianca.dia_vencimento or 10

        # 🔥 próximo mês da cobrança paga
        mes_atual = int(
            ultima_cobranca.mes.split("/")[0]
        )

        ano_atual = int(
            ultima_cobranca.mes.split("/")[1]
        )

        if mes_atual == 12:
            novo_mes = 1
            novo_ano = ano_atual + 1
        else:
            novo_mes = mes_atual + 1
            novo_ano = ano_atual

        ultimo_dia = monthrange(
            novo_ano,
            novo_mes
        )[1]

        dia_final = min(
            dia_vencimento,
            ultimo_dia
        )

        vencimento = datetime(
            novo_ano,
            novo_mes,
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
            mes=f"{novo_mes:02d}/{novo_ano}",
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

    if not checkout:
        return 0

    if checkin.tzinfo is None:
        checkin = checkin.replace(tzinfo=timezone.utc)

    if checkout.tzinfo is None:
        checkout = checkout.replace(tzinfo=timezone.utc)

    minutos_total = (
    checkout - checkin
    ).total_seconds() / 60

    # 🔥 horas contratadas → minutos
    minutos_contratados = (
        horas_contratadas or 0
    ) * 60

    # 🔥 tolerância apenas para liberar ou cobrar
    limite_tolerancia = (
        minutos_contratados
        + (tolerancia_minutos or 0)
    )

    # 🔥 ficou dentro da tolerância
    if minutos_total <= limite_tolerancia:
        return 0

    # 🔥 passou da tolerância
    minutos_extra = (
        minutos_total - minutos_contratados
    )

    # 🔥 R$5 por hora proporcional
    valor_por_minuto = 5 / 60

    valor_extra = (
        minutos_extra * valor_por_minuto
    )

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

    cobrancas = db.query(models.Cobranca)\
        .filter(
            models.Cobranca.empresa_id == empresa_id
        )\
        .order_by(models.Cobranca.id.desc())\
        .all()

    resultado = []

    for c in cobrancas:

        # 🔥 soma extras
        extras = sum(
            (i.valor or 0)
            for i in c.itens
        )

        # 🔥 total final
        total = (c.valor or 0) + extras

        telefone = ""

        if c.crianca and c.crianca.responsaveis:

            telefone = (
                c.crianca
                .responsaveis[0]
                .telefone or ""
            )

        resultado.append({

            "id": c.id,

            "crianca_id":
                c.crianca_id,

            "crianca_nome":
                c.crianca.nome
                if c.crianca else "-",

            # 🔥 valor final com extras
            "valor":
                total,

            "pago":
                c.pago,

            "data_pagamento":
                c.data_pagamento,

            "data_vencimento":
                c.data_vencimento,

            "telefone":
                telefone,

            "mes":
                c.mes
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
