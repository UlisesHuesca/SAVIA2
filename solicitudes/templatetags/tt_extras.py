from django import template

register = template.Library()

@register.simple_tag
def my_url(value, field_name, urlencode=None):
    url = '?{}={}'.format(field_name,value)

    if urlencode:
        querystring = urlencode.split('&')
        filtered_querystring = filter(lambda p: p.split('=')[0]!=field_name,querystring)
        encoded_querystring = '&'.join(filtered_querystring)
        url ='{}&{}'.format(url,encoded_querystring)

    return url

@register.filter(name='multiply')
def multiply(value, arg):
    try:
        return value * arg
    except (TypeError, ValueError):
        return value  # Retorna el valor original si hay algún error en la multiplicación
    

#@register.filter
#def get_item(dictionary, key):
#    """Permite acceder a valores de un dict en los templates"""
#    if dictionary and key in dictionary:
#        return dictionary.get(key)
#    return None

@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Permite acceder a la clave de un diccionario usando una variable en las plantillas de Django.
    Uso: {{ mi_diccionario|get_item:mi_variable_de_clave }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None # O puedes retornar '' o 0 si prefieres