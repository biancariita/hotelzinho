const token = localStorage.getItem("token")

if(!token){
window.location.href="/login-page"
}

function mostrarToast(mensagem, tipo = "success") {
    const toast = document.getElementById("toast")

    toast.innerText = mensagem
    toast.className = `toast show ${tipo}`

    setTimeout(() => {
        toast.className = "toast"
    }, 3000)
}

function carregarCriancas(){

fetch("/criancas",{
headers:{
Authorization:"Bearer "+token
}
})

.then(res=>res.json())
.then(dados=>{

const tbody=document.querySelector("#tabelaCriancas tbody")

tbody.innerHTML=""

dados.forEach(c=>{

const resp=c.responsaveis?.[0]?.nome || "-"

const acoes = c.ativo
? `
<div style="display:flex; flex-direction:column; gap:5px;">

<!-- 🔥 AUTOMÁTICO -->
<div>
<button onclick="checkin(${c.id})">Check-in</button>
<button onclick="checkout(${c.id})">Checkout</button>
</div>

<!-- 🔥 MANUAL -->
<div>
<input type="datetime-local" id="edit-checkin-${c.id}">
<input type="datetime-local" id="edit-checkout-${c.id}">

<button onclick="salvarEdicaoDireta(${c.id})">Salvar</button>
</div>

</div>
`
: `<span style="color:#888">Desativada</span>`

const linha=`
<tr>

<td>${c.nome}</td>

<td>${calcularIdade(c.data_nascimento)}</td>

<td>${resp}</td>

<td>${acoes}</td>

<td>${c.plano || "-"}</td>

<td>R$ ${c.valor || 0}</td>

</tr>
`

tbody.innerHTML+=linha

})

})

}

if (window.carregarDashboard) {
  carregarDashboard();
}

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

function checkin(id){

    const input = document.getElementById(`edit-checkin-${id}`)
    const data = input ? input.value : null

    fetch(`/checkin/${id}`,{
        method:"POST",
        headers:{
            "Content-Type":"application/json",
            Authorization:"Bearer "+token
        },
        body: data && data !== ""
            ? JSON.stringify({ checkin: data })
            : null
    })
    .then(async res => {

        const dados = await res.json();

        if(res.ok){
            mostrarToast("Check-in realizado ✅")
            atualizarDashboard();
        } else {
            mostrarToast(dados.detail || "Erro no check-in ❌", "error")
        }

        carregarCriancas()
    })
}

async function checkout(id, btn) {
    try {

        if (btn) btn.disabled = true;

        // 🔥 pega valor do input manual
        const input = document.getElementById(`edit-checkout-${id}`)
        const data = input ? input.value : null

        const res = await fetch(`/checkout/${id}`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json",
                "Authorization": "Bearer " + localStorage.getItem("token")
            },
            body: data && data !== ""
                ? JSON.stringify({ checkout: data })
                : null
        });
        

        const dados = await res.json();

        if (!res.ok) {
            throw new Error(dados.detail || "Erro");
        }

        mostrarToast("Checkout salvo ✅", "success");

        if (typeof atualizarDashboard === "function") {
            atualizarDashboard();
        }

        carregarCriancas();

    } catch (err) {
        mostrarToast(err.message || "Erro no checkout", "error");
    } finally {
        if (btn) btn.disabled = false;
    }
}

function logout(){
localStorage.removeItem("token")
window.location.href="/login-page"
}

carregarCriancas()

const titulo = document.getElementById("tituloModal")

if(titulo){
titulo.innerText="Editar Criança"
}

async function salvarEdicaoDireta(criancaId){

    const checkin = document.getElementById(`edit-checkin-${criancaId}`)?.value
    const checkout = document.getElementById(`edit-checkout-${criancaId}`)?.value

    if(checkin && checkout){

        const res = await fetch("/presenca-manual",{
            method:"POST",
            headers:{
                "Content-Type":"application/json",
                Authorization:"Bearer "+token
            },
            body: JSON.stringify({
                crianca_id: criancaId,
                checkin,
                checkout
            })
        })

        if(res.ok){
            mostrarToast("Presença manual criada ✅", "success")
        } else {
            const erro = await res.json()
            mostrarToast(erro.detail || "Erro ao salvar", "error")
        }
        carregarCriancas()
        return
    }

    // 🔽 RESTO CONTINUA IGUAL (SEU CÓDIGO)

    fetch("/relatorio-hoje",{
        headers:{ Authorization:"Bearer "+token }
    })
    .then(res=>res.json())
    .then(lista=>{

        let presenca = lista.find(p =>
            p.crianca_id === criancaId && p.checkout === null
        )

        // 🔥 SÓ CHECKIN
            if(!presenca && checkin){

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
                .then(res=>{
                    if(res.ok){
                        mostrarToast("Check-in manual salvo ✅", "success")
                    } else {
                        mostrarToast("Erro ao salvar check-in", "error")
                    }
                    carregarCriancas()
                })
                return
            }

            // 🔥 NOVO BLOCO
            if(!presenca && checkout){
                mostrarToast("Não existe check-in para esse dia ❌", "error")
                return
            }

        // 🔥 EDITAR EXISTENTE
        if(presenca){

            fetch(`/presencas/${presenca.id}`,{
                method:"PUT",
                headers:{
                    "Content-Type":"application/json",
                    Authorization:"Bearer "+token
                },
                body: JSON.stringify({
                    checkin: checkin && checkin !== "" ? checkin : presenca.checkin,
                    checkout: checkout
                })
            })
            .then(res=>{
                if(res.ok){
                    mostrarToast("Horário atualizado ✅", "success")
                } else {
                    mostrarToast("Erro ao atualizar", "error")
                }
                carregarCriancas()
            })
        }

    })
    .catch(()=>{
        mostrarToast("Erro geral", "error")
    })
}
