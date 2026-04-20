document.getElementById("loginForm").addEventListener("submit", async function(event) {
    event.preventDefault();

    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

    const formData = new URLSearchParams();
    formData.append("username", username);
    formData.append("password", password);

    const response = await fetch("/login", {
        method: "POST",
        headers: {
            "Content-Type": "application/x-www-form-urlencoded"
        },
        body: formData
    });

    const data = await response.json();

    if (response.ok) {

        // salva o token
        localStorage.setItem("token", data.access_token);

        // pega o mês atual automaticamente
        const hoje = new Date();
        const mes = String(hoje.getMonth() + 1).padStart(2, "0");

        // redireciona para o dashboard
        window.location.href = "/dashboard-page" 

    } else {
        document.getElementById("erro").innerText = "Login inválido";
    }
});

function abrirRecuperacao(){

window.location.href="/recuperar-senha"

}