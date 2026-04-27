const token = localStorage.getItem("token")

if (!token){
    window.location.href="/login-page"
}

if (!localStorage.getItem("token")){
    window.location.href="/login-page"
}

function formatarDataHora(data){

    const d = new Date(data)
    const hoje = new Date()
    const ontem = new Date()

    ontem.setDate(hoje.getDate() - 1)

    const mesmaData = (d1, d2) =>
        d1.getDate() === d2.getDate() &&
        d1.getMonth() === d2.getMonth() &&
        d1.getFullYear() === d2.getFullYear()

    let textoData = ""

    if (mesmaData(d, hoje)) {
        textoData = "Hoje"
    } 
    else if (mesmaData(d, ontem)) {
        textoData = "Ontem"
    } 
    else {
        textoData = d.toLocaleDateString("pt-BR")
    }

    const hora = d.toLocaleTimeString("pt-BR", {
        hour: "2-digit",
        minute: "2-digit"
    })

    return `${textoData} • ${hora}`
}

function carregarCobrancas(){

fetch("/cobrancas",{
headers:{
"Authorization":"Bearer "+token
}
})

.then(res=>{
if(!res.ok){
throw new Error("Erro ao carregar cobranças")
}
return res.json()
})

.then(dados=>{

const tbody = document.querySelector("#tabelaCobrancas tbody")

tbody.innerHTML=""

if(!Array.isArray(dados)){
console.error("Resposta inválida:", dados)
return
}

dados.forEach(c=>{

let status = ""
let dataPagamento = "-"

if (c.pago) {
    status = "Pago"

    if (c.data_pagamento) {
        dataPagamento = formatarDataHora(c.data_pagamento)
    }
} else {
    status = "Pendente"
}
let vencimento = "-"

if (c.data_vencimento) {
    const partes = c.data_vencimento.split("-")
    vencimento = `${partes[2]}/${partes[1]}/${partes[0]}`
}

const linha = `
<tr>

<td 
onclick="verHistorico(${c.crianca_id}, \`${c.crianca_nome}\`)">
    ${c.crianca_nome}
</td>

<td>
    <input 
        type="text" 
        value="${formatarMoeda(c.valor)}"
        id="valor-${c.id}"
        ${c.pago ? "disabled" : ""}
        ${!c.pago ? `onblur="salvarValorFormatado(${c.id})"` : ""}
    >
</td>

<td>${status}</td>

<td>${dataPagamento}</td>
<td>${vencimento}</td>

<td>
${!c.pago ? `

<button onclick="desconto(${c.id})">Desconto</button>
<button onclick="pagar(${c.id})">Marcar Pago</button>
<button onclick="pix(${c.id})">⚡ PIX</button>

` : `

<span style="color:green">✔ Pago</span>

<button onclick="abrirComprovante(${c.id})">📄</button>

<button onclick="enviarComprovanteWhats(${c.id}, \`${c.telefone || ''}\`)">
📲 WhatsApp
</button>

`}

</td>

</tr>
`

tbody.innerHTML += linha

})

})

.catch(err=>{
console.error("Erro financeiro:",err)
})

}

function abrirComprovante(id){

    fetch(`/cobrancas/${id}/comprovante`,{
        headers:{
            "Authorization":"Bearer "+token
        }
    })
    .then(res=>res.blob())
    .then(blob=>{

        const url = window.URL.createObjectURL(blob)

        window.open(url) // 👁 só visualiza
    })
}

function baixarComprovante(id){

    fetch(`/cobrancas/${id}/comprovante`,{
        headers:{
            "Authorization":"Bearer "+token
        }
    })
    .then(res=>res.blob())
    .then(blob=>{

        const url = window.URL.createObjectURL(blob)

        const a = document.createElement("a")
        a.href = url
        a.download = "comprovante.pdf"
        a.click()
    })
}

function enviarComprovanteWhats(id, telefone){

    if(!telefone){
        alert("Telefone não encontrado")
        return
    }

    const mensagem = "Segue seu comprovante de pagamento 😊"

    const tel = telefone.replace(/\D/g,"")

    const url = `https://wa.me/55${tel}?text=${encodeURIComponent(mensagem)}`

    window.open(url)

    // 📄 baixa junto
    baixarComprovante(id)
}

function formatarMoeda(valor){
    return Number(valor).toLocaleString("pt-BR", {
        style: "currency",
        currency: "BRL"
    })
}

function salvarValorFormatado(id){

    let input = document.getElementById(`valor-${id}`).value

    // remove R$, pontos e troca vírgula por ponto
    let valorLimpo = input
        .replace("R$", "")
        .replace(/\./g, "")
        .replace(",", ".")
        .trim()

    fetch(`/cobrancas/${id}/valor`,{
        method:"PUT",
        headers:{
            "Content-Type":"application/json",
            "Authorization":"Bearer "+token
        },
        body: JSON.stringify({
            valor: parseFloat(valorLimpo)
        })
    })
    .then(res=>res.json())
    .then(()=>{
        carregarCobrancas()
    })
}

function pagar(id){

fetch(`/cobrancas/${id}/pagar`,{

method:"PUT",

headers:{
"Authorization":"Bearer "+token
}

})

.then(async res=>{
    if(!res.ok){
        const erro = await res.text()
        console.error("Erro backend:", erro)
        throw new Error("Erro ao marcar como pago")
    }
    return res.json()
})

.then(()=>{
carregarCobrancas()
})

.catch(err=>{
alert(err.message)
})

}

async function pix(id){

    const res = await fetch(`/cobrancas/${id}/pix-dados`,{
        headers:{
            "Authorization":"Bearer "+token
        }
    })

    if(!res.ok){
        alert("Erro ao gerar PIX")
        return
    }

    const data = await res.json()

    const pix = data.pix
    const valor = data.valor
    const nome = data.nome
    const telefone = data.telefone

    // 🔥 MOSTRA NA TELA (isso que faltava)
    document.getElementById("pixCode").value = pix
    document.getElementById("valor").innerText = 
        "R$ " + Number(valor).toLocaleString("pt-BR",{style:"currency",currency:"BRL"})

    // 🔥 copia automático
    navigator.clipboard.writeText(pix)

    alert("PIX copiado! Agora é só colar 👍")

    // 🔥 QR CODE
    fetch(`/cobrancas/${id}/pix`,{
        headers:{
            "Authorization":"Bearer "+token
        }
    })
    .then(res=>res.blob())
    .then(blob=>{
        const url = window.URL.createObjectURL(blob)
        document.getElementById("qrCode").src = url
    })

    // 🔥 salva pra WhatsApp
    window.telefonePix = telefone
    window.nomePix = nome
}

async function verHistorico(id, nome){

    document.getElementById("tituloHistorico").innerText = `Histórico de ${nome}`

    const res = await fetch(`/historico-crianca/${id}`,{
        headers:{
            "Authorization":"Bearer "+token
        }
    })

    const dados = await res.json()

    let html = ""

    for(let mes in dados){

        html += `
        <div class="bloco-mes" onclick="toggleMes(this)">
            
            <div class="linha-topo">
                <span style="cursor:pointer;">📅 ${mes}</span>
                <span class="valor">R$ ${Number(dados[mes].total).toLocaleString("pt-BR",{style:"currency",currency:"BRL"})}</span>
            </div>

            <div class="detalhes" style="display:none;">
        `

        dados[mes].pagamentos.forEach(p=>{

            const data = p.data ? formatarDataInteligente(p.data) : "Sem data"
            const status = p.pago ? "🟢 Pago" : "🔴 Pendente"

            let detalhesHtml = ""

            if(p.detalhes && p.detalhes.length){

                p.detalhes.forEach(d=>{

                    let nomeDetalhe = ""

                    if(d.tipo === "sabado") nomeDetalhe = "Sábado"
                    if(d.tipo === "hora") nomeDetalhe = "Hora extra"
                    if(d.tipo === "diaria") nomeDetalhe = "Diária"

                    detalhesHtml += `
                    <div style="font-size:12px; color:#666;">
                        • ${nomeDetalhe}: ${Number(d.valor).toLocaleString("pt-BR",{style:"currency",currency:"BRL"})}
                    </div>
                    `
                })
            }
            // 🔵 PRESENÇAS
            if (dados[mes].presencas && dados[mes].presencas.length){

                html += `<div style="margin-top:10px; font-size:13px; color:#555;">`

                dados[mes].presencas.forEach(p=>{

                    const data = new Date(p.data).toLocaleDateString("pt-BR")

                    html += `
                    <div style="margin-bottom:5px;">
                        📅 ${data} • ⏱ ${p.horas}h
                    </div>
                    `
                })

                html += `</div>`
            }

            html += `
            <div class="linha" style="display:flex; justify-content:space-between; align-items:center;">
                
                <div>
                    💰 ${Number(p.valor).toLocaleString("pt-BR",{style:"currency",currency:"BRL"})}
                    ${detalhesHtml}
                    <br>
                    <small>${data} • ${status}</small>
                </div>

                ${p.pago ? `
                <button onclick="baixarComprovante(${p.id})">📄</button>
                ` : ""}

            </div>
            `
        })

        // 🔥 FECHA A DIV DO MÊS (FALTAVA ISSO!)
        html += `
            </div>
        </div>
        `
    }

    document.getElementById("conteudoHistorico").innerHTML = html
    document.getElementById("modalHistorico").style.display = "block"
}

function formatarDataInteligente(data){

    const d = new Date(data)
    const hoje = new Date()
    const ontem = new Date()

    ontem.setDate(hoje.getDate() - 1)

    const mesmaData = (a,b)=>
        a.getDate()===b.getDate() &&
        a.getMonth()===b.getMonth() &&
        a.getFullYear()===b.getFullYear()

    if(mesmaData(d, hoje)) return "Hoje"
    if(mesmaData(d, ontem)) return "Ontem"

    return d.toLocaleDateString("pt-BR")
}

function toggleMes(el){

    const detalhes = el.querySelector(".detalhes")

    if(detalhes.style.display === "none"){
        detalhes.style.display = "block"
    } else {
        detalhes.style.display = "none"
    }
}

function fecharHistorico(){
    document.getElementById("modalHistorico").style.display = "none"
}

function logout(){
localStorage.removeItem("token")
window.location.href="/login-page"
}

carregarCobrancas()

function carregarGrafico(){

const hoje = new Date()
const MES = hoje.getFullYear()+"-"+String(hoje.getMonth()+1).padStart(2,"0")

fetch(`/dashboard-financeiro?mes=${MES}`),{
headers:{
"Authorization":"Bearer "+token
}
}

.then(res=>res.json())

.then(dados=>{

const recebido = dados.total_recebido || 0
const pendente = dados.total_pendente || 0

const ctx = document.getElementById("graficoFinanceiro")

if(!ctx) return

new Chart(ctx,{

type:"doughnut",

data:{
labels:["Recebido","Pendente"],
datasets:[{
data:[recebido,pendente],
backgroundColor:[
"#4CAF50",
"#f44336"
]
}]
}

})

})

}

function salvarFinanceiro(){

    const token = localStorage.getItem("token")

    fetch("/configuracoes",{
        method:"PUT",
        headers:{
            "Content-Type":"application/json",
            "Authorization":"Bearer "+token
        },
        body:JSON.stringify({

            valor_hora: parseFloat(document.getElementById("valor_hora").value) || null,
            valor_diaria: parseFloat(document.getElementById("valor_diaria").value) || null,

            valor_semanal_integral: parseFloat(document.getElementById("valor_semanal_integral").value) || null,
            valor_semanal_meio: parseFloat(document.getElementById("valor_semanal_meio").value) || null,

            valor_mensal_integral: parseFloat(document.getElementById("valor_mensal_integral").value) || null,
            valor_mensal_meio: parseFloat(document.getElementById("valor_mensal_meio").value) || null,

            valor_sabado: parseFloat(document.getElementById("valor_sabado").value) || null,

            pix_chave: document.getElementById("pix_chave").value,
            banco_nome: document.getElementById("banco_nome").value,
            banco_agencia: document.getElementById("banco_agencia").value,
            banco_conta: document.getElementById("banco_conta").value

        })
    })
    .then(res=>{
        if(!res.ok){
            throw new Error("Erro ao salvar financeiro")
        }
        return res.json()
    })
    .then(()=>{
        alert("Configuração financeira salva")
    })
    .catch(err=>{
        alert(err.message)
    })
}

function carregarFinanceiro(){

    const token = localStorage.getItem("token")

    fetch("/configuracoes",{
        headers:{
            "Authorization":"Bearer " + token
        }
    })
    .then(res=>{
    if(!res.ok){
        throw new Error("Erro ao carregar dados")
    }
    return res.json()
})
    .then(dados=>{
        

    const el = document.getElementById("valor_hora")
    if (el) el.value = dados.valor_hora || ""
    if (document.getElementById("valor_diaria"))
        document.getElementById("valor_diaria").value = dados.valor_diaria || ""

    if (document.getElementById("valor_semanal_integral"))
        document.getElementById("valor_semanal_integral").value = dados.valor_semanal_integral || ""

    if (document.getElementById("valor_semanal_meio"))
        document.getElementById("valor_semanal_meio").value = dados.valor_semanal_meio || ""

    if (document.getElementById("valor_mensal_integral"))
        document.getElementById("valor_mensal_integral").value = dados.valor_mensal_integral || ""

    if (document.getElementById("valor_mensal_meio"))
        document.getElementById("valor_mensal_meio").value = dados.valor_mensal_meio || ""

    if (document.getElementById("valor_sabado"))
        document.getElementById("valor_sabado").value = dados.valor_sabado || ""

    if (document.getElementById("tipo_cobranca"))
        document.getElementById("tipo_cobranca").value = dados.tipo_cobranca || "hora"

    if (document.getElementById("pix_chave"))
        document.getElementById("pix_chave").value = dados.pix_chave || ""

    if (document.getElementById("banco_nome"))
        document.getElementById("banco_nome").value = dados.banco_nome || ""

    if (document.getElementById("banco_agencia"))
        document.getElementById("banco_agencia").value = dados.banco_agencia || ""

    if (document.getElementById("banco_conta"))
    document.getElementById("banco_conta").value = dados.banco_conta || ""

    })
}


// carregar automático
document.addEventListener("DOMContentLoaded", carregarFinanceiro)

async function abrirHistorico(tipo) {

    const res = await fetch(`/${tipo}-todos`, {
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        }
    });

    const dados = await res.json();

    const lista = document.getElementById("listaFinanceiro");
    lista.innerHTML = "";

    for (let mes in dados) {

        const bloco = document.createElement("div");

        bloco.innerHTML = `
            <h3>Mês ${mes}</h3>
        `;

        dados[mes].forEach(item => {

            const div = document.createElement("div");
            div.className = "item-historico";

            div.innerHTML = `
                <span>${item.descricao}</span>
                <strong>R$ ${item.valor}</strong>
            `;

            bloco.appendChild(div);
        });

        lista.appendChild(bloco);
    }

    document.getElementById("modalFinanceiro").style.display = "flex";
}



function desconto(id){

let valor = document.getElementById(`valor-${id}`).value

let d = prompt("Valor do desconto:")

valor = valor - d

document.getElementById(`valor-${id}`).value = valor

}

function enviar(id){

fetch(`/cobrancas/${id}/mensagem`,{
headers:{
"Authorization":"Bearer "+token
}
})
.then(res=>res.json())
.then(data=>{

const telefone = data.telefone.replace(/\D/g,"")

const url = `https://wa.me/55${telefone}?text=${encodeURIComponent(data.mensagem)}`

window.open(url)

})

}

function cartao(id){

fetch(`/cobrancas/${id}/asaas`,{
headers:{
"Authorization":"Bearer "+token
}
})
.then(res=>{
// redireciona direto
window.open(res.url)
})

}

setInterval(() => {
    carregarCobrancas()
}, 10000) // atualiza a cada 10 segundos

async function enviarWhats(){

    const res = await fetch("/enviar-cobrancas")
    const dados = await res.json()

    dados.forEach(c => {

        const telefone = c.telefone.replace(/\D/g,"")

        const url = `https://wa.me/55${telefone}?text=${encodeURIComponent(c.mensagem)}`

        window.open(url)
    })
}


function pegarMesURL(){
    const params = new URLSearchParams(window.location.search)
    return params.get("mes")
}

function copiarPix(){
    const pix = document.getElementById("pixCode").value

    if(!pix){
        alert("Gere o PIX primeiro")
        return
    }

    navigator.clipboard.writeText(pix)
    alert("PIX copiado!")
}

function abrirWhats(){

    if(!window.telefonePix){
        alert("Gere o PIX primeiro")
        return
    }

    const pix = document.getElementById("pixCode").value

    const msg = `Olá! Segue o PIX:

${pix}`

    const tel = window.telefonePix.replace(/\D/g,"")

    window.open(`https://wa.me/55${tel}?text=${encodeURIComponent(msg)}`)
}

