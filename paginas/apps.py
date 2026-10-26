from django.apps import AppConfig


class PaginasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'paginas'
    verbose_name = 'Páginas'

    def ready(self):
        # El admin importa este módulo al arrancar; la bandera evita registrar dos veces.
        from paginas.admin import registrar_rutas
        registrar_rutas()
