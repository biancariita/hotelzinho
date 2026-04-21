import json

from fastapi import FastAPI, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import engine, SessionLocal
from app.database import get_db
from app import models, schemas, crud
from app.security import criar_token, gerar_hash_senha, verificar_senha
from fastapi import HTTPException
from app.security import get_usuario_atual
from app.models import Cobranca, Crianca, Presenca
from fastapi import status
from fastapi.responses import FileResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Table
from reportlab.lib.units import inch
from reportlab.platypus import Image
import os
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import Request
from datetime import date, datetime
import qrcode
from fastapi import Query
from fastapi.responses import RedirectResponse
import random
from datetime import datetime, timedelta
import crcmod
from datetime import datetime
from datetime import date
import calendar

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Dependência de banco
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/criancas", response_model=schemas.CriancaResponse)
def criar(
    crianca: schemas.CriancaCreate,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):
    return crud.criar_crianca(db, crianca, usuario.empresa_id)

@app.get("/criancas")
def listar_criancas(
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):

    criancas = db.query(models.Crianca)\
        .filter(models.Crianca.empresa_id == usuario.empresa_id)\
        .all()

    resultado = []

    for c in criancas:

        responsaveis = []

        for r in c.responsaveis:
            responsaveis.append({
                "nome": r.nome,
                "telefone": r.telefone,
                "cpf": r.cpf,
                "endereco": r.endereco
            })

        resultado.append({
            "id": c.id,
            "nome": c.nome,
            "data_nascimento": c.data_nascimento,
            "alergias": c.alergias,
            "observacoes": c.observacoes,
            "autorizacao_imagem": c.autorizacao_imagem,
            "dia_vencimento": c.dia_vencimento,
            "ativo": c.ativo,
            "tipo_cobranca": c.tipo_cobranca,
            "responsaveis": responsaveis
        })

    return resultado

@app.put("/criancas/{crianca_id}")
def atualizar_crianca(
    crianca_id: int,
    dados: schemas.CriancaCreate,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):
    crianca = crud.atualizar_crianca(
        db,
        crianca_id,
        usuario.empresa_id,
        dados
    )

    if not crianca:
        raise HTTPException(status_code=404, detail="Criança não encontrada")

    return crianca


@app.delete("/criancas/{crianca_id}")
def desativar_crianca(
    crianca_id: int,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):

    crianca = db.query(models.Crianca).filter(
        models.Crianca.id == crianca_id,
        models.Crianca.empresa_id == usuario.empresa_id
    ).first()

    if not crianca:
        raise HTTPException(status_code=404, detail="Criança não encontrada")

    crianca.ativo = False

    db.commit()

    return {"msg": "Criança desativada"}


@app.post("/usuarios")
def cadastrar_usuario(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    return crud.criar_usuario(db, usuario)

@app.post("/login", response_model=schemas.Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    usuario = crud.autenticar_usuario(
        db,
        form_data.username,
        form_data.password
    )

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas"
        )

    token = criar_token({
        "sub": str(usuario.id),
        "empresa_id": usuario.empresa_id
    })

    return {
        "access_token": token,
        "token_type": "bearer"
    }

@app.get("/recuperar-senha")
def recuperar_senha_page(request: Request):

    return templates.TemplateResponse(
        "recuperar_senha.html",
        {"request": request}
    )

@app.post("/recuperar-senha")
def recuperar_senha(
    dados: schemas.RecuperarSenha,
    db: Session = Depends(get_db)
):

    usuario = None

    if dados.email:
        usuario = db.query(models.Usuario)\
            .filter(models.Usuario.email == dados.email)\
            .first()

    if dados.telefone:
        usuario = db.query(models.Usuario)\
            .filter(models.Usuario.telefone == dados.telefone)\
            .first()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    codigo = str(random.randint(100000,999999))

    usuario.codigo_recuperacao = codigo
    usuario.codigo_expira = datetime.utcnow() + timedelta(minutes=10)

    db.commit()

    print("Código recuperação:", codigo)

    return {"msg":"Código enviado"}

@app.post("/nova-senha")
def nova_senha(
    dados: schemas.NovaSenha,
    db: Session = Depends(get_db)
):

    usuario = db.query(models.Usuario)\
        .filter(models.Usuario.codigo_recuperacao == dados.codigo)\
        .first()

    if not usuario:
        raise HTTPException(status_code=400, detail="Código inválido")

    if datetime.utcnow() > usuario.codigo_expira:
        raise HTTPException(status_code=400, detail="Código expirado")

    usuario.senha_hash = gerar_hash_senha(dados.nova_senha)

    usuario.codigo_recuperacao = None

    db.commit()

    return {"msg":"Senha alterada"}

@app.post("/checkin/{crianca_id}")
def checkin(
    crianca_id: int,
    dados: dict = {},
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):

    try:
        data_checkin = dados.get("checkin")

        # 🔵 CHECK-IN AUTOMÁTICO (COM VALIDAÇÃO)
        if not data_checkin:

            presenca = crud.fazer_checkin(
                db,
                crianca_id,
                usuario.empresa_id
            )

            if not presenca:
                raise HTTPException(
                    status_code=400,
                    detail="Criança já está presente ou já fez check-in hoje"
                )

            return presenca

        # 🟢 CHECK-IN MANUAL
        else:
            data_checkin = datetime.fromisoformat(data_checkin)

            presenca = crud.fazer_checkin_manual(
                db,
                crianca_id,
                usuario.empresa_id,
                data_checkin
            )

            if not presenca:
                raise HTTPException(
                    status_code=400,
                    detail="Já existe check-in aberto para essa criança"
                )

            return presenca

    except Exception as e:
        print("ERRO CHECKIN:", e)
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/checkout/{crianca_id}")
def checkout(
    crianca_id: int,
    dados: dict = {},
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):

    presenca_id = dados.get("presenca_id")
    data_checkout = dados.get("checkout")

    # 🔥 1. EDITAR PRESENÇA ESPECÍFICA
    if presenca_id:

        presenca = db.query(Presenca).filter(
            Presenca.id == presenca_id,
            Presenca.empresa_id == usuario.empresa_id
        ).first()

        if not presenca:
            raise HTTPException(status_code=404, detail="Presença não encontrada")

    # 🔥 2. CHECKOUT MANUAL SEM ID → PEGA ÚLTIMA PRESENÇA
    elif data_checkout and data_checkout != "null":

        presenca = db.query(Presenca).filter(
            Presenca.crianca_id == crianca_id,
            Presenca.empresa_id == usuario.empresa_id
        ).order_by(Presenca.checkin.desc()).first()

        if not presenca:
            raise HTTPException(status_code=404, detail="Nenhuma presença encontrada")

    # 🔥 3. CHECKOUT NORMAL
    else:

        presenca = db.query(Presenca)\
            .filter(
                Presenca.crianca_id == crianca_id,
                Presenca.empresa_id == usuario.empresa_id,
                Presenca.checkout == None
            )\
            .first()

        if not presenca:
            raise HTTPException(status_code=404, detail="Não está em check-in")

    # 🔥 APLICA CHECKOUT
    if data_checkout and data_checkout != "null":
        presenca.checkout = datetime.fromisoformat(data_checkout)
        db.commit()
        db.refresh(presenca)
    else:
        presenca = crud.fazer_checkout(db, presenca.id)

    # 🔥 BUSCA CRIANÇA
    crianca = db.query(Crianca).filter(
        Crianca.id == crianca_id,
        Crianca.empresa_id == usuario.empresa_id
    ).first()

    # 🔥 VERIFICA COBRANÇA EM ABERTO
    cobranca_aberta = db.query(Cobranca).filter(
        Cobranca.crianca_id == crianca_id,
        Cobranca.empresa_id == usuario.empresa_id,
        Cobranca.pago == False
    ).first()

    # 🔥 GARANTE VENCIMENTO
    if cobranca_aberta and not cobranca_aberta.data_vencimento:

        hoje = date.today()

        dia = crianca.dia_vencimento or 10
        ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]

        if dia > ultimo_dia:
            dia = ultimo_dia

        cobranca_aberta.data_vencimento = date(hoje.year, hoje.month, dia)

        db.commit()

    # 🔥 CRIA NOVA COBRANÇA SE NÃO EXISTIR
    if not cobranca_aberta:

        hoje = date.today()

        dia = crianca.dia_vencimento or 10
        ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]

        if dia > ultimo_dia:
            dia = ultimo_dia

        nova = Cobranca(
            crianca_id=crianca.id,
            empresa_id=crianca.empresa_id,
            valor=0,
            mes=hoje.strftime("%m/%Y"),
            pago=False,
            data_vencimento=date(hoje.year, hoje.month, dia)
        )

        db.add(nova)
        db.commit()

    return presenca

@app.post("/presenca-manual")
def criar_presenca_manual(
    dados: dict,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):

    crianca_id = dados.get("crianca_id")
    checkin = dados.get("checkin")
    checkout = dados.get("checkout")

    if not crianca_id or not checkin:
        raise HTTPException(status_code=400, detail="Dados incompletos")

    checkin = datetime.fromisoformat(checkin)

    if checkout:
        checkout = datetime.fromisoformat(checkout)

        if checkout < checkin:
            raise HTTPException(status_code=400, detail="Checkout menor que checkin")

    # 🔥 NOVO: EVITA DUPLICIDADE (MESMO DIA)
    inicio_dia = checkin.replace(hour=0, minute=0, second=0, microsecond=0)
    fim_dia = inicio_dia + timedelta(days=1)

    existe = db.query(Presenca).filter(
        Presenca.crianca_id == crianca_id,
        Presenca.empresa_id == usuario.empresa_id,
        Presenca.checkin >= inicio_dia,
        Presenca.checkin < fim_dia
    ).first()

    if existe:
        raise HTTPException(
            status_code=400,
            detail="Já existe presença registrada nesse dia"
        )

    nova = Presenca(
        crianca_id=crianca_id,
        empresa_id=usuario.empresa_id,
        checkin=checkin,
        checkout=checkout
    )

    db.add(nova)
    db.commit()
    db.refresh(nova)

    return nova

def adicionar_detalhe(cobranca, tipo, valor):

    detalhes = []

    if cobranca.detalhes:
        detalhes = json.loads(cobranca.detalhes)

    detalhes.append({
        "tipo": tipo,
        "valor": valor
    })

    cobranca.detalhes = json.dumps(detalhes)

@app.get("/presentes", response_model=list[schemas.PresencaResponse])
def presentes(
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):
    return crud.listar_presentes(db, usuario.empresa_id)

@app.get("/relatorio-hoje", response_model=list[schemas.PresencaResponse])
def relatorio(
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):
    return crud.relatorio_hoje(db, usuario.empresa_id)

@app.get("/resumo-hoje", response_model=schemas.ResumoDiario)
def resumo(
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):
    return crud.resumo_diario(db, usuario.empresa_id)

@app.get("/tempo-hoje", response_model=list[schemas.TempoHoje])
def tempo_hoje(
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):
    return crud.tempo_total_hoje(db, usuario.empresa_id)

@app.post("/mensalidades", response_model=schemas.MensalidadeResponse)
def criar_mensalidade(
    dados: schemas.MensalidadeCreate,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):
    return crud.criar_mensalidade(db, dados, usuario.empresa_id)


@app.get("/mensalidades", response_model=list[schemas.MensalidadeResponse])
def listar_mensalidades(
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):
    verificar_permissao_financeiro(usuario)
    return crud.listar_mensalidades(db, usuario.empresa_id)


@app.put("/mensalidades/{mensalidade_id}/pagar", response_model=schemas.MensalidadeResponse)
def pagar_mensalidade(
    mensalidade_id: int,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):
    mensalidade = crud.marcar_como_pago(db, mensalidade_id, usuario.empresa_id)

    if not mensalidade:
        raise HTTPException(status_code=404, detail="Mensalidade não encontrada")

    return mensalidade

@app.get("/enviar-cobrancas")
def enviar_cobrancas(db: Session = Depends(get_db)):

    lista = crud.gerar_cobrancas_whatsapp(db)

    return lista

@app.get("/rodar-tudo")
def rodar_tudo(db: Session = Depends(get_db)):

    crud.gerar_cobrancas_mensais(db)
    crud.verificar_inadimplencia(db)

    return {"msg": "ok"}

@app.get("/inadimplentes/{mes}", response_model=list[schemas.Inadimplente])
def inadimplentes(
    mes: str,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):
    verificar_permissao_financeiro(usuario)
    return crud.listar_inadimplentes(db, usuario.empresa_id, mes)

@app.get("/dashboard-financeiro")
def dashboard(
    mes: str = Query(...),
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):
    return crud.dashboard_financeiro(db, usuario.empresa_id, mes)

@app.get("/relatorio-financeiro-pdf/{mes}", response_class=FileResponse)
def gerar_pdf(
    mes: str,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):
    dados = crud.dashboard_financeiro(db, usuario.empresa_id, mes)

    file_path = f"relatorio_{mes}.pdf"
    doc = SimpleDocTemplate(file_path, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()

    elements.append(Paragraph(f"Relatório Financeiro - {mes}", styles["Title"]))
    elements.append(Spacer(1, 0.5 * inch))

    tabela_dados = [
        ["Total mensalidades", dados["total_mensalidades"]],
        ["Total recebido", f"R$ {dados['total_recebido']:.2f}"],
        ["Total pendente", f"R$ {dados['total_pendente']:.2f}"],
        ["Percentual pago", f"{dados['percentual_pago']} %"]
    ]

    tabela = Table(tabela_dados)
    elements.append(tabela)

    doc.build(elements)

    return FileResponse(file_path, media_type="application/pdf", filename=file_path)

@app.get("/login-page")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard-page")
def dashboard_page(request: Request):

    mes = date.today().strftime("%m/%Y")

    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "mes": mes}
    )

@app.get("/criancas-page")
def criancas_page(request: Request):
    return templates.TemplateResponse(
        "criancas.html",
        {"request": request}
)

@app.get("/cobrancas", response_model=list[schemas.CobrancaResponse])
def listar_cobrancas(
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):
    verificar_permissao_financeiro(usuario)
    return crud.listar_cobrancas(db, usuario.empresa_id)

@app.put("/cobrancas/{cobranca_id}/valor")
def atualizar_valor_cobranca(
    cobranca_id: int,
    dados: dict,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):

    cobranca = db.query(models.Cobranca)\
        .filter(
            models.Cobranca.id == cobranca_id,
            models.Cobranca.empresa_id == usuario.empresa_id
        )\
        .first()

    if not cobranca:
        raise HTTPException(status_code=404, detail="Cobrança não encontrada")

    # salva valor original se ainda não tiver
    if not cobranca.valor_original:
        cobranca.valor_original = cobranca.valor

    cobranca.valor = dados.get("valor")

    db.commit()

    return {"msg": "Valor atualizado"}

@app.put("/cobrancas/{cobranca_id}/pagar", response_model=schemas.CobrancaResponse)
def pagar_cobranca(
    cobranca_id: int,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):
    cobranca = db.query(Cobranca)\
        .filter(
            Cobranca.id == cobranca_id,
            Cobranca.empresa_id == usuario.empresa_id
        )\
        .first()

    if not cobranca:
        raise HTTPException(status_code=404, detail="Cobrança não encontrada")

    cobranca.pago = True
    cobranca.data_pagamento = datetime.now()

    db.commit()
    db.refresh(cobranca)

    return {
        "id": cobranca.id,
        "crianca_id": cobranca.crianca_id,
        "crianca_nome": cobranca.crianca.nome,  # 🔥 ESSENCIAL
        "valor": cobranca.valor,
        "pago": cobranca.pago,
        "data_pagamento": cobranca.data_pagamento,
        "data_vencimento": cobranca.data_vencimento,
        "telefone": cobranca.crianca.responsaveis[0].telefone if cobranca.crianca.responsaveis else ""
}

@app.put("/empresa/perfil")
def atualizar_perfil_empresa(
    dados: schemas.EmpresaPerfil,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):

    empresa = db.query(models.Empresa)\
        .filter(models.Empresa.id == usuario.empresa_id)\
        .first()

    empresa.nome = dados.nome
    empresa.email = dados.email
    empresa.cnpj = dados.cnpj
    empresa.telefone = dados.telefone
    empresa.endereco = dados.endereco
    empresa.responsavel = dados.responsavel

    db.commit()

    return {"msg": "Perfil atualizado"}

@app.put("/empresa/asaas-key")
def salvar_asaas_key(
    api_key: str,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):
    empresa = db.query(models.Empresa)\
        .filter(models.Empresa.id == usuario.empresa_id)\
        .first()

    empresa.asaas_api_key = api_key
    db.commit()

    return {"message": "API Key salva com sucesso"}

@app.get("/cobrancas/{cobranca_id}/comprovante")
def gerar_comprovante(
    cobranca_id: int,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):

    cobranca = db.query(models.Cobranca)\
        .filter(models.Cobranca.id == cobranca_id)\
        .first()

    if not cobranca:
        raise HTTPException(status_code=404, detail="Cobrança não encontrada")

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()

    conteudo = []

    # 🔥 DADOS DA EMPRESA
    empresa = db.query(models.Empresa).filter(models.Empresa.id == cobranca.empresa_id).first()

    nome_empresa = empresa.nome if empresa else "Empresa"
    cnpj = empresa.cnpj if empresa else ""
    endereco = empresa.endereco if empresa else ""
    telefone_empresa = empresa.telefone if empresa else ""

    conteudo.append(Paragraph(f"<b>{nome_empresa}</b>", styles["Title"]))
    conteudo.append(Spacer(1, 10))

    if cnpj:
        conteudo.append(Paragraph(f"CNPJ: {cnpj}", styles["Normal"]))

    if endereco:
        conteudo.append(Paragraph(f"Endereço: {endereco}", styles["Normal"]))

    if telefone_empresa:
        conteudo.append(Paragraph(f"Telefone: {telefone_empresa}", styles["Normal"]))

        # 🔥 TÍTULO
        conteudo.append(Paragraph("<b>Comprovante de Pagamento</b>", styles["Heading2"]))
        conteudo.append(Spacer(1, 20))

    # 🔥 DADOS DA COBRANÇA
    nome = cobranca.crianca.nome
    valor = f"R$ {cobranca.valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    data = cobranca.data_pagamento.strftime("%d/%m/%Y às %H:%M") if cobranca.data_pagamento else "-"
    status = "Pago" if cobranca.pago else "Pendente"

    conteudo.append(Paragraph(f"Criança: {nome}", styles["Normal"]))
    conteudo.append(Paragraph(f"Valor: {valor}", styles["Normal"]))
    conteudo.append(Paragraph(f"Data: {data}", styles["Normal"]))
    conteudo.append(Paragraph(f"Status: {status}", styles["Normal"]))

    conteudo.append(Spacer(1, 30))

    conteudo.append(Paragraph("Obrigado pela preferência!", styles["Normal"]))

    doc.build(conteudo)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=comprovante.pdf"}
    )

@app.get("/cobrancas/{cobranca_id}/boleto-pdf", response_class=FileResponse)
def gerar_boleto_pdf(
    cobranca_id: int,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):

    empresa = db.query(models.Empresa)\
        .filter(models.Empresa.id == usuario.empresa_id)\
        .first()

    cobranca = db.query(models.Cobranca)\
        .filter(
            models.Cobranca.id == cobranca_id,
            models.Cobranca.empresa_id == usuario.empresa_id
        )\
        .first()

    if not cobranca:
        raise HTTPException(status_code=404, detail="Cobrança não encontrada")

    crianca = db.query(models.Crianca)\
        .filter(models.Crianca.id == cobranca.crianca_id)\
        .first()

    file_path = f"comprovante_{cobranca.id}.pdf"

    doc = SimpleDocTemplate(file_path, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("COMPROVANTE DE PAGAMENTO", styles["Title"]))
    elements.append(Spacer(1, 20))

    dados = [
        ["Criança:", crianca.nome],
        ["Valor:", f"R$ {cobranca.valor:.2f}"],
        ["Status:", "PAGO" if cobranca.pago else "PENDENTE"],
        ["Data:", datetime.utcnow().strftime("%d/%m/%Y")],
        ["Vencimento:", datetime.utcnow().date().isoformat()],
        ["Empresa:", empresa.nome],
        ["Banco:", empresa.banco_nome],
        ["Agência:", empresa.banco_agencia],
        ["Conta:", empresa.banco_conta],
    ]

    tabela = Table(dados, colWidths=[120, 300])
    elements.append(tabela)

    doc.build(elements)

    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=file_path
    )

def gerar_payload_pix(chave, valor, nome, cidade):

    nome = nome[:25]
    cidade = cidade[:15]

    payload = (
        "000201"
        "010211"
        "26"
        f"{len(f'0014BR.GOV.BCB.PIX01{len(chave):02}{chave}'):02}"
        "0014BR.GOV.BCB.PIX"
        f"01{len(chave):02}{chave}"
        "52040000"
        "5303986"
        f"54{len(f'{valor:.2f}'):02}{valor:.2f}"
        "5802BR"
        f"59{len(nome):02}{nome}"
        f"60{len(cidade):02}{cidade}"
        "62070503***"
        "6304"
    )

    import crcmod

    crc16 = crcmod.predefined.mkPredefinedCrcFun('crc-ccitt-false')
    crc = crc16(payload.encode("utf-8"))
    crc_hex = hex(crc)[2:].upper().zfill(4)

    return payload + crc_hex

@app.get("/cobrancas/{cobranca_id}/pix-dados")
def gerar_pix_dados(
    cobranca_id: int,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):

    cobranca = db.query(models.Cobranca)\
        .filter(
            models.Cobranca.id == cobranca_id,
            models.Cobranca.empresa_id == usuario.empresa_id
        )\
        .first()

    if not cobranca:
        raise HTTPException(status_code=404, detail="Cobrança não encontrada")

    empresa = db.query(models.Empresa)\
        .filter(models.Empresa.id == usuario.empresa_id)\
        .first()

    payload_pix = gerar_payload_pix(
        empresa.pix_chave,
        cobranca.valor,
        empresa.nome,
        "ITAU DE MINAS"
    )

    return {
        "pix": payload_pix,
        "valor": cobranca.valor,
        "nome": cobranca.crianca.nome,
        "telefone": cobranca.crianca.responsaveis[0].telefone if cobranca.crianca.responsaveis else ""
    }

@app.get("/cobrancas/{cobranca_id}/pix")
def gerar_qrcode_pix(
    cobranca_id: int,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):
    cobranca = db.query(models.Cobranca)\
        .filter(
            models.Cobranca.id == cobranca_id,
            models.Cobranca.empresa_id == usuario.empresa_id
        )\
        .first()

    if not cobranca:
        raise HTTPException(status_code=404, detail="Cobrança não encontrada")

    empresa = db.query(models.Empresa)\
        .filter(models.Empresa.id == usuario.empresa_id)\
        .first()

    payload_pix = gerar_payload_pix(
        empresa.pix_chave,
        cobranca.valor,
        empresa.nome,
        "ITAU DE MINAS"
    )

    # 🔥 GERA QR CODE
    img = qrcode.make(payload_pix)

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return StreamingResponse(buffer, media_type="image/png")

@app.put("/empresa/configuracao-financeira")
def configurar_financeiro(
    dados: schemas.ConfiguracaoFinanceira,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):
    empresa = db.query(models.Empresa)\
        .filter(models.Empresa.id == usuario.empresa_id)\
        .first()

    empresa.valor_hora = dados.valor_hora
    empresa.valor_diaria = dados.valor_diaria
    empresa.valor_mensal = dados.valor_mensal
    empresa.tipo_cobranca = dados.tipo_cobranca
    empresa.valor_semanal = dados.valor_semanal
    empresa.valor_meio_periodo = dados.valor_meio_periodo
    db.commit()

    return {"message": "Configuração salva com sucesso"}

def verificar_permissao_financeiro(usuario):
    if usuario.role not in ["admin", "financeiro"]:
        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para acessar o módulo financeiro"
        )

@app.put("/usuarios/{usuario_id}/role")
def alterar_role_usuario(
    usuario_id: int,
    nova_role: str,
    db: Session = Depends(get_db),
    usuario_logado = Depends(get_usuario_atual)
):
    # 🔐 Só admin pode alterar permissões
    if usuario_logado.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Apenas administrador pode alterar permissões"
        )

    usuario = db.query(models.Usuario)\
        .filter(
            models.Usuario.id == usuario_id,
            models.Usuario.empresa_id == usuario_logado.empresa_id
        )\
        .first()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if nova_role not in ["admin", "financeiro", "atendente"]:
        raise HTTPException(status_code=400, detail="Role inválida")

    usuario.role = nova_role
    db.commit()
    db.refresh(usuario)

    return {"message": "Permissão atualizada com sucesso"}

@app.get("/usuarios", response_model=list[schemas.UsuarioCreate])
def listar_usuarios(
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):
    if usuario.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Apenas administrador pode visualizar usuários"
        )

    return db.query(models.Usuario)\
        .filter(models.Usuario.empresa_id == usuario.empresa_id)\
        .all()

@app.get("/financeiro-page")
def financeiro_page(request: Request):
    return templates.TemplateResponse(
        "financeiro.html",
        {"request": request}
    )

@app.get("/")
def home():
    return RedirectResponse("/login-page")


@app.get("/configuracoes-page")
def configuracoes_page(request: Request):

    return templates.TemplateResponse(
        "configuracoes.html",
        {"request": request}
    )




@app.put("/configuracoes")
def atualizar_configuracoes(
    dados: schemas.ConfigEmpresa,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):

    empresa = db.query(models.Empresa)\
        .filter(models.Empresa.id == usuario.empresa_id)\
        .first()

    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    # PERFIL
    if dados.nome is not None:
        empresa.nome = dados.nome

    if dados.responsavel is not None:
        empresa.responsavel = dados.responsavel

    if dados.cnpj is not None:
        empresa.cnpj = dados.cnpj

    if dados.telefone is not None:
        empresa.telefone = dados.telefone

    if dados.email is not None:
        empresa.email = dados.email

    if dados.endereco is not None:
        empresa.endereco = dados.endereco

    # FINANCEIRO (só atualiza se vier)
    if dados.valor_hora is not None:
        empresa.valor_hora = dados.valor_hora

    if dados.valor_diaria is not None:
        empresa.valor_diaria = dados.valor_diaria

    if dados.valor_semanal_integral is not None:
        empresa.valor_semanal_integral = dados.valor_semanal_integral

    if dados.valor_semanal_meio is not None:
        empresa.valor_semanal_meio = dados.valor_semanal_meio

    if dados.valor_mensal_integral is not None:
        empresa.valor_mensal_integral = dados.valor_mensal_integral

    if dados.valor_mensal_meio is not None:
        empresa.valor_mensal_meio = dados.valor_mensal_meio

    if dados.valor_sabado is not None:
        empresa.valor_sabado = dados.valor_sabado

    if dados.tipo_cobranca is not None:
        empresa.tipo_cobranca = dados.tipo_cobranca

    if dados.pix_chave is not None :
        empresa.pix_chave = dados.pix_chave

    if dados.banco_nome is not None:
        empresa.banco_nome = dados.banco_nome

    if dados.banco_agencia is not None:
        empresa.banco_agencia = dados.banco_agencia

    if dados.banco_conta is not None:
        empresa.banco_conta = dados.banco_conta

    if dados.asaas_api_key is not None:
        empresa.asaas_api_key = dados.asaas_api_key

    db.commit()

    return {"msg": "Configurações salvas com sucesso"}


@app.get("/configuracoes")
def obter_configuracoes(
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):
    empresa = db.query(models.Empresa)\
        .filter(models.Empresa.id == usuario.empresa_id)\
        .first()

    return {
        "nome": empresa.nome,
        "responsavel": empresa.responsavel,
        "cnpj": empresa.cnpj,
        "telefone": empresa.telefone,
        "email": empresa.email,
        "endereco": empresa.endereco,

        "valor_hora": empresa.valor_hora,
        "valor_diaria": empresa.valor_diaria,
        "valor_semanal_integral": empresa.valor_semanal_integral,
        "valor_semanal_meio": empresa.valor_semanal_meio,
        "valor_mensal_integral": empresa.valor_mensal_integral,
        "valor_mensal_meio": empresa.valor_mensal_meio,
        "valor_sabado": empresa.valor_sabado,
        "tipo_cobranca": empresa.tipo_cobranca,

        "pix_chave": empresa.pix_chave,
        "banco_nome": empresa.banco_nome,
        "banco_agencia": empresa.banco_agencia,
        "banco_conta": empresa.banco_conta
    }

@app.get("/configuracoes-seguranca")
def configuracoes_seguranca(request: Request):

    return templates.TemplateResponse(
        "configuracoes_seguranca.html",
        {"request": request}
    )


@app.get("/configuracoes-financeiro")
def configuracoes_financeiro(request: Request):

    return templates.TemplateResponse(
        "configuracoes_financeiro.html",
        {"request": request}
    )


@app.put("/usuario/senha")
def alterar_senha(
    dados: dict,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):

    if not verificar_senha(dados["senha_atual"], usuario.senha_hash):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")

    usuario.senha_hash = gerar_hash_senha(dados["nova_senha"])

    db.commit()

    return {"msg": "Senha alterada"}

@app.post("/webhook/asaas")
async def webhook_asaas(
    request: Request,
    db: Session = Depends(get_db)
):
    data = await request.json()

    evento = data.get("event")
    pagamento = data.get("payment")

    if not pagamento:
        return {"msg": "Evento ignorado"}

    gateway_id = pagamento.get("id")

    cobranca = db.query(models.Cobranca)\
        .filter(models.Cobranca.gateway_id == gateway_id)\
        .first()

    if not cobranca:
        return {"msg": "Cobrança não encontrada"}

    if evento in ["PAYMENT_CONFIRMED", "PAYMENT_RECEIVED"]:

        cobranca.pago = True
        cobranca.metodo_pagamento = pagamento.get("billingType")

        data_pagamento = pagamento.get("paymentDate")

        if data_pagamento:
            cobranca.data_pagamento = datetime.strptime(data_pagamento, "%Y-%m-%d")
        else:
            cobranca.data_pagamento = datetime.now()

        db.commit()

    return {"msg": "ok"}

@app.get("/cadastro-criancas")
def cadastro_criancas_page(request: Request):
    return templates.TemplateResponse(
        "cadastro_criancas.html",
        {"request": request}
    )

@app.get("/api/cadastro-crianca")
def listar_cadastro_crianca(
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):

    criancas = db.query(models.Crianca)\
        .filter(models.Crianca.empresa_id == usuario.empresa_id)\
        .all()

    resultado = []

    for c in criancas:

        idade = date.today().year - c.data_nascimento.year

        mensalidade_atrasada = db.query(models.Mensalidade)\
            .filter(
                models.Mensalidade.crianca_id == c.id,
                models.Mensalidade.pago == False
            )\
            .first()

        resultado.append({
            "id": c.id,
            "nome": c.nome,
            "idade": idade,
            "alergias": c.alergias,
            "observacoes": c.observacoes,
            "nome_mae": c.nome_mae,
            "telefone": c.telefone,
            "contato_emergencia": c.contato_emergencia,
            "autorizacao_imagem": c.autorizacao_imagem,
            "financeiro": "Em dia" if not mensalidade_atrasada else "Atrasado"
        })

    return resultado

@app.get("/ficha-crianca/{crianca_id}", response_class=HTMLResponse)
def pagina_ficha_crianca(
    request: Request,
    crianca_id: int
):
    return templates.TemplateResponse(
        "ficha_crianca.html",
        {"request": request, "crianca_id": crianca_id}
    )


@app.get("/api/ficha-crianca/{crianca_id}")
def dados_ficha_crianca(
    crianca_id: int,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):

    crianca = db.query(models.Crianca)\
        .filter(
            models.Crianca.id == crianca_id,
            models.Crianca.empresa_id == usuario.empresa_id
        )\
        .first()

    if not crianca:
        raise HTTPException(status_code=404, detail="Criança não encontrada")

    presencas = db.query(models.Presenca)\
        .filter(models.Presenca.crianca_id == crianca_id)\
        .order_by(models.Presenca.checkin.desc())\
        .limit(20)\
        .all()

    cobrancas = db.query(models.Cobranca)\
        .filter(models.Cobranca.crianca_id == crianca_id)\
        .order_by(models.Cobranca.id.desc())\
        .limit(20)\
        .all()

    return {

    "crianca": {
        "id": crianca.id,
        "nome": crianca.nome,
        "alergias": crianca.alergias,
        "observacoes": crianca.observacoes,
        "autorizacao_imagem": crianca.autorizacao_imagem,
        "responsaveis": [
            {
                "nome": r.nome,
                "telefone": r.telefone
            }
            for r in crianca.responsaveis
        ]
    },

    "presencas": presencas,
    "cobrancas": cobrancas

    }
@app.put("/reativar-crianca/{crianca_id}")
def reativar_crianca(
    crianca_id: int,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):

    crianca = db.query(models.Crianca).filter(
        models.Crianca.id == crianca_id,
        models.Crianca.empresa_id == usuario.empresa_id
    ).first()

    if not crianca:
        raise HTTPException(status_code=404, detail="Criança não encontrada")

    crianca.ativo = True

    db.commit()

    return {"msg": "Criança reativada"}

@app.put("/alterar-email")
def alterar_email(
    dados: dict,
    db: Session = Depends(get_db),
    usuario_token = Depends(get_usuario_atual)
):
    novo_email = dados.get("email")

    if not novo_email:
        raise HTTPException(status_code=400, detail="Email inválido")

    # 🔥 BUSCA DE NOVO NO BANCO
    usuario = db.query(models.Usuario)\
        .filter(models.Usuario.id == usuario_token.id)\
        .first()

    usuario.email = novo_email

    db.commit()
    db.refresh(usuario)  # 🔥 IMPORTANTE

    return {"msg": "Email atualizado com sucesso"}

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@app.put("/alterar-senha")
def alterar_senha(
    dados: dict,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):
    senha_atual = dados.get("senha_atual")
    nova_senha = dados.get("nova_senha")

    if not senha_atual or not nova_senha:
        raise HTTPException(status_code=400, detail="Dados inválidos")

    # verifica senha atual
    if not pwd_context.verify(senha_atual, usuario.senha):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")

    # atualiza senha
    usuario.senha = pwd_context.hash(nova_senha)
    db.commit()

    return {"msg": "Senha atualizada com sucesso"}

@app.get("/cobrancas/{id}/asaas")
def gerar_link_pagamento(
    id: int,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):

    cobranca = db.query(models.Cobranca)\
        .filter(
            models.Cobranca.id == id,
            models.Cobranca.empresa_id == usuario.empresa_id
        )\
        .first()

    if not cobranca:
        raise HTTPException(status_code=404, detail="Cobrança não encontrada")

    empresa = db.query(models.Empresa)\
        .filter(models.Empresa.id == usuario.empresa_id)\
        .first()

    crianca = db.query(models.Crianca)\
        .filter(models.Crianca.id == cobranca.crianca_id)\
        .first()

    pagamento = crud.gerar_pagamento_asaas(
        db,
        cobranca,
        empresa,
        crianca
    )

    return RedirectResponse(pagamento.get("invoiceUrl"))

@app.get("/cobrancas/{id}/mensagem")
def gerar_mensagem_cobranca(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):

    cobranca = db.query(models.Cobranca)\
        .filter(models.Cobranca.id == id)\
        .first()

    crianca = db.query(models.Crianca)\
        .filter(models.Crianca.id == cobranca.crianca_id)\
        .first()

    responsavel = crianca.responsaveis[0] if crianca.responsaveis else None

    base_url = str(request.base_url).rstrip("/")
    mensagem = f"""
    Olá! 

    Cobrança do Hotelzinho:

    {crianca.nome}
    R$ {cobranca.valor:.2f}

    Escolha como pagar:

    PIX:
    {base_url}/cobrancas/{id}/pix

    Cartão:
    {base_url}/cobrancas/{id}/asaas
    """

    return {
        "telefone": responsavel.telefone if responsavel else "",
        "mensagem": mensagem
    }

from datetime import datetime

@app.get("/historico-crianca/{crianca_id}")
def historico_crianca(
    crianca_id: int,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):

    # 🔥 AGORA TRAZ TODAS (PAGAS E PENDENTES)
    cobrancas = db.query(models.Cobranca)\
        .filter(
            models.Cobranca.crianca_id == crianca_id
        )\
        .all()

    presencas = db.query(models.Presenca)\
        .filter(models.Presenca.crianca_id == crianca_id)\
        .all()

    resultado = {}

    # 🔥 COBRANÇAS (PAGAS E PENDENTES)
    for c in cobrancas:

        # 🔥 define data base
        data_base = c.data_pagamento if c.data_pagamento else c.data_vencimento

        if not data_base:
            continue

        mes = data_base.strftime("%m/%Y")

        if mes not in resultado:
            resultado[mes] = {
                "total": 0,
                "pagamentos": [],
                "presencas": []
            }

        resultado[mes]["total"] += c.valor or 0

        resultado[mes]["pagamentos"].append({
            "id": c.id,
            "valor": c.valor,
            "data": data_base,
            "pago": c.pago,
            "detalhes": json.loads(c.detalhes) if c.detalhes else []
        })

    # 🔥 PRESENÇAS
    for p in presencas:

        if not p.checkin:
            continue

        mes = p.checkin.strftime("%m/%Y")

        if mes not in resultado:
            resultado[mes] = {
                "total": 0,
                "pagamentos": [],
                "presencas": []
            }

        horas = 0

        if p.checkout:
            horas = (p.checkout - p.checkin).total_seconds() / 3600

            if horas < 0:
                horas = 0

        resultado[mes]["presencas"].append({
            "data": p.checkin,
            "horas": round(horas, 2)
        })

    return resultado

def calcular_valor(c, empresa, checkin, checkout):

    tempo = checkout - checkin
    horas = tempo.total_seconds() / 3600
    dia_semana = checkin.weekday()

    # 🟥 SÁBADO
    if dia_semana == 5:
        return empresa.valor_sabado or 0

    # 📦 TIPO DE COBRANÇA DA CRIANÇA
    tipo = c.tipo_cobranca  # hora / semanal / mensal
    periodo = getattr(c, "periodo", "integral")

    # ⏱ HORA
    if tipo == "hora":
        return (empresa.valor_hora or 0) * horas

    # 📅 SEMANAL
    if tipo == "semanal":
        if periodo == "meio":
            return empresa.valor_semanal_meio or 0
        return empresa.valor_semanal_integral or 0

    # 📆 MENSAL
    if tipo == "mensal":
        if periodo == "meio":
            return empresa.valor_mensal_meio or 0
        return empresa.valor_mensal_integral or 0

    # fallback
    return empresa.valor_diaria or 0

@app.put("/presencas/{presenca_id}")
def editar_presenca(
    presenca_id: int,
    dados: dict,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):
    presenca = db.query(Presenca)\
        .filter(
            Presenca.id == presenca_id,
            Presenca.empresa_id == usuario.empresa_id
        ).first()

    if not presenca:
        raise HTTPException(status_code=404, detail="Presença não encontrada")

    # 🔥 atualiza datas
    if "checkin" in dados:
        presenca.checkin = dados["checkin"]

    if "checkout" in dados:
        presenca.checkout = dados["checkout"]

    db.commit()
    db.refresh(presenca)

    return presenca

@app.post("/gastos")
def criar_gasto(
    dados: dict,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):

    gasto = models.Gasto(
        descricao=dados["descricao"],
        valor=dados["valor"],
        empresa_id=usuario.empresa_id,
        mes=dados["mes"]
    )

    db.add(gasto)
    db.commit()

    return gasto



@app.get("/gastos")
def listar_gastos(
    mes: str = Query(...),  # 🔥 ISSO AQUI RESOLVE
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual)
):
    return crud.listar_gastos(db, usuario.empresa_id, mes)

@app.get("/receita-mes-page")
def receita_mes_page(request: Request):
    return templates.TemplateResponse(
        "receita_mes.html",
        {"request": request}
    )

@app.put("/gastos/{id}")
def editar_gasto(id: int, dados: dict, db: Session = Depends(get_db), usuario=Depends(get_usuario_atual)):

    gasto = db.query(models.Gasto)\
        .filter(
            models.Gasto.id == id,
            models.Gasto.empresa_id == usuario.empresa_id
        )\
        .first()

    if not gasto:
        raise HTTPException(status_code=404)

    gasto.descricao = dados["descricao"]
    gasto.valor = dados["valor"]

    db.commit()

    return gasto


@app.delete("/gastos/{id}")
def deletar_gasto(id: int, db: Session = Depends(get_db), usuario=Depends(get_usuario_atual)):

    gasto = db.query(models.Gasto)\
        .filter(
            models.Gasto.id == id,
            models.Gasto.empresa_id == usuario.empresa_id
        )\
        .first()

    if not gasto:
        raise HTTPException(status_code=404)

    db.delete(gasto)
    db.commit()

    return {"ok": True}

@app.get("/calendario-page")
def calendario_page(request: Request):
    return templates.TemplateResponse(
        "calendario.html",
        {"request": request}
    )

