from django.views.generic import TemplateView
from servicios.models import Categoria, Servicio
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.http import request
from BiologiaComputacional.forms import ServicioForm
import os
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from BiologiaComputacional.permissions import is_staff_or_superuser, staff_required
from paginas.contenido import contexto_publico


def contexto_herramientas(request):
    """Listado de herramientas. Cada registro sigue en el modelo Servicio."""
    query = None if request is None else request.GET.get('q')
    herramientas = Servicio.objects.filter(
        categoria__nombre_categoria='Herramienta')
    form_submitted = False

    if query:
        herramientas = herramientas.filter(Q(nombre__icontains=query))
        cantidad_herramientas_buscadas = herramientas.count()
        form_submitted = True
    else:
        cantidad_herramientas_buscadas = herramientas.count()

    return {
        'cantidad_db': Servicio.objects.filter(
            categoria__nombre_categoria='Base de Datos').count(),
        'herramientas': herramientas,
        'cantidad_herramientas': Servicio.objects.filter(
            categoria__nombre_categoria='Herramienta').count(),
        'cantidad_herramientas_buscadas': cantidad_herramientas_buscadas,
        'form_submitted': form_submitted,
    }


def contexto_bases(request):
    """Listado de bases de datos. Cada registro sigue en el modelo Servicio."""
    query = None if request is None else request.GET.get('q')
    db = Servicio.objects.filter(categoria__nombre_categoria='Base de Datos')
    form_submitted = False

    if query:
        db = db.filter(Q(nombre__icontains=query))
        cantidad_db_buscadas = db.count()
        form_submitted = True
    else:
        cantidad_db_buscadas = db.count()

    return {
        'db': db,
        'cantidad_db': Servicio.objects.filter(
            categoria__nombre_categoria='Base de Datos').count(),
        'cantidad_herramientas': Servicio.objects.filter(
            categoria__nombre_categoria='Herramienta').count(),
        'cantidad_db_buscadas': cantidad_db_buscadas,
        'form_submitted': form_submitted,
    }


class herramientas_view(TemplateView):
    template_name = "servicios/herramientas.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(contexto_publico('servicios', self.request))
        return context


class bases_de_datos_view(TemplateView):
    template_name = "servicios/bases_de_datos.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(contexto_publico('bases-de-datos', self.request))
        return context


# Vista para mostrar la informacion de las herramientas o bases de datos

@method_decorator(login_required, name='dispatch')
class servicios_detalle_view(TemplateView):
    template_name = "servicios/servicios_detalle.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        servicio_nombre = kwargs.get('nombre')

        servicio = get_object_or_404(Servicio, nombre=servicio_nombre)

        servicios_herramienta = Servicio.objects.filter(
            categoria__nombre_categoria='Herramienta').exclude(nombre=servicio_nombre)

        servicios_db = Servicio.objects.filter(
            categoria__nombre_categoria='Base de Datos').exclude(nombre=servicio_nombre)

        context['servicios_herramienta'] = servicios_herramienta
        context['servicios_db'] = servicios_db
        context['servicio'] = servicio
        return context
    
    def post(self, request, nombre):
        # El GET sigue pidiendo solo login. Borrar exige staff, igual que editar.
        if not is_staff_or_superuser(request.user):
            raise PermissionDenied

        servicio = get_object_or_404(Servicio, nombre=nombre)
        servicio.delete()
        messages.success(request, 'Servicio eliminado correctamente')
        return redirect('servicios')

# Vista para editar la informacion de las herramientas o bases de datos

@method_decorator(staff_required, name='dispatch')
class servicio_edit_view(TemplateView):
    template_name = "servicios/servicio_edit.html"
    
    def get(self, request, nombre):
        servicio = get_object_or_404(Servicio, nombre=nombre)
        form = ServicioForm(instance=servicio)
        categorias = Categoria.objects.all()

        context = {
            'servicio': servicio,
            'form': form,
            'categorias': categorias
        }

        return render(request, self.template_name, context)
    
    def post(self, request, nombre):
        servicio = get_object_or_404(Servicio, nombre=nombre)
        form = ServicioForm(request.POST, request.FILES, instance=servicio)
        categorias = Categoria.objects.all()

        if 'delete_file' in request.POST:
            servicio.archivo.delete()
            servicio.archivo = None
            servicio.save()

        if form.is_valid():
            form.save()
            messages.success(
                request, 'Información actualizada correctamente')
            return redirect('servicios_detalle', servicio.nombre)
        else:
            context = {
                'servicio': servicio,
                'form': form,
                'categorias': categorias,
                'form_errors': form.errors
            }
            return render(request, self.template_name, context)
        
        
# Vista para agregar una herramienta o base de datos


@method_decorator(staff_required, name='dispatch')
class nuevo_servicio_view(TemplateView):
    template_name = "servicios/nuevo_servicio.html"

    def get(self, request):
        form = ServicioForm()
        categorias = Categoria.objects.all()
        
        context = {
            'form': form,
            'categorias': categorias
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request):
        form = ServicioForm(request.POST, request.FILES)
        categorias = Categoria.objects.all()
        
        if form.is_valid():
            servicio = form.save(commit=False)
            servicio.save()
            messages.success(request, 'Servicio agregado correctamente')
            
            return redirect('servicios_detalle', servicio.nombre)
        
        else:
            context = {
                'form': form,
                'form_errors': form.errors,
                'categorias': categorias
            }
            
            return render(request, self.template_name, context)
        