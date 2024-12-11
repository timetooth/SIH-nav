from rest_framework.decorators import api_view
from rest_framework import status
from django.shortcuts import render
from django.http import JsonResponse
from . import utils
from . import PathFinder
import requests
import json

cache = {}

@api_view(['GET'])
def default_view(request):
    """ Get A Dummy Route """   
    db = utils.get_db()
    data = db.child("Incidents").get().val()
    return JsonResponse(data)

@api_view(['GET'])
def get_route(request):
    """
    Get a path between two nodes in a building.

    Query Parameters:
    - building_id (str): The ID of the building to fetch the graph.
    - start_id (int): The ID of the start node.
    - goal_id (int): The ID of the goal node.

    Response:
    - 200: A dictionary containing the path as a series of node IDs.
        {"path": {"0": 101,"1": 102,"2": 103}}
    """
    building_id = request.query_params.get('building_id')
    start_id = int(request.query_params.get('start_id'))
    goal_id = int(request.query_params.get('goal_id'))
    if building_id is None or start_id is None or goal_id is None:
        err = {'error': 'building_id, start_id and goal_id are required as querry params'}
        return JsonResponse(err, status=status.HTTP_400_BAD_REQUEST)
    db = utils.get_db()
    base_url = utils.get_nodeurl()
    graph = PathFinder.get_graph(building_id,db)
    nodes, fire_extinguishers, medkits, exits = PathFinder.get_node_objs(graph,[],building_id)
    start = nodes[start_id]
    end = nodes[goal_id]
    path_nodes = PathFinder.astar(nodes,start,[end])
    path = {id: node.id for id, node in enumerate(path_nodes)}
    return JsonResponse({'path':path}, status=status.HTTP_200_OK)

@api_view(['GET'])
def route_nearest(request):
    """
    Get a path between two nodes in a building.

    Query Parameters:
    - building_id (str): The ID of the building to fetch the graph.
    - start_id (int): The ID of the start node.
    - goal_id (int): The ID of the goal node.

    Response:
    - 200: A dictionary containing the path as a series of node IDs.
        {"path": {"0": 101,"1": 102,"2": 103}}
    """
    incident_id = request.query_params.get('incident_id')
    start_id = int(request.query_params.get('start_id'))
    mode = request.query_params.get('mode','exit')

    modes = ['exit','extinguisher','medkit']

    if incident_id is None or start_id is None or mode is None:
        err = {'error': 'incident_id, start_id are required as querry params'}
        return JsonResponse(err, status=status.HTTP_400_BAD_REQUEST)
    if mode not in modes:
        err = {'error': "mode should be either 'exit', 'extinguisher' or 'medkit'"}
        return JsonResponse(err, status=status.HTTP_400_BAD_REQUEST)
    
    db = utils.get_db()
    base_url = utils.get_nodeurl()
    incident = requests.get(f'{base_url}/api/incident/{incident_id}')

    if incident.status_code != 200 or incident.json()['incident'] is None:
        err = {'error': 'incident not found', 'incident':incident.json()}
        return JsonResponse(err, status=status.HTTP_400_BAD_REQUEST)
    
    building_id = incident.json()['incident']['buildingId']
    graph = PathFinder.get_graph(incident_id,db)
    fire_nodes = PathFinder.get_fire_nodes(incident_id,db)
    nodes, fire_extinguishers, medkits, exits = PathFinder.get_node_objs(graph,fire_nodes,building_id)
    start = nodes[start_id]
    goal_nodes = []
    if mode == 'exit': goal_nodes = exits
    elif mode == 'extinguisher': goal_nodes = fire_extinguishers
    elif mode == 'medkit': goal_nodes = medkits
    path_nodes = PathFinder.astar(nodes,start,goal_nodes)
    path = {id: node.id for id, node in enumerate(path_nodes)}
    return JsonResponse({'path':path}, status=status.HTTP_200_OK)


@api_view(['get'])
def route_user(request):
    incident_id = request.query_params.get('incident_id')
    mode = request.query_params.get('mode','exit')
    start = request.query_params.get('start_id')
    user_id = request.query_params.get('user_id')

    if start is not None: start = int(start)
    if user_id is not None: user_id = int(user_id)

    modes = ['exit','extinguisher','medkit']

    if incident_id is None or start is None or user_id is None:
        err = {'error': 'incident_id, start and user_id are required as querry params'}
        return JsonResponse(err, status=status.HTTP_400_BAD_REQUEST)
    if mode not in modes:
        err = {'error': "mode should be either 'exit', 'extinguisher' or 'medkit'"}
        return JsonResponse(err, status=status.HTTP_400_BAD_REQUEST)
    
    db = utils.get_db()
    base_url = utils.get_nodeurl()
    incident = requests.get(f'{base_url}/api/incident/{incident_id}')

    if incident.status_code != 200 or incident.json()['incident'] is None:
        err = {'error': 'incident not found', 'incident':incident.json()}
        return JsonResponse(err, status=status.HTTP_400_BAD_REQUEST)
    
    building_id = incident.json()['incident']['buildingId']
    graph = PathFinder.get_graph(incident_id,db)
    fire_nodes = PathFinder.get_fire_nodes(incident_id,db)
    nodes, fire_extinguishers, medkits, exits = PathFinder.get_node_objs(graph,fire_nodes,building_id)
    start = nodes[start]
    goal_nodes = []
    if mode == 'exit': goal_nodes = exits
    elif mode == 'extinguisher': goal_nodes = fire_extinguishers
    elif mode == 'medkit': goal_nodes = medkits
    path_nodes = PathFinder.astar(nodes,start,goal_nodes)
    path = {id: node.id for id, node in enumerate(path_nodes)}

    try:
        db.child('Incidents').child(incident_id).child('UserRoutes').child(user_id).set(path)
        return JsonResponse({'message':f'Route Created for user {user_id}'}, status=status.HTTP_200_OK)
    except Exception as e:
        return JsonResponse({'error':f'Error creating route for user {user_id}'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_dummy(request):
    user_id = request.GET.get('user_id', None)
    incident_id = request.GET.get('incident_id', None)
    if user_id is None or incident_id is None:
        err = {'error': 'user_id and incident_id is required as querry params'}
        return JsonResponse(err, status=status.HTTP_400_BAD_REQUEST)
    db = utils.get_db()
    path = {'0':'1','1':'2','2':'3','3':'4','4':'5','5':'6','6':'18','7':'17','8':'25','9':'33'}
    db.child('Incidents').child(incident_id).child('UserRoutes').child(user_id).set(path)
    return JsonResponse({'message':f'Dummy Route Created for user {user_id}'}, status=status.HTTP_200_OK)
