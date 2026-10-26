from django.core.validators import FileExtensionValidator
from django.db import models

# El formulario público ya limita estos campos a PDF. El admin usa el mismo modelo.
_PDF = FileExtensionValidator(
    allowed_extensions=['pdf'],
    message='Solo se permiten archivos PDF.',
)

# Create your models here.

class Carrusel(models.Model):
    titulo = models.CharField(max_length=50, blank=True)
    texto1 = models.CharField(max_length=100, blank=False)
    texto2 = models.CharField(max_length=100, blank=False)
    texto3 = models.CharField(max_length=100, blank=False)
    imagen1 = models.ImageField(upload_to='imagen-carrusel-1/', blank=False)
    imagen2 = models.ImageField(upload_to='imagen-carrusel-2/', blank=False)
    imagen3 = models.ImageField(upload_to='imagen-carrusel-3/', blank=False)
    
    def __str__(self):
        return 'Datos carrusel de fotos'


class CarruselBorrador(models.Model):
    """Copia editable del carrusel. La portada no lee este modelo.

    El siguiente paso del panel es crear secciones nuevas; este borrador
    solo cubre el carrusel que ya existe.
    """

    titulo = models.CharField(max_length=50, blank=True)
    texto1 = models.CharField(max_length=100)
    texto2 = models.CharField(max_length=100)
    texto3 = models.CharField(max_length=100)
    imagen1 = models.ImageField(upload_to='imagen-carrusel-borrador-1/', blank=True)
    imagen2 = models.ImageField(upload_to='imagen-carrusel-borrador-2/', blank=True)
    imagen3 = models.ImageField(upload_to='imagen-carrusel-borrador-3/', blank=True)

    class Meta:
        verbose_name = 'Borrador del carrusel'
        verbose_name_plural = 'Borrador del carrusel'

    def __str__(self):
        return 'Borrador del carrusel de investigación'


class CategoriaI(models.Model):
    nombre_categoria = models.CharField(max_length=20, blank=False)
    
    def __str__(self):
        return 'Categoria de investigacion %s' % (self.nombre_categoria)
    
class Investigacion(models.Model):
    categoria = models.ForeignKey(CategoriaI, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100, blank=False, unique=True)
    descrip = models.TextField(blank=False)
    imagen_investigacion = models.ImageField(upload_to='investigacion-imagenes/', blank=False)
    imagen_tif = models.ImageField(upload_to='investigacion-tif/', blank=True)
    pdf = models.FileField(upload_to='investigacion-pdf/', blank=True, validators=[_PDF])
    mejores_pdf = models.FileField(upload_to='investigacion-mejores/', blank=True, validators=[_PDF])
    imagen_extra_1 = models.ImageField(upload_to='investigacion-imagenes-extras1/', blank=True)
    imagen_extra_2 = models.ImageField(upload_to='investigacion-imagenes-extras2/', blank=True)
    imagen_extra_3 = models.ImageField(upload_to='investigacion-imagenes-extras3/', blank=True)

    def imagenes_extra(self):
        # Una sola serie: la plantilla no repite el mismo bloque tres veces.
        return (
            (1, self.imagen_extra_1),
            (2, self.imagen_extra_2),
            (3, self.imagen_extra_3),
        )

    def __str__(self):
        if self.categoria.nombre_categoria == 'Alpha':
            return 'PROYECTO ALPHA-SINUCLEINA %s' % self.nombre
        elif self.categoria.nombre_categoria == 'Cry11':
            return 'FAMILIA CRY11 %s' % self.nombre
        elif self.categoria.nombre_categoria == 'Otros':
            return 'Otros %s' % self.nombre
        else:
            return self.nombre