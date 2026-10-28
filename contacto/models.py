from django.db import models

# El listado del panel muestra un recorte; el detalle conserva el texto entero.
LARGO_EXTRACTO = 80


class MensajeContacto(models.Model):
    """Copia de un envío del formulario público, para leerla en el panel."""

    nombres = models.CharField('Nombres', max_length=255)
    apellidos = models.CharField('Apellidos', max_length=255)
    email = models.EmailField('Correo')
    telefono = models.CharField('Teléfono', max_length=10)
    opiniones = models.TextField('Mensaje')
    creado = models.DateTimeField('Fecha', auto_now_add=True, db_index=True)
    leido = models.BooleanField('Leído', default=False)

    class Meta:
        verbose_name = 'Mensaje de contacto'
        verbose_name_plural = 'Mensajes de contacto'
        ordering = ['-creado']

    def __str__(self):
        return self.nombre_completo or self.email

    @property
    def nombre_completo(self):
        return f'{self.nombres} {self.apellidos}'.strip()

    @property
    def extracto(self):
        texto = ' '.join((self.opiniones or '').split())
        if len(texto) <= LARGO_EXTRACTO:
            return texto
        return texto[:LARGO_EXTRACTO - 1].rstrip() + '…'

    def marcar_leido(self):
        """Abrir el detalle es la lectura. No reescribe si ya estaba leído."""
        if self.leido:
            return
        self.leido = True
        self.save(update_fields=['leido'])
