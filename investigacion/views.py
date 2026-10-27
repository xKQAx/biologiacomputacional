from django.views.generic import TemplateView
from investigacion.models import CategoriaI, Investigacion
from investigacion.carrusel import (
    borrador_actual,
    descartar_borrador,
    diapositivas_publicas,
    guardar_borrador,
    publicar_borrador,
    publicado_actual,
    url_imagen,
    CAMPOS_IMAGEN,
)
from investigacion.forms import CarruselBorradorForm, filas_del_formulario
from django.utils.decorators import method_decorator
from django.shortcuts import render, get_object_or_404, redirect
from BiologiaComputacional.forms import InvestigacionForm
from BiologiaComputacional.permissions import staff_required
from django.contrib import messages
from django.views import View
from paginas.contenido import contexto_publico


def contexto_pagina(request=None):
    """Datos del listado. El carrusel aquí es el publicado; su borrador tiene otra pantalla."""
    carrusel = publicado_actual()
    return {
        'categorias': CategoriaI.objects.all(),
        'carrusel': carrusel,
        'diapositivas': diapositivas_publicas(carrusel),
    }


class investigacion_view(TemplateView):
    template_name = "investigacion/investigacion.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(contexto_publico('investigacion', self.request))
        return context


def _contexto_borrador(form, borrador, publicado):
    urls = {
        campo: url_imagen(borrador, publicado, campo)
        for campo in CAMPOS_IMAGEN
    }
    return {
        'form': form,
        'filas': filas_del_formulario(form, urls),
        'hay_borrador': borrador is not None,
    }


def _responder_publicar(request):
    borrador = borrador_actual()
    if borrador is None:
        messages.error(request, 'No hay un borrador para publicar.')
        return redirect('investigacion_editar_carrusel')
    try:
        publicar_borrador(borrador)
    except ValueError:
        messages.error(
            request,
            'No se pudo publicar: el borrador no tiene todas las imágenes.',
        )
        return redirect('investigacion_editar_carrusel')
    messages.success(
        request,
        'Carrusel publicado. Los visitantes ya ven estos cambios.',
    )
    return redirect('investigacion')


def _formulario_inicial(borrador, publicado):
    fuente = borrador or publicado
    initial = {}
    if fuente is not None:
        initial = {
            'titulo': fuente.titulo,
            'texto1': fuente.texto1,
            'texto2': fuente.texto2,
            'texto3': fuente.texto3,
        }
    return CarruselBorradorForm(
        initial=initial,
        borrador=borrador,
        publicado=publicado,
    )


# El staff edita un borrador. Publicar es otro paso.

@method_decorator(staff_required, name='dispatch')
class InvestigacionCarruselEditView(View):
    template_name = "investigacion/investigacion_edit_carrusel.html"

    def get(self, request):
        borrador = borrador_actual()
        publicado = publicado_actual()
        form = _formulario_inicial(borrador, publicado)
        return render(
            request,
            self.template_name,
            _contexto_borrador(form, borrador, publicado),
        )

    def post(self, request):
        borrador = borrador_actual()
        publicado = publicado_actual()
        form = CarruselBorradorForm(
            request.POST,
            request.FILES,
            borrador=borrador,
            publicado=publicado,
        )
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                _contexto_borrador(form, borrador, publicado),
            )

        try:
            borrador = guardar_borrador(form.cleaned_data, borrador, publicado)
        except ValueError:
            form.add_error(None, 'Falta una imagen. Sube las tres diapositivas.')
            return render(
                request,
                self.template_name,
                _contexto_borrador(form, borrador_actual(), publicado),
            )

        accion = request.POST.get('accion')
        if accion == 'previsualizar':
            return redirect('investigacion_carrusel_vista_previa')
        if accion == 'publicar':
            return _responder_publicar(request)

        messages.success(
            request,
            'Borrador guardado. Los visitantes todavía ven la versión publicada.',
        )
        return redirect('investigacion_editar_carrusel')


@method_decorator(staff_required, name='dispatch')
class CarruselVistaPreviaView(View):
    """La misma plantilla pública, con el borrador en el carrusel."""

    def get(self, request):
        borrador = borrador_actual()
        if borrador is None:
            messages.info(request, 'No hay un borrador para previsualizar.')
            return redirect('investigacion_editar_carrusel')

        contexto = contexto_publico('investigacion', request)
        contexto['diapositivas'] = diapositivas_publicas(borrador)
        contexto['es_vista_previa'] = True
        response = render(request, 'investigacion/investigacion.html', contexto)
        response['X-Robots-Tag'] = 'noindex, nofollow'
        response['Cache-Control'] = 'private, no-store'
        return response


@method_decorator(staff_required, name='dispatch')
class CarruselPublicarView(View):
    http_method_names = ['post']

    def post(self, request):
        return _responder_publicar(request)


@method_decorator(staff_required, name='dispatch')
class CarruselDescartarView(View):
    http_method_names = ['post']

    def post(self, request):
        borrador = borrador_actual()
        if borrador is None:
            messages.info(request, 'No había un borrador que descartar.')
        else:
            descartar_borrador(borrador)
            messages.success(
                request,
                'Borrador descartado. Lo publicado no cambió.',
            )
        return redirect('investigacion_editar_carrusel')


# Vista para editar informacion de las investigaciones


@method_decorator(staff_required, name='dispatch')
class InvestigacionEditView(TemplateView):
    template_name = "investigacion/investigacion_edit.html"

    def get(self, request, nombre):
        investigacion = get_object_or_404(Investigacion, nombre=nombre)
        form = InvestigacionForm(instance=investigacion)
        categorias = CategoriaI.objects.all()

        context = {
            'investigacion': investigacion,
            'form': form,
            'categorias': categorias
        }

        return render(request, self.template_name, context)

    def post(self, request, nombre):
        investigacion = get_object_or_404(Investigacion, nombre=nombre)
        form = InvestigacionForm(
            request.POST, request.FILES, instance=investigacion)
        categorias = CategoriaI.objects.all()

        if 'delete_file_imagen_tif' in request.POST:
            investigacion.imagen_tif.delete()
            investigacion.imagen_tif = None
            investigacion.save()

        if 'delete_file_pdf' in request.POST:
            investigacion.pdf.delete()
            investigacion.pdf = None
            investigacion.save()

        if 'delete_file_mejores' in request.POST:
            investigacion.mejores_pdf.delete()
            investigacion.mejores_pdf = None
            investigacion.save()

        if 'delete_file_imagen_extra1' in request.POST:
            investigacion.imagen_extra_1.delete()
            investigacion.imagen_extra_1 = None
            investigacion.save()

        if 'delete_file_imagen_extra2' in request.POST:
            investigacion.imagen_extra_2.delete()
            investigacion.imagen_extra_2 = None
            investigacion.save()

        if 'delete_file_imagen_extra3' in request.POST:
            investigacion.imagen_extra_3.delete()
            investigacion.imagen_extra_3 = None
            investigacion.save()

        if form.is_valid():
            form.save()
            messages.success(
                request, 'Información actualizada correctamente')
            return redirect('investigacion')
        else:
            context = {
                'investigacion': investigacion,
                'form': form,
                'categorias': categorias,
                'form_errors': form.errors
            }
            return render(request, self.template_name, context)


# Vista para eliminar una investigacion


@method_decorator(staff_required, name='dispatch')
class InvestigacionEliminarView(View):
    def post(self, request, nombre):
        investigacion = get_object_or_404(Investigacion, nombre=nombre)
        investigacion.delete()
        messages.success(
            request, 'La investigación ha sido eliminada correctamente')
        return redirect('investigacion')

# Vista para agregar una nueva investigacion


@method_decorator(staff_required, name='dispatch')
class InvestigacionCreateView(TemplateView):
    template_name = "investigacion/investigacion_create.html"

    def get(self, request):
        form = InvestigacionForm()
        categorias = CategoriaI.objects.all()

        context = {
            'form': form,
            'categorias': categorias
        }

        return render(request, self.template_name, context)

    def post(self, request):
        form = InvestigacionForm(request.POST, request.FILES)
        categorias = CategoriaI.objects.all()

        if form.is_valid():
            form.save()
            messages.success(request, 'Investigación creada correctamente')
            return redirect('investigacion')
        else:
            context = {
                'form': form,
                'categorias': categorias,
                'form_errors': form.errors
            }
            return render(request, self.template_name, context)
