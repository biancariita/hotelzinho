async function cadastrar() {
    const nome = document.getElementById("nome").value;
    const email = document.getElementById("email").value;
    const senha = document.getElementById("senha").value;
    const empresa = document.getElementById("empresa").value;

    const res = await fetch("/cadastro", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            nome,
            email,
            senha,
            nome_empresa: empresa
        })
    });

    const data = await res.json();

    if (!res.ok) {
        document.getElementById("msg").innerText =
            data.detail?.[0]?.msg || data.detail || "Erro ao cadastrar";
        return;
    }

    document.getElementById("msg").innerText = data.msg;
}
