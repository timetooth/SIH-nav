from django.urls import path
from . import views

urlpatterns = [
    path('',views.default_view,name='default_view'),
    path('dummy/',views.get_dummy,name='default_view'),
]