
def obtener_empresa_por_host(request):
    host = request.get_host().split(':')[0].lower()

    dominios_yerod = {
        'yerod.local',
        'yerod.cloud',
        'www.yerod.cloud',
    }

    dominios_vordcab = {
        'vordcab.local',
        'grupovordcab.cloud',
        'www.grupovordcab.cloud',
    }

    if host in dominios_yerod:
        return 'YEROD'

    if host in dominios_vordcab:
        return 'VORDCAB'

    return None