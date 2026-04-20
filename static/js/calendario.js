const token = localStorage.getItem("token")

let dataAtual = new Date()

function carregarCalendario(){

    const ano = dataAtual.getFullYear()
    const mes = dataAtual.getMonth()

    document.getElementById("mesAtual").innerText =
        dataAtual.toLocaleString("pt-BR",{month:"long",year:"numeric"})

    const primeiroDia = new Date(ano, mes, 1).getDay()
    const diasNoMes = new Date(ano, mes+1, 0).getDate()

    const calendario = document.getElementById("calendario")
    calendario.innerHTML = ""

    for(let i=0;i<primeiroDia;i++){
        calendario.innerHTML += "<div></div>"
    }

    for(let d=1; d<=diasNoMes; d++){

        calendario.innerHTML += `
            <div class="dia" onclick="abrirDia(${d})">
                ${d}
            </div>
        `
    }
}

function abrirDia(dia){

    const data = new Date(
        dataAtual.getFullYear(),
        dataAtual.getMonth(),
        dia
    )

    document.getElementById("modalDia").style.display="block"
    document.getElementById("dataSelecionada").innerText =
        data.toLocaleDateString()

    window.dataSelecionada = data
    carregarCriancasSelect()
}

function fecharModal(){
    document.getElementById("modalDia").style.display="none"
}

function mesAnterior(){
    dataAtual.setMonth(dataAtual.getMonth()-1)
    carregarCalendario()
}

function proximoMes(){
    dataAtual.setMonth(dataAtual.getMonth()+1)
    carregarCalendario()
}

function carregarCriancasSelect(){

    fetch("/criancas",{
        headers:{ Authorization:"Bearer "+token }
    })
    .then(res=>res.json())
    .then(lista=>{

        const select = document.getElementById("criancaSelect")
        select.innerHTML=""

        lista.forEach(c=>{
            select.innerHTML += `
                <option value="${c.id}">
                    ${c.nome}
                </option>
            `
        })

    })
}

function salvarPresenca(){

    const criancaId = document.getElementById("criancaSelect").value

    const checkin = document.getElementById("checkin").value
    const checkout = document.getElementById("checkout").value

    fetch(`/checkin/${criancaId}`,{
        method:"POST",
        headers:{
            "Content-Type":"application/json",
            Authorization:"Bearer "+token
        },
        body: JSON.stringify({
            checkin: checkin
        })
    })
    .then(()=>{

        if(checkout){
            fetch(`/checkout/${criancaId}`,{
                method:"PUT",
                headers:{
                    "Content-Type":"application/json",
                    Authorization:"Bearer "+token
                },
                body: JSON.stringify({
                    checkout: checkout
                })
            })
        }

        fecharModal()
    })
}