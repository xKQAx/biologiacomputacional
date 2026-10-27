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
