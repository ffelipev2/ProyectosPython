// Función para validar el RUT en tiempo real
function validarRutEnTiempoReal(input, mensajeErrorId) {
    const rut = input.value.trim(); // Obtener el valor del campo RUT
    const mensajeError = document.getElementById(mensajeErrorId); // Elemento para mostrar el mensaje de error

    if (rut === "") {
        mensajeError.textContent = ""; // Limpiar el mensaje si el campo está vacío
        return;
    }

    // Validar el formato del RUT
    if (!/^\d{7,8}-[\dkK]$/.test(rut)) {
        mensajeError.textContent = "Formato de RUT inválido. Use el formato 12345678-9 o 12345678-K.";
        return;
    }

    // Validar el dígito verificador
    const [numero, dv] = rut.split("-");
    const dvCalculado = calcularDigitoVerificador(numero);

    if (dv.toUpperCase() !== dvCalculado) {
        mensajeError.textContent = "RUT inválido. El dígito verificador no es correcto.";
        return;
    }

    // Si el RUT es válido, limpiar el mensaje de error
    mensajeError.textContent = "";
}

// Función para calcular el dígito verificador
function calcularDigitoVerificador(numero) {
    let suma = 0;
    let multiplicador = 2;

    for (let i = numero.length - 1; i >= 0; i--) {
        suma += parseInt(numero[i]) * multiplicador;
        multiplicador++;
        if (multiplicador > 7) multiplicador = 2;
    }

    const dv = 11 - (suma % 11);
    if (dv === 11) return '0';
    if (dv === 10) return 'K';
    return dv.toString();
}

// Función para validar los minutos en tiempo real
function validarMinutosEnTiempoReal(input, mensajeErrorId) {
    const minutos = parseInt(input.value); // Obtener el valor del campo minutos
    const mensajeError = document.getElementById(mensajeErrorId); // Elemento para mostrar el mensaje de error

    if (isNaN(minutos)) {
        mensajeError.textContent = "Ingrese un número válido.";
        return;
    }

    if (minutos < 5 || minutos > 240) {
        mensajeError.textContent = "Los minutos deben estar entre 5 y 240.";
        return;
    }

    // Si los minutos son válidos, limpiar el mensaje de error
    mensajeError.textContent = "";
}

// Función para validar el formulario de visita antes de enviarlo
function validarFormularioVisita() {
    const rutInput = document.querySelector('input[name="buscar_rut"]');
    const minutosInput = document.querySelector('input[name="minutos"]');
    const rutError = document.getElementById('rut-error-visita');
    const minutosError = document.getElementById('minutos-error');

    // Validar el RUT
    const rut = rutInput.value.trim();
    if (!/^\d{7,8}-[\dkK]$/.test(rut)) {
        rutError.textContent = "Formato de RUT inválido. Use el formato 12345678-9 o 12345678-K.";
        return false; // Evitar que el formulario se envíe
    }

    const [numero, dv] = rut.split("-");
    const dvCalculado = calcularDigitoVerificador(numero);
    if (dv.toUpperCase() !== dvCalculado) {
        rutError.textContent = "RUT inválido. El dígito verificador no es correcto.";
        return false; // Evitar que el formulario se envíe
    }

    // Validar los minutos
    const minutos = parseInt(minutosInput.value);
    if (isNaN(minutos) || minutos < 5 || minutos > 240) {
        minutosError.textContent = "Los minutos deben estar entre 5 y 240.";
        return false; // Evitar que el formulario se envíe
    }

    // Si todo es válido, permitir que el formulario se envíe
    return true;
}

// Función para ocultar los mensajes después de 3 segundos
function ocultarMensajes() {
    const mensajes = document.querySelectorAll('.alert');
    mensajes.forEach(function(mensaje) {
        setTimeout(function() {
            mensaje.style.display = 'none';
        }, 3000); // 3000 milisegundos = 3 segundos
    });
}

// Ejecutar la función cuando la página se cargue
window.onload = ocultarMensajes;

// Función para mostrar un formulario y ocultar los demás
function mostrarFormulario(id) {
    // Oculta todos los formularios
    document.querySelectorAll('.formulario').forEach(form => {
        form.classList.add('hidden');
    });
    // Muestra el formulario seleccionado
    document.getElementById(id).classList.remove('hidden');
}