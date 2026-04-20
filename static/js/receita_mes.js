const token = localStorage.getItem("token")

function getMesAtual(){
    const hoje = new Date()
    return String(hoje.getMonth()+1).padStart(2,"0") + "/" + hoje.getFullYear()
}

function carregarDados(){

    const mes = getMesAtual()

    fetch(`/dashboard-financeiro?mes=${mes}`,{
        headers:{ Authorization:"Bearer "+token }
    })
    .then(res=>res.json())
    .then(d=>{

        const faturamento = d.total_recebido || 0

        document.getElementById("faturamento").innerText =
            formatarMoeda(faturamento)

        // 🔥 GASTOS
        fetch(`/gastos?mes=${mes}`,{
            headers:{ Authorization:"Bearer "+token }
        })
        .then(res=>res.json())
        .then(g=>{

        const totalGastos = g.total || 0

        document.getElementById("gastos").innerText =
            formatarMoeda(totalGastos)

        const lucro = faturamento - totalGastos

        document.getElementById("lucro").innerText =
            formatarMoeda(lucro)

        // 🔥 AQUI QUE FALTAVA
        renderizarGastos(g.lista)
    })

    })
}

function salvarGasto(){

    const descricao = document.getElementById("descricaoGasto").value
    const valorInput = document.getElementById("valorGasto").value

    if(!valorInput){
        alert("Digite o valor do gasto")
        return
    }

    const valor = parseFloat(valorInput)

    const mes = getMesAtual()

    fetch("/gastos",{
        method:"POST",
        headers:{
            "Content-Type":"application/json",
            Authorization:"Bearer "+token
        },
        body: JSON.stringify({ descricao, valor, mes })
    })
    .then(()=>{
        fecharModalGasto()

        document.getElementById("descricaoGasto").value = ""
        document.getElementById("valorGasto").value = ""

        carregarDados()
})
}

function renderizarGastos(lista){

    const div = document.getElementById("listaGastos")
    div.innerHTML = ""

    lista.forEach(g=>{

        div.innerHTML += `
            <div class="item-gasto">
                <span>${g.descricao}</span>

                <div class="acoes-gasto">
                    <strong>${formatarMoeda(g.valor)}</strong>

                    <button class="btn-edit"
                        onclick="editarGasto(${g.id}, '${g.descricao}', ${g.valor})">
                        ✏️
                    </button>

                    <button class="btn-delete"
                        onclick="excluirGasto(${g.id})">
                        🗑️
                    </button>
                </div>
            </div>
        `
    })
}

function toggleGastos(){
    const lista = document.getElementById("listaGastos")

    if(lista.style.display === "none" || lista.style.display === ""){
        lista.style.display = "block"
    } else {
        lista.style.display = "none"
    }
}


function editarGasto(id, descricao, valor){

    document.getElementById("descricaoGasto").value = descricao
    document.getElementById("valorGasto").value = valor

    document.getElementById("modalGasto").style.display = "block"

    // sobrescreve salvar
    window.salvarGasto = function(){

        fetch(`/gastos/${id}`,{
            method:"PUT",
            headers:{
                "Content-Type":"application/json",
                Authorization:"Bearer "+token
            },
            body: JSON.stringify({
                descricao: document.getElementById("descricaoGasto").value,
                valor: parseFloat(document.getElementById("valorGasto").value)
            })
        })
        .then(()=>{
            fecharModalGasto()
            carregarDados()
        })
    }
}

function excluirGasto(id){

    if(!confirm("Excluir gasto?")) return

    fetch(`/gastos/${id}`,{
        method:"DELETE",
        headers:{ Authorization:"Bearer "+token }
    })
    .then(()=>{
        carregarDados()
    })
}



function formatarMoeda(valor){
    return Number(valor).toLocaleString("pt-BR", {
        style: "currency",
        currency: "BRL"
    })
}

function abrirModalGasto(){
    document.getElementById("modalGasto").style.display = "block"
}

function fecharModalGasto(){
    document.getElementById("modalGasto").style.display = "none"
}

window.onload = function(){
    carregarDados()
}