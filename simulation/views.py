from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from . import simulate_fire

# Create your views here.

cache = {}

@api_view(['GET'])
def default_view(request):
    return Response({"message": "Welcome to Simulate Module!"})

@api_view(['GET'])
def get_keyframe(requests):
    '''
    This function is used to get the keyframes of the simulation
    GET request:
    Pass the frame number as frame_number
    '''
    frame_number = requests.query_params.get('time')
    building_id = requests.query_params.get('building_id', 1)

    if frame_number is None:
        err = {'error': 'time is required parameter'}
        return Response(err, status=status.HTTP_400_BAD_REQUEST)
    key = f'building:{building_id}:frame:{frame_number}'
    key_frame = cache.get(key,None)
    if key_frame is None:
        err = {'error': 'time frame not found'}
        return Response(err, status=status.HTTP_400_BAD_REQUEST)
    return Response({'key_frame': key_frame})

@api_view(['POST'])
def start_simulation(request):
    '''
    This function is used to simulate the fire spread in the building
    POST request:
    ignite_cell: 2D array ([x,y]) coordinates of the cell to ignite
    shape: 2D array ([rows, cols]) shape of the grid
    steps: int number of keyframes
    alpha, beta, gamma: optional hyperparameters, range(0,1)
    warn_threshold: float threshold for warning, range(0,1)
    send_frames: bool whether to send the frames in the response
    '''
    ignite_cell = request.data.get('ignite_cell')
    shape = request.data.get('shape')
    alpha = request.data.get('alpha', 1)
    beta = request.data.get('beta', 0.5)
    gamma = request.data.get('gamma', 0.1)
    steps = request.data.get('steps')
    warn_threshold = request.data.get('warn_threshold', 0.8)
    building_id = request.data.get('building_id', 1)
    send_frames = request.data.get('send_frames', True)

    if ignite_cell is None or shape is None or steps is None:
        err = {'error': 'ignite_cell, shape, and steps are required parameters'}
        return Response(err, status=status.HTTP_400_BAD_REQUEST)
    
    frames = simulate_fire.simulate_fire(ignite_cell, shape, alpha, beta, gamma, steps, warn_threshold)

    for frame_number, frame in enumerate(frames):
        key = f'building:{building_id}:frame:{frame_number}'
        cache[key] = frame
    
    if send_frames: return Response({'keyframes': frames}, status=status.HTTP_202_ACCEPTED)
    else: return Response({'keyframes': 'Frames have ben stored'}, status=status.HTTP_200_OK)