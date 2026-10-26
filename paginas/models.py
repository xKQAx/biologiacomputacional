from django.db import models


class BloquePortada(models.Model):
    """Texto de un bloque de la portada, publicado o en borrador.

    La portada pública solo lee lo publicado. El editor lee el borrador.
    """

    class Estado(models.TextChoices):
        PUBLICADO = 'publicado', 'Publicado'
        BORRADOR = 'borrador', 'Borrador'

    clave = models.SlugField(max_length=80)
    texto = models.TextField(blank=True)
    enlace = models.CharField(max_length=500, blank=True)
    orden = models.PositiveIntegerField(default=0)
    estado = models.CharField(max_length=20, choices=Estado.choices)

    class Meta:
        verbose_name = 'bloque de la portada'
        verbose_name_plural = 'bloques de la portada'
        constraints = [
            models.UniqueConstraint(
                fields=['clave', 'estado'],
                name='paginas_bloque_clave_estado',
            ),
        ]
        ordering = ['orden', 'clave']

    def __str__(self):
        return f'{self.clave} ({self.estado})'
