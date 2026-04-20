const token = localStorage.getItem("token");

async function carregarUsuarios() {
    const response = await fetch("http://127.0.0.1:8000/usuarios", {
        headers: {
            "Authorization": `Bearer ${token}`
        }
    });

    if (!response.ok) {
        alert("Você não tem permissão.");
        return;
    }

    const usuarios = await response.json();
    const tbody = document.querySelector("#tabelaUsuarios tbody");
    tbody.innerHTML = "";

    usuarios.forEach(usuario => {
        const tr = document.createElement("tr");

        tr.innerHTML = `
            <td>${usuario.nome}</td>
            <td>${usuario.email}</td>
            <td>${usuario.role}</td>
            <td>
                <select onchange="alterarRole(${usuario.id}, this.value)">
                    <option value="admin">Admin</option>
                    <option value="financeiro">Financeiro</option>
                    <option value="atendente">Atendente</option>
                </select>
            </td>
        `;

        tbody.appendChild(tr);
    });
}

async function alterarRole(id, novaRole) {
    await fetch(`http://127.0.0.1:8000/usuarios/${id}/role?nova_role=${novaRole}`, {
        method: "PUT",
        headers: {
            "Authorization": `Bearer ${token}`
        }
    });

    alert("Permissão atualizada!");
    carregarUsuarios();
}

carregarUsuarios();