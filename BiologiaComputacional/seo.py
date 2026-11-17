from django.contrib.sitemaps import Sitemap
from django.http import HttpResponse
from django.urls import reverse


class PaginasPublicasSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.7

    def items(self):
        return (
            'inicio',
            'buscarProfesional',
            'investigacion',
            'servicios',
            'database',
            'contactos',
            'politicas_privacidad',
        )

    def location(self, item):
        return reverse(item)


def robots_txt(request):
    sitemap_url = request.build_absolute_uri(reverse('sitemap'))
    contenido = (
        'User-agent: *\n'
        'Allow: /\n'
        'Disallow: /admin/\n'
        'Disallow: /identity/\n'
        f'Sitemap: {sitemap_url}\n'
    )
    return HttpResponse(contenido, content_type='text/plain; charset=utf-8')
