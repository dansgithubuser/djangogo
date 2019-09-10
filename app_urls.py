from . import views

from rest_framework import routers, viewsets

from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.generic import TemplateView

import inspect

urlpatterns = [
    path('', TemplateView.as_view(template_name='home.html')),
    path('login', auth_views.LoginView.as_view(template_name='login.html')),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]

router = routers.DefaultRouter()

for name, value in inspect.getmembers(views):
    if getattr(value, '__module__', None) != '{app}.views': continue
    if name.startswith('_'): continue
    if inspect.isfunction(value):
        urlpatterns.append(path(name, value))
    elif issubclass(value, viewsets.GenericViewSet):
        if name.lower().endswith('viewset'):
            name = name[:-7]
        router.register(name.lower(), value)

urlpatterns.append(path('resource/', include(router.urls)))
