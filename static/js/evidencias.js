// static/js/evidencias.js

document.addEventListener("DOMContentLoaded", function () {

    const filtro = document.getElementById(
        "filtroCategoriaEvidencia"
    );

    const filas = document.querySelectorAll(
        "#tablaEvidencias tr[data-categoria]"
    );

    const sinResultados = document.querySelector(
        ".js-evidencias-sin-resultados"
    );

    if (filtro) {
        filtro.addEventListener("change", function () {

            const categoria = this.value;
            let visibles = 0;

            filas.forEach(function (fila) {

                const mostrar = (
                    !categoria ||
                    fila.dataset.categoria === categoria
                );

                fila.classList.toggle("d-none", !mostrar);

                if (mostrar) visibles++;
            });

            if (sinResultados) {
                sinResultados.classList.toggle(
                    "d-none",
                    visibles > 0 || filas.length === 0
                );
            }
        });
    }


    // Formulario de evidencias

    const form = document.getElementById("formEvidencias");

    if (!form) return;

    const input = form.querySelector('input[type="file"]');
    const resumen = document.getElementById("resumenEvidencias");
    const boton = document.getElementById("btnGuardarEvidencia");

    if (input && resumen) {
        input.addEventListener("change", function () {

            const archivo = this.files[0];
            resumen.replaceChildren();

            const titulo = document.createElement("span");
            titulo.className = "sv-empty-title d-block";

            if (!archivo) {
                titulo.textContent = "Ningún archivo seleccionado";
            } else {
                titulo.textContent = archivo.name;

                const detalle = document.createElement("span");
                detalle.className = "sv-empty-text d-block mt-2";

                detalle.textContent = (
                    archivo.size / 1024 / 1024
                ).toFixed(2) + " MB";

                resumen.appendChild(detalle);
            }

            resumen.prepend(titulo);
        });
    }

    form.addEventListener("submit", function (event) {

        if (!form.reportValidity()) {
            event.preventDefault();
            return;
        }

        if (form.dataset.enviando === "true") {
            event.preventDefault();
            return;
        }

        form.dataset.enviando = "true";

        if (boton) {
            boton.disabled = true;
            boton.innerHTML = `
                <span class="spinner-border spinner-border-sm me-2"
                      role="status"
                      aria-hidden="true"></span>
                Guardando...
            `;
        }
    });

});