const token = localStorage.getItem("token")

if(!token){
    window.location.href="/login-page"
}

// 🔥 CARREGAR CRIANÇAS
function carregarCriancas(){

fetch("/criancas",{
headers:{ Authorization:"Bearer "+token }
})
.then(res=>res.json())
.then(dados=>{

const tbody=document.querySelector("#tabelaCriancas tbody")
tbody.innerHTML=""

dados.forEach(c=>{

const resp=c.responsaveis?.[0] || {}

const botaoStatus = c.ativo
? `<button class="btn-desativar" onclick="desativar(${c.id})">Desativar</button>`
: `<button class="btn-reativar" onclick="reativar(${c.id})">Reativar</button>`

const linha=`
<tr>

<td>${c.nome}</td>
<td>${calcularIdade(c.data_nascimento)}</td>
<td>${resp.nome || "-"}</td>
<td>${resp.telefone || "-"}</td>
<td>${c.alergias || "-"}</td>
<td>${c.autorizacao_imagem ? "Sim":"Não"}</td>
<td>${nomePlano(c.tipo_cobranca)}</td>


<td>
<button class="btn-abrir" onclick="abrirFicha(${c.id})">Abrir</button>
<button class="btn-editar" onclick="editar(${c.id})">Editar</button>
${botaoStatus}
</td>

</tr>
`

tbody.innerHTML+=linha

function nomePlano(tipo){
    if(tipo === "hora") return "Hora"
    if(tipo === "diaria") return "Diária"

    if(tipo === "mensal") return "Mensal Integral"
    if(tipo === "meio_periodo") return "Mensal Meio Período"

    if(tipo === "semanal") return "Semanal Integral"
    if(tipo === "semanal_meio") return "Semanal Meio Período"

    return "-"
}

})

})

}

function capitalizarTexto(texto){
    return texto
        .toLowerCase()
        .replace(/\b\w/g, letra => letra.toUpperCase())
}

// 🔥 IDADE
function calcularIdade(data){
if(!data) return ""

const nascimento=new Date(data)
const hoje=new Date()

let idade=hoje.getFullYear()-nascimento.getFullYear()

const mes=hoje.getMonth()-nascimento.getMonth()

if(mes<0||(mes===0&&hoje.getDate()<nascimento.getDate())){
idade--
}

return idade+" anos"
}

// 🔥 PESQUISA
function pesquisarCrianca(){
const texto=document.getElementById("pesquisaCrianca").value.toLowerCase()

document.querySelectorAll("#tabelaCriancas tbody tr")
.forEach(linha=>{
const nome=linha.children[0].innerText.toLowerCase()
linha.style.display=nome.includes(texto)?"":"none"
})
}

// 🔥 NAVEGAÇÃO
function abrirFicha(id){
window.location.href=`/ficha-crianca/${id}`
}

function editar(id){

fetch("/criancas",{
headers:{ Authorization:"Bearer "+token }
})
.then(res=>res.json())
.then(lista=>{

const crianca = lista.find(c => c.id === id)
if(!crianca) return

document.getElementById("tituloModal").innerText="Editar Criança"

document.getElementById("crianca_id").value = crianca.id
document.getElementById("nome").value = crianca.nome || ""
document.getElementById("data_nascimento").value = crianca.data_nascimento || ""
document.getElementById("alergias").value = crianca.alergias || ""
document.getElementById("observacoes").value = crianca.observacoes || ""
document.getElementById("tipo_cobranca").value = crianca.tipo_cobranca || "hora"
document.getElementById("dia_vencimento").value = crianca.dia_vencimento || ""

// ✅ LIMPA TODOS OS RADIOS (IMPORTANTE)
document.querySelectorAll('input[name="autorizacao_imagem"]').forEach(r => r.checked = false)

// ✅ SETA CORRETO BASEADO NO BANCO
if(crianca.autorizacao_imagem === true){
    const radioSim = document.querySelector('input[name="autorizacao_imagem"][value="true"]')
    if(radioSim) radioSim.checked = true
} else {
    const radioNao = document.querySelector('input[name="autorizacao_imagem"][value="false"]')
    if(radioNao) radioNao.checked = true
}

// 🔥 RESPONSÁVEIS
const container = document.getElementById("responsaveis-container")
container.innerHTML=""

crianca.responsaveis.forEach(r=>{
const bloco = document.createElement("div")

bloco.innerHTML=`
<input value="${r.nome || ""}" class="resp-nome" placeholder="Nome">
<input value="${r.telefone || ""}" class="resp-telefone" placeholder="Telefone">
<input value="${r.cpf || ""}" class="resp-cpf" placeholder="CPF"> 
<input value="${r.endereco || ""}" class="resp-endereco" placeholder="Endereço">
<button onclick="removerResponsavel(this)">Remover</button>
<hr>
`

container.appendChild(bloco)
})

// 🔥 ABRE MODAL POR ÚLTIMO
abrirModal()

})

}

// 🔥 DESATIVAR
function desativar(id){

if(!confirm("Deseja desativar esta criança?")) return

fetch(`/criancas/${id}`,{
method:"DELETE",
headers:{ Authorization:"Bearer "+token }
})
.then(()=>carregarCriancas())

}

// 🔥 REATIVAR (AGORA FUNCIONA)
function reativar(id){

fetch(`/reativar-crianca/${id}`,{
method:"PUT",
headers:{ Authorization:"Bearer "+token }
})
.then(()=>carregarCriancas())

}

// 🔥 MODAL
function abrirModal(){
document.getElementById("modal").style.display="flex"
}

function fecharModal(){
document.getElementById("modal").style.display="none"
}

// 🔥 RESPONSÁVEIS
function adicionarResponsavel(){

const container=document.getElementById("responsaveis-container")

const bloco=document.createElement("div")

bloco.innerHTML=`
<input placeholder="Nome" class="resp-nome">
<input placeholder="Telefone" class="resp-telefone">
<input placeholder="CPF" class="resp-cpf">
<input placeholder="Endereço" class="resp-endereco">  <!-- 🔥 AQUI -->
<button onclick="removerResponsavel(this)">Remover</button>
<hr>
`

container.appendChild(bloco)

}

function removerResponsavel(btn){
btn.parentElement.remove()
}

// 🔥 SALVAR
function salvarCrianca(){

const id = document.getElementById("crianca_id").value

const nome = document.getElementById("nome").value
const data_nascimento = document.getElementById("data_nascimento").value
const alergias = document.getElementById("alergias").value
const observacoes = document.getElementById("observacoes").value

// ✅ VENCIMENTO (corrigido)
const valorVencimento = document.getElementById("dia_vencimento").value
const dia_vencimento = valorVencimento ? parseInt(valorVencimento) : null

// ✅ AUTORIZAÇÃO (CORREÇÃO DEFINITIVA)
const radioSelecionado = document.querySelector('input[name="autorizacao_imagem"]:checked')

const autorizacao_imagem = radioSelecionado
    ? radioSelecionado.value.toLowerCase() === "true"
    : false

const tipo_cobranca = document.getElementById("tipo_cobranca").value

// 🔥 RESPONSÁVEIS
const responsaveis = []

const nomes = document.querySelectorAll(".resp-nome")
const telefones = document.querySelectorAll(".resp-telefone")
const cpfs = document.querySelectorAll(".resp-cpf")
const enderecos = document.querySelectorAll(".resp-endereco")

nomes.forEach((el, i) => {

responsaveis.push({
nome: el.value,
telefone: telefones[i]?.value || "",
cpf: cpfs[i]?.value || "",
endereco: enderecos[i]?.value || ""
})

})

// 🔍 DEBUG (pode apagar depois)
console.log("RADIO:", radioSelecionado)
console.log("VALOR RADIO:", radioSelecionado?.value)
console.log("ENVIANDO AUTORIZAÇÃO:", autorizacao_imagem
)

// 🔥 DADOS
const dados = {
nome,
data_nascimento,
alergias,
observacoes,
tipo_cobranca,
dia_vencimento,
autorizacao_imagem,
responsaveis
}

// 🔥 URL
const url = id ? `/criancas/${id}` : "/criancas"
const metodo = id ? "PUT" : "POST"

// 🔥 FETCH
fetch(url,{
method: metodo,
headers:{
"Content-Type":"application/json",
Authorization:"Bearer "+token
},
body: JSON.stringify(dados)
})
.then(res => {

if(!res.ok){
throw new Error("Erro ao salvar")
}

return res.json()

})
.then(()=>{

// limpar campos
document.getElementById("crianca_id").value = ""
document.getElementById("nome").value = ""
document.getElementById("data_nascimento").value = ""
document.getElementById("alergias").value = ""
document.getElementById("observacoes").value = ""
document.getElementById("dia_vencimento").value = ""

document.getElementById("responsaveis-container").innerHTML = ""

// fechar modal
fecharModal()

// atualizar lista
carregarCriancas()

// ⚠️ NÃO chama carregarGrafico aqui (não existe nessa página)

// alerta
alert("Salvo com sucesso ✅")

})
.catch(err=>{
console.error(err)
alert("Erro ao salvar ❌")
})

}

// 🔥 LOGOUT
function logout(){
localStorage.removeItem("token")
window.location.href="/login-page"
}

// 🔥 INICIAL
carregarCriancas()

document.addEventListener("input", function(e){

    if(e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA"){

        // ignora campos numéricos e data
        if(e.target.type === "number" || e.target.type === "date") return

        e.target.value = capitalizarTexto(e.target.value)
    }

})

function formatarTelefone(valor){
    valor = valor.replace(/\D/g, "")

    if(valor.length <= 10){
        return valor
            .replace(/^(\d{2})(\d)/g, "($1) $2")
            .replace(/(\d{4})(\d)/, "$1-$2")
    } else {
        return valor
            .replace(/^(\d{2})(\d)/g, "($1) $2")
            .replace(/(\d{5})(\d)/, "$1-$2")
    }
}

function formatarCPF(valor){
    valor = valor.replace(/\D/g, "")

    return valor
        .replace(/(\d{3})(\d)/, "$1.$2")
        .replace(/(\d{3})(\d)/, "$1.$2")
        .replace(/(\d{3})(\d{1,2})$/, "$1-$2")
}

document.addEventListener("input", function(e){

    // TELEFONE
    if(e.target.id.includes("telefone")){
        e.target.value = formatarTelefone(e.target.value)
    }

    // CPF
   if(e.target.classList.contains("resp-cpf")){
    e.target.value = formatarCPF(e.target.value)
}

})