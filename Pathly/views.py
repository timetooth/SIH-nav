from rest_framework.decorators import api_view
from rest_framework import status
from django.shortcuts import render
from rest_framework.response import Response
from . import utils
from . import PathFinder
import requests
import json

walking_speed = 1.5


@api_view(['GET'])
def default_view(request):
    """ Get A Dummy Route """   
    db = utils.get_db()
    data = db.child("Incidents").get().val()
    return Response(data)

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
        return Response(err, status=status.HTTP_400_BAD_REQUEST)
    db = utils.get_db()
    base_url = utils.get_nodeurl()
    graph = PathFinder.get_graph(building_id,db)
    nodes, fire_extinguishers, medkits, exits = PathFinder.get_node_objs(graph,[],building_id)
    start = nodes[start_id]
    end = nodes[goal_id]
    path_nodes,distance = PathFinder.astar(nodes,start,[end])
    path = {id: node.id for id, node in enumerate(path_nodes)}
    return Response({'path':path,'distance':distance}, status=status.HTTP_200_OK)

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
        return Response(err, status=status.HTTP_400_BAD_REQUEST)
    if mode not in modes:
        err = {'error': "mode should be either 'exit', 'extinguisher' or 'medkit'"}
        return Response(err, status=status.HTTP_400_BAD_REQUEST)
    
    db = utils.get_db()
    base_url = utils.get_nodeurl()
    incident = requests.get(f'{base_url}/api/incident/{incident_id}')

    if incident.status_code != 200 or incident.json()['incident'] is None:
        err = {'error': 'incident not found', 'incident':incident.json()}
        return Response(err, status=status.HTTP_400_BAD_REQUEST)
    
    building_id = incident.json()['incident']['buildingId']
    graph = PathFinder.get_graph(incident_id,db)
    fire_nodes = PathFinder.get_fire_nodes(incident_id,db)
    nodes, fire_extinguishers, medkits, exits = PathFinder.get_node_objs(graph,fire_nodes,building_id)
    start = nodes[start_id]
    goal_nodes = []
    if mode == 'exit': goal_nodes = exits
    elif mode == 'extinguisher': goal_nodes = fire_extinguishers
    elif mode == 'medkit': goal_nodes = medkits
    path_nodes,distance = PathFinder.astar(nodes,start,goal_nodes)
    path = {id: node.id for id, node in enumerate(path_nodes)}
    return Response({'path':path,'distance':distance,'time':int(distance/(walking_speed*60))}, status=status.HTTP_200_OK)


@api_view(['get'])
def route_user(request):
    incident_id = request.query_params.get('incident_id')
    mode = request.query_params.get('mode','exit')
    user_id = request.query_params.get('user_id')

    modes = ['exit','extinguisher','medkit']

    if incident_id is None or user_id is None:
        err = {'error': 'incident_id and user_id are required as querry params'}
        return Response(err, status=status.HTTP_400_BAD_REQUEST)
    if mode not in modes:
        err = {'error': "mode should be either 'exit', 'extinguisher' or 'medkit'"}
        return Response(err, status=status.HTTP_400_BAD_REQUEST)
    
    db = utils.get_db()
    base_url = utils.get_nodeurl()
    incident = requests.get(f'{base_url}/api/incident/{incident_id}')
    start = db.child('Incidents').child(incident_id).child('UserLocs').child(user_id).child('nearestNode').get().val()
    if start is None: 
        return Response({'error':f'User {user_id} not found in incident {incident_id}'}, status=status.HTTP_400_BAD_REQUEST)
    start = int(start)

    incident_data = incident.json()
    if 'incident' not in incident_data or incident_data['incident'] is None:
        return Response({'error': 'Invalid incident response'}, status=status.HTTP_400_BAD_REQUEST)
    
    building_id = incident.json()['incident']['buildingId']
    graph = PathFinder.get_graph(building_id,db)
    fire_nodes = PathFinder.get_fire_nodes(incident_id,db)
    nodes, fire_extinguishers, medkits, exits = PathFinder.get_node_objs(graph,fire_nodes,building_id)
    start = nodes[start]
    goal_nodes = []
    if mode == 'exit': goal_nodes = exits
    elif mode == 'extinguisher': goal_nodes = fire_extinguishers
    elif mode == 'medkit': goal_nodes = medkits
    path_nodes, distance = PathFinder.astar(nodes,start,goal_nodes)
    print(path_nodes)
    path = {id: node.id for id, node in enumerate(path_nodes)}
    time = distance/walking_speed
    try:
        db.child('Incidents').child(incident_id).child('UserRoutes').child(user_id).set(path)
        db.child('Incidents').child(incident_id).child('RoutesMetadata').child(user_id).set({'distance':distance,'mode':mode,'time': int(time/60)})
        return Response({'message':f'Route Created for user {user_id}'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error':f'Error creating route for user {user_id}'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['post'])
def reroute(request):
    incident_id = request.data.get('incident_id')
    mode = request.data.get('mode','exit')

    modes = ['exit','extinguisher','medkit']

    if incident_id is None:
        err = {'error': 'incident_id, start and user_id are required as querry params'}
        return Response(err, status=status.HTTP_400_BAD_REQUEST)
    else: incident_id = int(incident_id)
    if mode not in modes:
        err = {'error': "mode should be either 'exit', 'extinguisher' or 'medkit'"}
        return Response(err, status=status.HTTP_400_BAD_REQUEST)
    
    db = utils.get_db()
    base_url = utils.get_nodeurl()
    try:
        incident = requests.get(f'{base_url}/api/incident/{incident_id}')
    except Exception as e:
        return Response({'error':f'Error getting incident from Node backend {incident_id}','exception':str(e)}, status=status.HTTP_400_BAD_REQUEST)

    if incident.status_code != 200 or incident.json()['incident'] is None:
        err = {'error': 'incident not found', 'incident':incident.json()}
        return Response(err, status=status.HTTP_400_BAD_REQUEST)
    
    building_id = incident.json()['incident']['buildingId']
    graph = PathFinder.get_graph(incident_id,db)
    fire_nodes = PathFinder.get_fire_nodes(incident_id,db)
    nodes, fire_extinguishers, medkits, exits = PathFinder.get_node_objs(graph,fire_nodes,building_id)
    goal_nodes = []
    if mode == 'exit': goal_nodes = exits
    elif mode == 'extinguisher': goal_nodes = fire_extinguishers
    elif mode == 'medkit': goal_nodes = medkits
    errors = []
    users_data = db.child('Incidents').child(incident_id).child('UserLocs').get().val()
    if users_data is None: users_data = {}
    users = dict(users_data)
    for user_id, user_data in users.items():
        if not user_data['isInside']: continue
        start = nodes[user_data['nearestNode']]
        try:
            path_nodes, distance = PathFinder.astar(nodes,start,goal_nodes)
            path = {id: node.id for id, node in enumerate(path_nodes)}
            if path_nodes is None or len(path_nodes)<1: 
                db.child('Incidents').child(incident_id).child('UserLocs').child(user_id).update(
                    {'canEscape':False}
                )
            db.child('Incidents').child(incident_id).child('UserRoutes').child(user_id).set(path)
            time = distance/walking_speed
            db.child('Incidents').child(incident_id).child('RoutesMetadata').child(user_id).set({
                'distance':int(distance),'mode':mode,'time': int(time/60)
            })
        except Exception as e:
            errors.append(f'Error creating route for user {user_id}')

        if errors is not None and len(errors)>1:
            return Response({'message':'Some users were updated, but these were not','error':errors}, status=status.HTTP_400_BAD_REQUEST)
    return Response({'message':'All user routes updated'}, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_dummy(request):
    user_id = request.GET.get('user_id', None)
    incident_id = request.GET.get('incident_id', None)
    if user_id is None or incident_id is None:
        err = {'error': 'user_id and incident_id is required as querry params'}
        return Response(err, status=status.HTTP_400_BAD_REQUEST)
    db = utils.get_db()
    path = {'0':'1','1':'2','2':'3','3':'4','4':'5','5':'6','6':'18','7':'17','8':'25','9':'33'}
    db.child('Incidents').child(incident_id).child('UserRoutes').child(user_id).set(path)
    return Response({'message':f'Dummy Route Created for user {user_id}'}, status=status.HTTP_200_OK)

def compute_fire_intensity_index(T_current, H_current, CO_ppm, FlameValue, P_current,alpha=0.5):
    def clip(value, min_val=0.0, max_val=1.0): return max(min_val, min(value, max_val))
    T_ambient,T_maxRise = 25.0,75.0
    CO_max ,FlameMax = 1000.0, 1023.0
    P_baseline,P_range = 1013.0, 10.0
    H_ambient = 50.0
    T_n = clip((T_current - T_ambient) / T_maxRise)
    H_n = clip((H_ambient - H_current) / H_ambient)
    S_n = clip(CO_ppm / CO_max)
    F_n = clip(FlameValue / FlameMax)
    P_n = clip(abs(P_current - P_baseline) / P_range)
    W_flame,W_smoke,W_temp,W_hum,W_press = 0.40,0.30,0.20,0.05,0.05
    FII = (W_flame * F_n) + (W_smoke * S_n) + (W_temp * T_n) + (W_hum * H_n) + (W_press * P_n)
    FII = round(alpha*FII*100,2)
    return FII

@api_view(['Post'])
def set_fire_intensity(request):
    incident_id = request.data.get('incident_id')
    node_id = request.data.get('node_id')
    T_current = request.data.get('temperature')
    H_current = request.data.get('humidity')
    CO_ppm = request.data.get('CO_ppm')
    FlameValue = request.data.get('FlameValue')
    P_current = request.data.get('pressure')
    alpha = request.data.get('alpha',0.5)
    if T_current is None or H_current is None or CO_ppm is None or FlameValue is None or P_current is None:
        err = {'error': 'temperature, humidity, CO_ppm, FlameValue, and pressure are required parameters'}
        return Response(err, status=status.HTTP_400_BAD_REQUEST)
    FII = compute_fire_intensity_index(T_current, H_current, CO_ppm, FlameValue, P_current,alpha)
    db = utils.get_db()
    try:
        db.child('Incidents').child(incident_id).update({f'intensity':FII})
    except Exception as e:
        return Response({'error':f'Error setting fire intensity for incident {incident_id}'}, status=status.HTTP_400_BAD_REQUEST)
    return Response({'message':f'Fire Intensity set to {FII}','intensity':FII}, status=status.HTTP_200_OK)