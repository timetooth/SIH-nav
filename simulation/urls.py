from django.urls import path
from . import views

urlpatterns = [
    path('start/', views.start_simulation),
    path('keyframe/', views.get_keyframe),
    path('default/', views.default_view),
]