import json
import pyrebase
import requests
from geopy.distance import geodesic
from queue import PriorityQueue
from . import utils
from upstash_redis import Redis
from dotenv import load_dotenv
import os

load_dotenv()

redis_url = os.getenv("REDIS_URL")
redis_token = os.getenv("REDIS_TOKEN")

redis = Redis(url=redis_url, token=redis_token)

class Node:
    def __init__(self,id,coordinates,neighbours,poi=None,name=None,on_fire=False,is_extinguisher=False,is_medkit=False):
        self.id = id
        self.coordinates = coordinates
        self.neighbours = neighbours
        self.poi = poi
        self.name = name
        self.on_fire = on_fire
    def __str__(self):
        return f'Node-{self.id}'
    def get_pos(self):
        return self.coordinates
    def get_children(self):
        return self.neighbours
    
def normalize_data(data):
    if isinstance(data, list):
        data = {index: value for index, value in enumerate(data) if value is not None}
    return data


def get_fire_nodes(incident_id,db):
    '''
    Returns the list of Node Ids that are on fire in the incident
    '''
    fire_nodes_data = db.child('Incidents').child(incident_id).child('Nodes').child('FireNodes').get().val()
    if fire_nodes_data is None: return []
    fire_nodes = []
    for i,node in enumerate(fire_nodes_data):
        if node is not None and node == True: fire_nodes.append(i)
        elif isinstance(node, tuple) or isinstance(node, list): fire_nodes.append((node[0]))
    return fire_nodes

def get_graph(building_id, db):
    cache_key = f"graph_data:{building_id}"
    cached_graph = redis.get(cache_key)
    if cached_graph is not None:
        graph = json.loads(cached_graph)
        return graph
    else:
        adj_list = normalize_data(db.child('Buildings').child(f'{building_id}').child('AdjList').get().val())
        if adj_list is None:
            return {}
        graph = {}
        for node, children in adj_list.items():
            node = int(node)
            children = normalize_data(children)
            graph[node] = list(map(int, children.keys()))
        redis.set(cache_key, json.dumps(graph))
        return graph

def get_node_objs(graph, fire_nodes, building_id):
    """
    Returns:
        - dict {Id: Node_obj}
        - list [fire extinguisher node objects]
        - list [medkit node objects]
        - list [exit node objects]
    """
    base_url = utils.get_nodeurl()
    cache_key = f"nodes_data:{building_id}"
    nodes_data = {}

    try:
        cached_nodes = redis.get(cache_key)
        if cached_nodes:
            nodes_data = json.loads(cached_nodes)
        else:
            nodes_raw = requests.get(f'{base_url}/api/building/{building_id}/node')
            nodes_raw.raise_for_status()
            nodes_data = nodes_raw.json().get('nodes', [])
            redis.set(cache_key, json.dumps(nodes_data))

        if not nodes_data:
            return {}, [], [], [] 

        fire_extinguishers = []
        medkits = []
        exits = []
        nodes = {}

        for node in nodes_data:
            id = node['id']
            coordinates = node.get('latlng', {}).get('coordinates', None)
            poi = node.get('poi', None)
            name = node.get('name', None)
            on_fire = id in fire_nodes

            nodes[id] = Node(id, coordinates, graph.get(id, []), poi, name, on_fire=on_fire)

            if poi == 'EXTINGUISHER':
                fire_extinguishers.append(nodes[id])
            elif poi == 'FIRST_AID':
                medkits.append(nodes[id])
            elif poi == 'EXIT':
                exits.append(nodes[id])

        return nodes, fire_extinguishers, medkits, exits

    except requests.RequestException as e:
        raise ValueError(f"Error fetching nodes data for building {building_id}: {e}")
    except Exception as e:
        raise ValueError(f"Unexpected error while processing nodes: {e}")

def construct_path(came_from,current):
    path=[current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path = path[::-1]
    return path

def h(node,neighbour):
    Node_on_fire_heuristic = float('inf')
    if node.on_fire: return Node_on_fire_heuristic
    return 0

def g(node,neighbour):
    return geodesic(node.get_pos(),neighbour.get_pos()).meters

def astar(nodes,start,goal_nodes):
    count = 0
    open_set = PriorityQueue()
    open_set.put((0,count,start))
    came_from = {}
    g_score = {node: float('inf') for node in nodes.values()}
    g_score[start] = 0
    f_score = {node: float('inf') for node in nodes.values()}
    f_score[start] = 0
    open_set_hash = {start}

    while not open_set.empty():
        current = open_set.get()[2]
        open_set_hash.remove(current)
        if current in goal_nodes: 
            path = construct_path(came_from,current)
            return path, int(g_score[current])
        
        for neighbour_id in current.neighbours: 
            neighbour = nodes[int(neighbour_id)]
            temp_g_score = g_score[current] + g(current,neighbour)
            if temp_g_score < g_score[neighbour]:
                came_from[neighbour] = current
                g_score[neighbour] = temp_g_score
                f_score[neighbour] = temp_g_score + h(current,neighbour)
                if neighbour not in open_set_hash:
                    count += 1
                    open_set.put((f_score[neighbour],count,neighbour))
                    open_set_hash.add(neighbour)
    return [], 0