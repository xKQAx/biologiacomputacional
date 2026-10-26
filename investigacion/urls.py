from django.urls import path
from investigacion.views import investigacion_view
from investigacion import views

urlpatterns = [
    path('', investigacion_view.as_view(), name='investigacion'),
    path('editar-carrusel', views.InvestigacionCarruselEditView.as_view(), name="investigacion_editar_carrusel"),
    path('carrusel/vista-previa/', views.CarruselVistaPreviaView.as_view(), name="investigacion_carrusel_vista_previa"),
    path('carrusel/publicar/', views.CarruselPublicarView.as_view(), name="investigacion_carrusel_publicar"),
    path('carrusel/descartar/', views.CarruselDescartarView.as_view(), name="investigacion_carrusel_descartar"),
    path('<str:nombre>/editar/', views.InvestigacionEditView.as_view(), name="investigacion_editar"),
    path('<str:nombre>/eliminar/', views.InvestigacionEliminarView.as_view(), name="investigacion_eliminar"),
    path('nueva-investigacion/', views.InvestigacionCreateView.as_view(), name="investigacion_crear")
] 