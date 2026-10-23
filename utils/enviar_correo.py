import mimetypes
import os

from email.mime.image import MIMEImage

from django.conf import settings
from django.core.mail import EmailMessage, get_connection


def normalizar_correos(correos):
    if not correos:
        return []

    if isinstance(correos, str):
        return [
            correo.strip()
            for correo in correos.split(",")
            if correo.strip()
        ]

    return list(correos)


def obtener_conexion_correo(es_savia_negro):
    if es_savia_negro:
        conexion = get_connection(
            backend="django.core.mail.backends.smtp.EmailBackend",
            host=settings.YEROD_EMAIL_HOST,
            port=settings.YEROD_EMAIL_PORT,
            username=settings.YEROD_EMAIL_HOST_USER,
            password=settings.YEROD_EMAIL_HOST_PASSWORD,
            use_tls=settings.YEROD_EMAIL_USE_TLS,
            use_ssl=settings.YEROD_EMAIL_USE_SSL,
            timeout=20,
            fail_silently=False,
        )

        from_email = settings.YEROD_FROM_EMAIL

    else:
        conexion = get_connection(
            backend="django.core.mail.backends.smtp.EmailBackend",
            host=settings.EMAIL_HOST,
            port=settings.EMAIL_PORT,
            username=settings.EMAIL_HOST_USER,
            password=settings.EMAIL_HOST_PASSWORD,
            use_tls=settings.EMAIL_USE_TLS,
            use_ssl=settings.EMAIL_USE_SSL,
            timeout=20,
            fail_silently=False,
        )

        from_email = settings.DEFAULT_FROM_EMAIL

    return conexion, from_email


def adjuntar_imagen_inline(
    email,
    content_id,
    ruta_imagen,
):
    if not os.path.isfile(ruta_imagen):
        raise FileNotFoundError(
            f"No se encontró la imagen: {ruta_imagen}"
        )

    mime_type, _ = mimetypes.guess_type(
        ruta_imagen
    )

    subtipo = (
        mime_type.split("/")[-1]
        if mime_type
        else "png"
    )

    with open(ruta_imagen, "rb") as archivo:
        imagen = MIMEImage(
            archivo.read(),
            _subtype=subtipo,
        )

    imagen.add_header(
        "Content-ID",
        f"<{content_id}>",
    )

    imagen.add_header(
        "X-Attachment-Id",
        content_id,
    )

    imagen.add_header(
        "Content-Disposition",
        "inline",
        filename=os.path.basename(ruta_imagen),
    )

    email.attach(imagen)


def enviar_correo_savia(
    *,
    asunto,
    html_message,
    destinatarios,
    es_savia_negro=False,
    bcc=None,
    cc=None,
    reply_to=None,
    imagenes_inline=None,
    adjuntos=None,
):
    conexion, from_email = obtener_conexion_correo(
        es_savia_negro
    )

    email = EmailMessage(
        subject=asunto,
        body=html_message,
        from_email=from_email,
        to=normalizar_correos(destinatarios),
        cc=normalizar_correos(cc),
        bcc=normalizar_correos(bcc),
        reply_to=normalizar_correos(reply_to),
        connection=conexion,
    )

    email.content_subtype = "html"

    if imagenes_inline:
        email.mixed_subtype = "related"

        for content_id, ruta_imagen in imagenes_inline:
            adjuntar_imagen_inline(
                email=email,
                content_id=content_id,
                ruta_imagen=ruta_imagen,
            )

    for adjunto in adjuntos or []:
        if isinstance(adjunto, (str, os.PathLike)):
            email.attach_file(str(adjunto))

        elif isinstance(adjunto, tuple):
            email.attach(*adjunto)

        else:
            email.attach(adjunto)

    return email.send()