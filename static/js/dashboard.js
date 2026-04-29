const token = localStorage.getItem("token")

if (!token){
window.location.href="/login-page"
}

const hoje = new Date()

const MES =
  hoje.getFullYear() +
  "-" +
  String(hoje.getMonth() + 1).padStart(2, "0")


let grafico = null   // ← controle do gráfico


window.mostrarLista = async function mostrarLista(tipo) {

  const lista = document.getElementById("lista-criancas");
  const titulo = document.getElementById("titulo-modal");

  if (!lista || !titulo) {
    console.error("Modal não encontrado");
    return;
  }

lista.innerHTML = "";

  let dados = [];

  // 🔥 presentes agora
  if (tipo === "presentes") {
    titulo.innerText = "Crianças presentes";

    const res = await fetch("/presentes", {
      headers: { Authorization: "Bearer " + token }
    });

    dados = await res.json();
  }

  // 🔥 checkin hoje
  if (tipo === "checkin") {
    titulo.innerText = "Check-in hoje";

    const res = await fetch("/relatorio-hoje", {
      headers: { Authorization: "Bearer " + token }
    });

    dados = await res.json();
  }

  // 🔥 já saíram
  if (tipo === "sairam") {
    titulo.innerText = "Crianças que saíram";

    const res = await fetch("/relatorio-hoje", {
      headers: { Authorization: "Bearer " + token }
    });

    const todos = await res.json();
    dados = todos.filter(p => p.checkout !== null);
  }

  if (dados.length === 0) {
    lista.innerHTML = "<li>Nenhuma criança</li>";
  } else {
    dados.forEach(p => {
      const li = document.createElement("li");
      li.textContent = p.crianca?.nome || "Sem nome";
      lista.appendChild(li);
    });
  }

  document.getElementById("modal").style.display = "block";

}

async function carregarListasDashboard() {

  const headers = { Authorization: "Bearer " + token };

  // PRESENTES
  const res1 = await fetch("/presentes", { headers });
  const presentes = await res1.json();

  renderLista("lista-presentes", presentes, "presente");

  // CHECKIN
  const res2 = await fetch("/relatorio-hoje", { headers });
  const checkins = await res2.json();

  renderLista("lista-checkin", checkins, "checkin");

  // SAÍRAM
  const sairam = checkins.filter(p => p.checkout !== null);

  renderLista("lista-sairam", sairam, "saiu");
}


function renderLista(id, dados, tipo) {

  const lista = document.getElementById(id);
  lista.innerHTML = "";

  dados.forEach(p => {

    const nome = p.crianca?.nome || "Sem nome";
    const inicial = nome.charAt(0).toUpperCase();

    let horario = "";

    if (tipo === "presente" || tipo === "checkin") {
      horario = p.checkin
        ? new Date(p.checkin).toLocaleTimeString('pt-BR', {
            hour: '2-digit',
            minute: '2-digit'
          })
        : "";
    }

    if (tipo === "saiu") {
      horario = p.checkout
        ? new Date(p.checkout).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})
        : "";
    }

    const div = document.createElement("div");
    div.className = "item-crianca";

    div.innerHTML = `
      <div class="info-crianca">
        <div class="avatar-crianca">${inicial}</div>
        <div>
          <div class="nome-crianca">${nome}</div>
          <div class="status">${tipo}</div>
        </div>
      </div>
      <div class="horario ${tipo}">${horario}</div>
    `;

    lista.appendChild(div);
  });
}

  carregarListasDashboard();

  setInterval(() => {
    carregarListasDashboard();
  }, 5000);
window.fecharModal = function () {
  const modal = document.getElementById("modal");

  if (modal) {
    modal.style.display = "none";
  }
}

window.onclick = function(event) {
  const modal = document.getElementById("modal");

  if (event.target === modal) {
    modal.style.display = "none";
  }
}

function abrirFinanceiroMes(){
    window.location.href = "/receita-mes-page"
}

function carregarDashboard(){

// RESUMO
fetch("/resumo-hoje",{
headers:{
"Authorization":"Bearer "+token
}
})
.then(res=>res.json())
.then(dados=>{

const total = document.getElementById("totalHoje");
if (total) total.innerText = dados.total_hoje;

const presentes = document.getElementById("presentesAgora");
if (presentes) presentes.innerText = dados.presentes_agora;

const saiu = document.getElementById("jaSairam");
if (saiu) saiu.innerText = dados.ja_sairam;

})


// FINANCEIRO
fetch(`/dashboard-financeiro?mes=${MES}`,{
headers:{
"Authorization":"Bearer "+token
}
})
.then(res=>res.json())
.then(dados=>{

const receitaEl = document.getElementById("receitaMes");
if (receitaEl) {
  receitaEl.innerText = "R$ " + dados.total_recebido;
}

})

}

// carregar
carregarDashboard()

// atualizar
setInterval(() => {
carregarDashboard()
}, 5000)

function logout(){
localStorage.removeItem("token")
window.location.href="/login-page"
}

async function atualizarDashboard() {

    const res = await fetch("/resumo-hoje", {
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        }
    });

    const dados = await res.json();

    document.getElementById("presentesAgora").innerText = dados.presentes_agora;
    document.getElementById("totalHoje").innerText = dados.total_hoje;
    document.getElementById("jaSairam").innerText = dados.ja_sairam;
}

async function verificarAniversarios() {
    const res = await fetch("/aniversarios-proximos");
    const data = await res.json();

    data.forEach(c => {
        if (c.dias === 0) {
            mostrarNotificacao(
                " Hoje é aniversário",
                `${c.nome} está fazendo aniversário hoje!`,
                "🎂"
            );
        } else {
            mostrarNotificacao(
                " Aniversário chegando",
                `${c.nome} faz aniversário em ${c.dias} dia(s)`,
                "🎉"
            );
        }
    });
}

window.onload = function () {
    verificarAniversarios();
};

function mostrarNotificacao(titulo, mensagem, icone = "🎉") {
    const container = document.getElementById("notificacao-container");

    const div = document.createElement("div");
    div.classList.add("notificacao");

    div.innerHTML = `
        <div class="notificacao-icon">${icone}</div>
        <div class="notificacao-content">
            <div class="notificacao-title">${titulo}</div>
            <div class="notificacao-msg">${mensagem}</div>
        </div>
        <div class="fechar-btn" onclick="this.parentElement.remove()">×</div>
    `;

    container.appendChild(div);

    setTimeout(() => {
        div.remove();
    }, 9000);
}