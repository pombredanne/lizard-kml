from django.core.urlresolvers import reverse
from django.conf import settings

from djangorestframework.views import View

from lizard_kml.models import Category

DEFAULT_PREVIEW_IMAGE = settings.STATIC_URL + 'lizard_kml/figures/none.png'

class CategoryTreeView(View):
    _IGNORE_IE_ACCEPT_HEADER = False # keep this for IE8 and IE9

    def get(self, request):
        categories = [
            {
                'id': category.id,
                'name': category.name,
                'description': category.description,
                'collapsed_by_default': category.collapsed_by_default,
                'kml_resources': self._kml_resource_tree(category)
            }
            for category in Category.objects.all()
        ]
        return {'categories': categories}

    def _kml_resource_tree(self, category):
        return [
            {
                'id': k.id,
                'name': k.name,
                'description': k.description,
                'kml_type': k.kml_type,
                'kml_url': self._mk_kml_resource_url(k),
                'slug': k.slug,
                'preview_image_url': k.preview_image.url if k.preview_image else DEFAULT_PREVIEW_IMAGE
            }
            for k in category.kmlresource_set.all()
        ]

    def _mk_kml_resource_url(self, kml_resource):
        if kml_resource.slug == 'jarkus':
            rela = reverse('lizard-jarkus-kml', kwargs={'kml_type': 'lod'})
        else:
            rela = reverse('lizard-kml-kml', kwargs={'kml_resource_id': kml_resource.pk})
        return self.request.build_absolute_uri(rela)
