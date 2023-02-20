from . import views

from django.urls import include, path

import inspect

urlpatterns = [
    path('accounts/', include('django.contrib.auth.urls')),
]

for name, value in inspect.getmembers(views):
    if getattr(value, '__module__', None) != '{app_name}.views': continue
    if name.startswith('_'): continue
    if inspect.isfunction(value):
        if hasattr(value, 'route'):
            route = value.route
        else:
            route = name
        urlpatterns.append(path(route, value))
