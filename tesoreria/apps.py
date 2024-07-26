from django.apps import AppConfig


class TesoreriaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tesoreria'

class TesoreriaConfig(AppConfig):
    name = 'tesoreria'

    def ready(self):
        import tesoreria.signals