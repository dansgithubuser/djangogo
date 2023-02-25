from . import models

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods

import json

@login_required
def home(request):
    return render(request, 'home.html')
home.route = ''
