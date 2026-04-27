const token = localStorage.getItem("token")

function formatarMoeda(valor){
    return Number(valor).toLocaleString("pt-BR", {
        style: "currency",
        currency: "BRL"
    })
}

function getMesAtual(){
    const hoje = new Date()
    return String(hoje.getMonth()+1).padStart(2,"0") + "/" + hoje.getFullYear()
}

async function carregarResumo(){

    const mes = getMesAtual()

    const res = await fetch(`/dashboard-financeiro?mes=${mes}`,{
        headers:{ Authorization:"Bearer "+token }
    })

    const d = await res.json()

    const faturamento = d.total_recebido || 0

    document.getElementById("faturamento").innerText = formatarMoeda(faturamento)

    const resG = await fetch(`/gastos?mes=${mes}`,{
        headers:{ Authorization:"Bearer "+token }
    })

    const g = await resG.json()

    const totalGastos = g.total || 0

    document.getElementById("gastos").innerText = formatarMoeda(totalGastos)

    const lucro = faturamento - totalGastos

    document.getElementById("lucro").innerText = formatarMoeda(lucro)
}

function fecharFinanceiro(){
    document.getElementById("modalFinanceiro").style.display = "none"
}

async function abrirHistoricoFinanceiro(tipo){

    const lista = document.getElementById("listaFinanceiro")
    const titulo = document.getElementById("tituloFinanceiro")
    const btn = document.getElementById("btnAdicionar")

    lista.innerHTML = ""

    if(tipo === "faturamento"){
        titulo.innerText = "💰 Faturamento"
        btn.innerText = "+ Adicionar Faturamento"
        btn.onclick = abrirModalFaturamento
    }

    if(tipo === "gastos"){
        titulo.innerText = "💸 Gastos"
        btn.innerText = "+ Adicionar Gasto"
        btn.onclick = abrirModalGasto
    }

    const res = await fetch(`/${tipo}-mes`, {
        headers:{
            "Authorization":"Bearer "+token
        }
    })

    const dados = await res.json()

    if(!Array.isArray(dados)){
        console.error("Erro:", dados)
        return
    }

    dados.forEach(item=>{

        const div = document.createElement("div")
        div.className = "item-financeiro"

        div.innerHTML = `
            <span>${item.descricao}</span>

            <div class="acoes-item">
                <strong>R$ ${item.valor}</strong>

                <button onclick="excluirItem(${item.id}, '${tipo}')">Excluir</button>
            </div>
        `

        lista.appendChild(div)
    })

    document.getElementById("modalFinanceiro").style.display = "flex"
}

async function salvarFaturamento(){

    const descricao = document.getElementById("descricaoFaturamento").value
    const valor = document.getElementById("valorFaturamento").value

    const res = await fetch("/faturamento", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token
        },
        body: JSON.stringify({ descricao, valor })
    })

    if (!res.ok){
        alert("Erro ao salvar faturamento")
        return
    }

    fecharModalFaturamento()
    carregarResumo()
}

async function salvarGasto(){

    const descricao = document.getElementById("descricaoGasto").value
    const valor = document.getElementById("valorGasto").value

    const res = await fetch("/gastos", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token
        },
        body: JSON.stringify({ descricao, valor })
    })

    if (!res.ok){
        alert("Erro ao salvar gasto")
        return
    }

    fecharModalGasto()
    carregarResumo()
}

function abrirModalFaturamento(){
    document.getElementById("modalFaturamento").style.display = "flex"
}

function fecharModalFaturamento(){
    document.getElementById("modalFaturamento").style.display = "none"
}

function abrirModalGasto(){
    document.getElementById("modalGasto").style.display = "flex"
}

function fecharModalGasto(){
    document.getElementById("modalGasto").style.display = "none"
}

async function excluirItem(id, tipo){

    if(!confirm("Excluir?")) return

    await fetch(`/${tipo}/${id}`,{
        method:"DELETE",
        headers:{
            "Authorization":"Bearer "+token
        }
    })

    abrirHistoricoFinanceiro(tipo)
    carregarResumo()
}

carregarResumo()