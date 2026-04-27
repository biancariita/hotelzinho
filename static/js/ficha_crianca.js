const token = localStorage.getItem("token")

const id = window.location.pathname.split("/")[2]

// 🔥 BOTÃO STATUS
function ajustarBotaoStatus(c) {
    const btn = document.getElementById("btnStatus")

    if (!btn) return

    if (c.ativo) {
        btn.innerText = "Desativar"
        btn.onclick = () => desativar(c.id)
    } else {
        btn.innerText = "Reativar"
        btn.onclick = () => reativar(c.id)
    }
}

// 🔥 BUSCAR DADOS
fetch(`/api/ficha-crianca/${id}`,{
headers:{
"Authorization":"Bearer "+token
}
})
.then(res=>res.json())
.then(data=>{

const c = data.crianca

// 🔥 DADOS DA CRIANÇA
document.getElementById("dados_crianca").innerHTML = `
<h3>${c.nome}</h3>

<p><b>Responsável:</b> ${c.responsaveis?.[0]?.nome || "-"}</p>
<p><b>Telefone:</b> ${c.responsaveis?.[0]?.telefone || "-"}</p>
<p><b>Endereço:</b> ${c.responsaveis?.[0]?.endereco || "-"}</p>
<p><b>Alergias:</b> ${c.alergias || "-"}</p>
<p><b>Observações:</b> ${c.observacoes || "-"}</p>
<p><b>Autorização imagem:</b> ${c.autorizacao_imagem ? "Sim" : "Não"}</p>
`

ajustarBotaoStatus(c)

// =========================
// 🔥 PRESENÇA POR MÊS
// =========================
const tabelaPresenca = document.getElementById("historico_presenca")
tabelaPresenca.innerHTML = ""

const porMes = {}

data.presencas.forEach(p => {
    const d = new Date(p.checkin)
    const mes = `${String(d.getMonth()+1).padStart(2,'0')}/${d.getFullYear()}`

    if(!porMes[mes]) porMes[mes] = []
    porMes[mes].push(p)
})

for (let mes in porMes){

    // 🔹 TÍTULO DO MÊS
    const titulo = document.createElement("tr")

    titulo.innerHTML = `
        <td colspan="3" class="mes-toggle" data-mes="${mes}">
            📅 ${mes}
        </td>
    `

    tabelaPresenca.appendChild(titulo)

    // 🔹 LINHAS
    porMes[mes].forEach(p=>{
        const linha = document.createElement("tr")

        linha.innerHTML = `
            <td>${formatarDataBR(p.checkin)}</td>
            <td>${p.checkout ? formatarDataBR(p.checkout) : "-"}</td>
            <td>${calcularHoras(p.checkin, p.checkout)}</td>
        `

        linha.classList.add("linha-mes")
        linha.setAttribute("data-mes", mes)
        linha.style.display = "none" // 🔥 começa fechado

        tabelaPresenca.appendChild(linha)
    })
}

// =========================
// 🔥 FINANCEIRO
// =========================
const tabelaFinanceiro = document.getElementById("historico_financeiro")
tabelaFinanceiro.innerHTML = ""

data.cobrancas.forEach(c=>{
const linha = document.createElement("tr")

linha.innerHTML = `
<td>R$ ${Number(c.valor).toFixed(2)}</td>

<td>
    ${c.pago 
        ? `<span style="color:#10b981;">Pago</span><br>
           <small>${formatarDataBR(c.data_pagamento)}</small>`
        : `<span style="color:#ef4444;">Pendente</span><br>
           <small>-</small>`
    }
</td>
`

tabelaFinanceiro.appendChild(linha)
})

})

// =========================
// 🔥 FUNÇÕES
// =========================

function reativar(id){
fetch(`/reativar-crianca/${id}`,{
method:"PUT",
headers:{ Authorization:"Bearer "+token }
})
.then(res => {
if(res.ok){
mostrarToast("Criança reativada ✅", "success")
}
setTimeout(()=>location.reload(),1000)
})
}

function desativar(id){
fetch(`/desativar-crianca/${id}`,{
method:"PUT",
headers:{ Authorization:"Bearer "+token }
})
.then(res => {
if(res.ok){
mostrarToast("Criança desativada ❌", "error")
}
setTimeout(()=>location.reload(),1000)
})
}

// 🔥 FORMATAR DATA
function formatarDataBR(data){
    if (!data) return "-"

    const d = new Date(data)

    const dia = String(d.getDate()).padStart(2, '0')
    const mes = String(d.getMonth() + 1).padStart(2, '0')
    const ano = d.getFullYear()

    const hora = String(d.getHours()).padStart(2, '0')
    const min = String(d.getMinutes()).padStart(2, '0')

    return `${dia}/${mes}/${ano} - ${hora}:${min}`
}

// 🔥 CALCULAR HORAS
function calcularHoras(checkin, checkout){
    if (!checkout) return "-"

    const inicio = new Date(checkin)
    const fim = new Date(checkout)

    const horas = (fim - inicio) / (1000 * 60 * 60)

    return horas.toFixed(1) + "h"
}

document.addEventListener("click", function(e){

    if(e.target.classList.contains("mes-toggle")){

        const mes = e.target.getAttribute("data-mes")

        const linhas = document.querySelectorAll(`.linha-mes[data-mes='${mes}']`)

        linhas.forEach(linha => {
            linha.style.display = linha.style.display === "none" ? "table-row" : "none"
        })

    }

})