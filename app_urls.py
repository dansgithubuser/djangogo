from . import views

from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import TemplateView

import inspect

urlpatterns = {urlpatterns}

for name, value in inspect.getmembers(views):
    if getattr(value, '__module__', None) != '{app}.views': continue
    if not inspect.isfunction(value): continue
    if name.startswith('_'): continue
    urlpatterns.append(path(name, value))
