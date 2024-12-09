from rest_framework.decorators import api_view
from rest_framework import status
from django.shortcuts import render
from django.http import JsonResponse
from . import utils
import requests

@api_view(['GET'])
def default_view(request):
    """ Get A Dummy Route """   
    db = utils.get_db()
    data = db.child("Incidents").get().val()
    return JsonResponse(data)

@api_view(['GET'])
def get_route(request,incident_id):
    if incident_id is None:
        err = {'error': 'incident_id is required as a path parameter'}
        return JsonResponse(err, status=status.HTTP_400_BAD_REQUEST)
    base_url = utils.get_nodeurl()
    incident = requests.get(f'{base_url}/api/incident/{incident_id}')
    if incident.status_code != 200:
        err = {'error': 'incident not found'}
        return JsonResponse(err, status=status.HTTP_400_BAD_REQUEST)
    building_id = incident.json()['incident']['buildingId']
    nodes = requests.get(f'{base_url}/api/building/{building_id}/node')
    if nodes.status_code != 200:
        err = {'error': 'Error fetching nodes accociated with specified incident'}
        return JsonResponse(err, status=status.HTTP_400_BAD_REQUEST)
    all_nodes = nodes.json()['nodes']
    return JsonResponse({"nodes":nodes.json()['nodes']}, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_dummy(request):
    user_id = request.GET.get('user_id', None)
    incident_id = request.GET.get('incident_id', None)
    if user_id is None or incident_id is None:
        err = {'error': 'user_id and incident_id is required as querry params'}
        return JsonResponse(err, status=status.HTTP_400_BAD_REQUEST)
    db = utils.get_db()
    path = {'1':True,'2':True,'3':True,'4':True,'5':True,'6':True,'7':True,'8':True,'9':True}
    db.child('Incidents').child(incident_id).child('UserRoutes').child(user_id).set(path)
    return JsonResponse({'message':f'Dummy Route Created for user {user_id}'}, status=status.HTTP_200_OK)