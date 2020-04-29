from django.shortcuts import render

# Create your views here.
from django.shortcuts import render
from django.http import HttpResponse
from .models import Place

# Create your views here.
def list_places(request, *args, **kwargs):
    return render(request, 'list_places.html', {'places': Place.objects.all()})
