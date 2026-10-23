from django.contrib import admin
from identity.models import ProfileAdditionalInfo

# AdditionalUserInfo es el perfil legado: la web no lo lee.
admin.site.register(ProfileAdditionalInfo)