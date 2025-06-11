from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .decorators import expert_required


@login_required
@expert_required
def index(request):
    return render(request, 'expert/index.html')
