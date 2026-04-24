async function enviarCodigo() {
    const email = document.getElementById("email").value;

    if (!email) {
        alert("Digite o usuário");
        return;
    }

    try {
        const res = await fetch("/recuperar-senha", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                email: email
            })
        });

        const data = await res.json();

        if (!res.ok) {
            alert(data.detail);
            return;
        }

        alert(data.msg);
    } catch (e) {
        console.error(e);
        alert("Erro ao enviar código");
    }
}


async function alterarSenha() {
    const email = document.getElementById("email").value;
    const codigo = document.getElementById("codigo").value;
    const nova_senha = document.getElementById("nova_senha").value;

    if (!email || !codigo || !nova_senha) {
        alert("Preencha todos os campos");
        return;
    }

    try {
        const res = await fetch("/nova-senha", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                email: email,
                codigo: codigo,
                nova_senha: nova_senha
            })
        });

        const data = await res.json();

        if (!res.ok) {
            document.getElementById("msg").innerText = data.detail;
            return;
        }

        document.getElementById("msg").innerText = data.msg;

    } catch (e) {
        console.error(e);
        alert("Erro ao alterar senha");
    }
}
