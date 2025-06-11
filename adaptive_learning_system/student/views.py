from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .decorators import student_required


@login_required
@student_required
def index(request):
    return render(request, 'student/index.html')
