from . import models

from django.contrib import auth
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt

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
