import base64
import os


def get_image_base64(image_path):
    """
    Convierte una imagen local a una cadena Base64.
    """

    if not os.path.isfile(image_path):
        raise FileNotFoundError(
            f"No se encontró la imagen para el correo: {image_path}"
        )

    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def obtener_tema_correo(static_path, es_savia_negro):
    """
    Devuelve colores y logotipos para los correos de SAVIA.

    SAVIA NEGRO:
        - Encabezado negro.
        - Acentos verdes.
        - Solamente el logo SAVIA verde.

    SAVIA normal:
        - Encabezado azul.
        - Logo Vordcab en el encabezado.
        - Logo SAVIA en el pie.
    """

    if es_savia_negro:
        logo_encabezado_path = os.path.join(
            static_path,
            "images",
            "SAVIA_Negro_Verde.jpg",
        )

        return {
            "es_savia_negro": True,
            "nombre_sistema": "SAVIA 2.1",
            "nombre_empresa": "YEROD",
            "color_encabezado": "#191919",
            "color_texto_encabezado": "#D0D5DD",
            "color_encabezado_tabla": "#29332E",
            "color_acento": "#288C45",
            "color_fondo_acento": "#EAF6EE",
            "logo_encabezado_mime": "image/jpeg",
            "logo_encabezado_base64": get_image_base64(
                logo_encabezado_path
            ),
            "logo_pie_base64": "",
        }

    logo_encabezado_path = os.path.join(
        static_path,
        "images",
        "logo_vordcab.jpg",
    )

    logo_pie_path = os.path.join(
        static_path,
        "images",
        "SAVIA_Logo.png",
    )

    return {
        "es_savia_negro": False,
        "nombre_sistema": "SAVIA 2.1",
        "nombre_empresa": "GRUPO VORDCAB S.A. DE C.V.",
        "color_encabezado": "#173F5F",
        "color_texto_encabezado": "#D0D5DD",
        "color_encabezado_tabla": "#173F5F",
        "color_acento": "#3E92CC",
        "color_fondo_acento": "#EAF4FA",
        "logo_encabezado_mime": "image/jpeg",
        "logo_encabezado_base64": get_image_base64(
            logo_encabezado_path
        ),
        "logo_pie_base64": get_image_base64(
            logo_pie_path
        ),
    }