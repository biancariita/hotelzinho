async function cadastrar() {
    const nome = document.getElementById("nome").value;
    const email = document.getElementById("email").value;
    const senha = document.getElementById("senha").value;

    const res = await fetch("/cadastro", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            nome,
            email,
            senha,
            empresa_id: 1
        })
    });

    const data = await res.json();

    if (!res.ok) {
        document.getElementById("msg").innerText = data.detail || "Erro ao cadastrar";
        return;
    }

    document.getElementById("msg").innerText = data.msg;
}