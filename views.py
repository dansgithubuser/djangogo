from . import models

from rest_framework import serializers, viewsets

from django.contrib import auth
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt

import inspect
import json

@csrf_exempt
def signup(request):
    status = None
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = auth.authenticate(username=username, password=raw_password)
            auth.login(request, user)
            return redirect('/')
        else:
            status = 400
    else:
        form = UserCreationForm()
    return render(request, 'signup.html', {'form': form}, status=status)

def login_json(request):
    params = json.loads(request.body.decode())
    user = auth.authenticate(
        username=params['username'],
        password=params['password'],
    )
    if user:
        auth.login(request, user)
        return HttpResponse(status=200)
    else:
        return HttpResponse(status=400)

for name, model in inspect.getmembers(models):
    if getattr(model, '__module__', None) != '{app}.models': continue
    if not issubclass(model, models.models.Model): continue
    exec(f'''class {name}Serializer(serializers.ModelSerializer):
        class Meta:
            model = models.{name}
            fields = '__all__'
    ''')
    exec(f'''class {name}Viewset(viewsets.ModelViewSet):
        queryset = models.{name}.objects.all()
        serializer_class = {name}Serializer
    ''')
