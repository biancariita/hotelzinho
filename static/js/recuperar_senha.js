async function enviarCodigo(){

await fetch("/recuperar-senha",{

method:"POST",

headers:{
"Content-Type":"application/json"
},

body:JSON.stringify({

email:document.getElementById("email").value,
telefone:document.getElementById("telefone").value

})

})

alert("Código enviado")

}

async function novaSenha(){

await fetch("/nova-senha",{

method:"POST",

headers:{
"Content-Type":"application/json"
},

body:JSON.stringify({

codigo:document.getElementById("codigo").value,
nova_senha:document.getElementById("nova_senha").value

})

})

alert("Senha alterada")

}

