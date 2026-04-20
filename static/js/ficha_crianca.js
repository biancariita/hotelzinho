const token = localStorage.getItem("token")

const id = window.location.pathname.split("/")[2]

// 🔥 FUNÇÃO BOTÃO (AGORA NO LUGAR CERTO)
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

// 🔥 BUSCAR DADOS DA CRIANÇA
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

// 🔥 AJUSTA BOTÃO AQUI (CORRETO)
ajustarBotaoStatus(c)

// 🔥 HISTÓRICO PRESENÇA
const tabelaPresenca = document.getElementById("historico_presenca")
tabelaPresenca.innerHTML = ""

data.presencas.forEach(p=>{
const linha = document.createElement("tr")

linha.innerHTML = `
<td>${p.checkin}</td>
<td>${p.checkout || "-"}</td>
<td>
<button onclick="editarPresenca(${p.id}, '${p.checkin}', '${p.checkout || ""}')">
Editar
</button>
</td>
`

tabelaPresenca.appendChild(linha)
})

// 🔥 HISTÓRICO FINANCEIRO
const tabelaFinanceiro = document.getElementById("historico_financeiro")
tabelaFinanceiro.innerHTML = ""

data.cobrancas.forEach(c=>{
const linha = document.createElement("tr")

linha.innerHTML = `
<td>R$ ${c.valor}</td>
<td>${c.pago ? "Pago" : "Pendente"}</td>
`

tabelaFinanceiro.appendChild(linha)
})

})


// 🔥 FUNÇÃO REATIVAR
function reativar(id){

fetch(`/reativar-crianca/${id}`,{
method:"PUT",
headers:{
Authorization:"Bearer "+token
}
})
.then(res => {

if(res.ok){
mostrarToast("Criança reativada ✅", "success")
} else {
mostrarToast("Erro ao reativar", "error")
}

setTimeout(() => {
window.location.reload()
}, 1000)

})

}


// 🔥 (SE NÃO TIVER) DESATIVAR
function desativar(id){

fetch(`/desativar-crianca/${id}`,{
method:"PUT",
headers:{
Authorization:"Bearer "+token
}
})
.then(res => {

if(res.ok){
mostrarToast("Criança desativada ❌", "error")
} else {
mostrarToast("Erro ao desativar", "error")
}

setTimeout(() => {
window.location.reload()
}, 1000)

})

}

function editarPresenca(id, checkin, checkout){

document.getElementById("presenca_id").value = id

// formata data pro input
document.getElementById("edit-checkin").value = formatarData(checkin)
document.getElementById("edit-checkout").value = checkout ? formatarData(checkout) : ""

document.getElementById("modal-editar").style.display = "block"
}

function formatarData(data){
return new Date(data).toISOString().slice(0,16)
}

function salvarEdicao(){

const id = document.getElementById("presenca_id").value
const checkin = document.getElementById("edit-checkin").value
const checkout = document.getElementById("edit-checkout").value

fetch(`/presencas/${id}`,{
method:"PUT",
headers:{
"Content-Type":"application/json",
Authorization:"Bearer "+token
},
body: JSON.stringify({
checkin: checkin,
checkout: checkout
})
})
.then(()=>{
fecharModalEditar()
location.reload()
})

}

function fecharModalEditar(){
document.getElementById("modal-editar").style.display = "none"
}