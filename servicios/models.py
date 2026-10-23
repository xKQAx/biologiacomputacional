from django.core.validators import FileExtensionValidator
from django.db import models

# Create your models here.

class Categoria(models.Model):
    nombre_categoria = models.CharField(max_length=20, blank=False)
    
    def __str__(self):
        return 'Categoria de servicios %s' % (self.nombre_categoria)
    
class Servicio(models.Model):
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100, unique=True)
    descrip = models.TextField(blank=False)
    imagen_servicio = models.ImageField(upload_to='servicios-imagenes/', blank=True)
    # La ficha ya anuncia ZIP o RAR. El modelo lo exige para que el admin no acepte otro tipo.
    archivo = models.FileField(
        upload_to='archivos/',
        blank=True,
        validators=[FileExtensionValidator(
            allowed_extensions=['zip', 'rar'],
            message='Solo se permiten archivos ZIP o RAR.',
        )],
    )
    video_enlace = models.URLField(blank=True)
    desarrollador = models.CharField(max_length=100, blank=False)
    desarrollador_enlace = models.URLField(blank=True)
    nombre_licencia = models.CharField(max_length=100, blank=False)
    nombre_licencia_enlace = models.URLField(blank=True)
    
    def __str__(self):
        if self.categoria.nombre_categoria == 'Herramienta':
            return 'Herramienta %s' % self.nombre
        elif self.categoria.nombre_categoria == 'Base de Datos':
            return 'Base de datos %s' % self.nombre
        else:
            return self.nombre