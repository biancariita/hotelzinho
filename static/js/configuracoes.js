function valor(id){
    const el = document.getElementById(id)
    if (!el) return null
    return el.value
}

function numero(id){
const el = document.getElementById(id)
return el ? parseFloat(el.value) || null : null
}

function salvar(){

fetch("/configuracoes",{
method:"PUT",

headers:{
"Content-Type":"application/json",
"Authorization":"Bearer "+localStorage.getItem("token")
},

body: JSON.stringify({

    nome: valor("nome_empresa"),
    responsavel: valor("responsavel"),
    cnpj: valor("cnpj"),
    telefone: valor("telefone"),
    email: valor("email_empresa"),
    endereco: valor("endereco"),

    valor_hora: numero("valor_hora"),
    valor_diaria: numero("valor_diaria"),

    valor_semanal_integral: numero("valor_semanal_integral"),
    valor_semanal_meio: numero("valor_semanal_meio"),

    valor_mensal_integral: numero("valor_mensal_integral"),
    valor_mensal_meio: numero("valor_mensal_meio"),

    valor_sabado: numero("valor_sabado")
})

})

.then(res=>{
if(!res.ok){
throw new Error("Erro ao salvar configurações")
}
return res.json()
})

.then(()=>{
alert("Configurações salvas com sucesso")
})

.catch(err=>{
alert(err.message)
})

}

function voltar(){
window.history.back()
}

const token = localStorage.getItem("token")

async function alterarEmail(){

const email = document.getElementById("novo_email").value

await fetch("/usuario/email",{

method:"PUT",

headers:{
"Content-Type":"application/json",
Authorization:"Bearer "+token
},

body:JSON.stringify({
email:email
})

})

alert("Email atualizado")

}


async function alterarSenha(){

const senha_atual=document.getElementById("senha_atual").value
const nova_senha=document.getElementById("nova_senha").value

await fetch("/usuario/senha",{

method:"PUT",

headers:{
"Content-Type":"application/json",
Authorization:"Bearer "+token
},

body:JSON.stringify({

senha_atual:senha_atual,
nova_senha:nova_senha

})

})

alert("Senha alterada")

}


async function recuperarSenha(){

const email=document.getElementById("email_recuperacao").value

await fetch("/recuperar-senha",{

method:"POST",

headers:{
"Content-Type":"application/json"
},

body:JSON.stringify({
email:email
})

})

alert("Email de recuperação enviado")

}

function carregarConfiguracoes(){

    const token = localStorage.getItem("token")

    if (!token){
        window.location.href = "/login-page"
    }
    fetch("/configuracoes",{
        headers:{
            "Authorization":"Bearer "+localStorage.getItem("token")
        }
    })
    .then(res=>{
        if(!res.ok){
            throw new Error("Erro ao carregar configurações")
        }
        return res.json()
    })
    .then(dados=>{
        document.getElementById("nome_empresa").value = dados.nome || ""
        document.getElementById("responsavel").value = dados.responsavel || ""
        document.getElementById("cnpj").value = dados.cnpj || ""
        document.getElementById("telefone").value = dados.telefone || ""
        document.getElementById("email_empresa").value = dados.email || ""
        document.getElementById("endereco").value = dados.endereco || ""

        if(document.getElementById("valor_hora"))
            document.getElementById("valor_hora").value = dados.valor_hora || ""

        if(document.getElementById("valor_diaria"))
            document.getElementById("valor_diaria").value = dados.valor_diaria || ""

        if(document.getElementById("valor_semanal_integral"))
            document.getElementById("valor_semanal_integral").value = dados.valor_semanal_integral || ""

        if(document.getElementById("valor_semanal_meio"))
            document.getElementById("valor_semanal_meio").value = dados.valor_semanal_meio || ""

        if(document.getElementById("valor_mensal_integral"))
            document.getElementById("valor_mensal_integral").value = dados.valor_mensal_integral || ""

        if(document.getElementById("valor_mensal_meio"))
            document.getElementById("valor_mensal_meio").value = dados.valor_mensal_meio || ""

        if(document.getElementById("valor_sabado"))
            document.getElementById("valor_sabado").value = dados.valor_sabado || ""
    })
    .catch(err=>{
        console.error(err)
    })
    
}
document.addEventListener("DOMContentLoaded", () => {
    console.log("CARREGANDO CONFIG...")
    carregarConfiguracoes()
})

async function alterarEmail() {
    const email = document.getElementById("novo_email").value

    const res = await fetch("/alterar-email", {
        method: "PUT",
        headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        body: JSON.stringify({ email })
    })

    const data = await res.json()
    alert(data.msg || data.detail)
}