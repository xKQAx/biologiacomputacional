from django.shortcuts import render, HttpResponse
from django.views.generic import TemplateView

from paginas.contenido import contexto_publico


def inicio(request):
    return render(request, "inicio.html", contexto_publico())

def mi_vista_404(request, exception):
    return render(request, '404.html', status=404)

def view_403(request, exception=None):
    return render(request, '403.html', status=403)

class politicas_privacidad(TemplateView):
    
    template_name = "politicas_privacidad.html"