const token = localStorage.getItem("token")

if (!token){
window.location.href="/login-page"
}

function carregarPresencas(){

fetch("/presentes",{
headers:{
"Authorization":"Bearer "+token
}
})

.then(res=>res.json())
.then(dados=>{

const tbody = document.querySelector("#tabelaPresencas tbody")

tbody.innerHTML=""

dados.forEach(p=>{

const entrada = new Date(p.checkin)

const linha = `
<tr>

<td>${p.crianca.nome}</td>

<td>${entrada.toLocaleTimeString()}</td>

<td>${calcularTempo(entrada)}</td>

<td>

<button onclick="checkout(${p.crianca_id})">
Checkout
</button>

</td>

</tr>
`

tbody.innerHTML += linha

})

})

}

function calcularTempo(entrada){

const agora = new Date()

const diff = Math.floor((agora - entrada)/60000)

const horas = Math.floor(diff/60)
const minutos = diff%60

return horas+"h "+minutos+"m"

}


setInterval(carregarPresencas,30000)