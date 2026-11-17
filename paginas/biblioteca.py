from django.contrib import admin, messages
from django.shortcuts import redirect, render

from paginas.forms import ImagenBibliotecaForm
from paginas.models import ImagenBiblioteca


def biblioteca_imagenes(request):
    """Carga y consulta imágenes reutilizables desde el panel del laboratorio."""
    formulario = ImagenBibliotecaForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and formulario.is_valid():
        imagen = formulario.save(commit=False)
        imagen.subida_por = request.user
        imagen.save()
        messages.success(request, 'La imagen quedó disponible en la biblioteca.')
        return redirect('admin:pagina_biblioteca_imagenes')

    consulta = request.GET.get('q', '').strip()
    imagenes = ImagenBiblioteca.objects.all()
    if consulta:
        imagenes = imagenes.filter(nombre__icontains=consulta)
    contexto = admin.site.each_context(request)
    contexto.update({
        'title': 'Biblioteca de imágenes',
        'formulario': formulario,
        'imagenes': imagenes,
        'consulta': consulta,
    })
    return render(request, 'admin/paginas/biblioteca_imagenes.html', contexto)
