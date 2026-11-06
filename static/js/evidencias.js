
document.addEventListener("DOMContentLoaded", function () {

    // =========================================================
    // 1. FORMULARIO DE EVIDENCIAS
    // =========================================================

    const form = document.getElementById("formEvidencias");

    if (form) {
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
    }


    // =========================================================
    // 2. VISOR EXCLUSIVO DE EVIDENCIAS
    // =========================================================

    const modalElement = document.getElementById("evidenciaPreviewModal");

    if (!modalElement) return;

    const previewTitle = document.getElementById("evidenciaPreviewTitle");
    const previewFrame = document.getElementById("evidenciaPreviewFrame");
    const previewImage = document.getElementById("evidenciaPreviewImage");
    const previewLoading = document.getElementById("evidenciaPreviewLoading");

    if (!previewFrame || !previewImage) return;

    function limpiarVisor() {

        previewFrame.onload = null;
        previewImage.onload = null;
        previewImage.onerror = null;

        previewFrame.removeAttribute("src");
        previewFrame.classList.add("d-none");

        previewImage.removeAttribute("src");
        previewImage.classList.add("d-none");

        if (previewLoading) {
            previewLoading.classList.add("d-none");
        }
    }

    // Evento delegado compatible con HTMX
    document.addEventListener("click", function (event) {

        const boton = event.target.closest(".js-preview-evidencia");

        if (!boton) return;

        event.preventDefault();
        event.stopPropagation();

        const url = boton.dataset.url;
        const nombre = boton.dataset.nombre || "Evidencia";

        if (!url) {
            Swal.fire({
                icon: "warning",
                title: "Documento no disponible",
                text: "La evidencia no tiene un archivo asociado."
            });
            return;
        }

        limpiarVisor();

        const nombreArchivo = nombre.split(/[\\/]/).pop();

        if (previewTitle) {
            previewTitle.textContent = nombreArchivo;
        }

        if (previewLoading) {
            previewLoading.classList.remove("d-none");
        }

        const esImagen = /\.(png|jpg|jpeg)$/i.test(
            nombreArchivo
        );

        if (esImagen) {

            previewImage.onload = function () {

                if (previewLoading) {
                    previewLoading.classList.add("d-none");
                }

                previewImage.classList.remove("d-none");
            };

            previewImage.onerror = function () {

                if (previewLoading) {
                    previewLoading.classList.add("d-none");
                }

                Swal.fire({
                    icon: "error",
                    title: "Error",
                    text: "No se pudo cargar la imagen."
                });
            };

            previewImage.src = url;

        } else {

            previewFrame.onload = function () {

                if (previewLoading) {
                    previewLoading.classList.add("d-none");
                }
            };

            previewFrame.src = url;
            previewFrame.classList.remove("d-none");
        }

        const modal = bootstrap.Modal.getOrCreateInstance(
            modalElement
        );

        modal.show();
    });


    // =========================================================
    // 3. CIERRE Y LIMPIEZA DEL MODAL
    // =========================================================

    modalElement.addEventListener("hide.bs.modal", function () {

        const elementoActivo = document.activeElement;

        if (
            elementoActivo &&
            modalElement.contains(elementoActivo)
        ) {
            elementoActivo.blur();
        }
    });

    modalElement.addEventListener("hidden.bs.modal", function () {
        limpiarVisor();
    });

});
