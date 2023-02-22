from . import models

from django.contrib import admin
from django.db.models import Model

import inspect

for name, value in inspect.getmembers(models):
    if getattr(value, '__module__', None) != '{app_name}.models': continue
    if not issubclass(value, Model): continue
    admin.site.register(value)
