from django.conf import settings
from django.db import models


class BloquePortada(models.Model):
    """Texto de un bloque de una página pública, publicado o en borrador.

    El visitante solo lee lo publicado de esa página. El editor lee su borrador.
    """

    class Estado(models.TextChoices):
        PUBLICADO = 'publicado', 'Publicado'
        BORRADOR = 'borrador', 'Borrador'

    pagina = models.SlugField(max_length=40, default='inicio')
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
                fields=['pagina', 'clave', 'estado'],
                name='paginas_bloque_pagina_clave_estado',
            ),
        ]
        ordering = ['orden', 'clave']

    def __str__(self):
        return f'{self.pagina}:{self.clave} ({self.estado})'


class HistorialPagina(models.Model):
    """Copia de lo publicado. Restaurar la escribe en el borrador, no en la página pública."""

    pagina = models.SlugField(max_length=40)
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )
    fecha = models.DateTimeField(auto_now_add=True)
    contenido = models.JSONField()

    class Meta:
        verbose_name = 'publicación de una página'
        verbose_name_plural = 'publicaciones de páginas'
        ordering = ['-fecha', '-pk']

    def __str__(self):
        return f'{self.pagina} ({self.fecha:%Y-%m-%d %H:%M})'
