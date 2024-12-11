from django.urls import path
from . import views

urlpatterns = [
    path('',views.default_view,name='default_view'),
    path('dummy/',views.get_dummy,name='default_view'),
    path('get_route/',views.get_route,name='normal_route'),
    path('route_nearest/',views.route_nearest,name='nearest_route'),
    path('route_user/',views.route_user,name='route_user'),
    path('route_all/',views.reroute,name='route_all'),
    path('fire_intensity/',views.set_fire_intensity,name='set_intensity'),
]