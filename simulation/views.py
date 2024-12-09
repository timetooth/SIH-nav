from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from . import simulate_fire

# Create your views here.

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
    if frame_number is None:
        err = {'error': 'time is required parameter'}
        return Response(err, status=status.HTTP_400_BAD_REQUEST)
    key = f'building:1:frame:{frame_number}'
    key_frame = simulate_fire.retrieve_array(key)
    if key_frame is None:
        err = {'error': 'time frame not found'}
        return Response(err, status=status.HTTP_400_BAD_REQUEST)
    return Response({'key_frames': key_frame})

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
    '''
    ignite_cell = request.data.get('ignite_cell')
    shape = request.data.get('shape')
    alpha = request.data.get('alpha', 1)
    beta = request.data.get('beta', 0.5)
    gamma = request.data.get('gamma', 0.1)
    steps = request.data.get('steps')
    warn_threshold = request.data.get('warn_threshold', 0.8)

    if ignite_cell is None or shape is None or steps is None:
        err = {'error': 'ignite_cell, shape, and steps are required parameters'}
        return Response(err, status=status.HTTP_400_BAD_REQUEST)
    
    simulate_fire.simulate_fire(ignite_cell, shape, alpha, beta, gamma, steps, warn_threshold)

    return Response({'message': 'Simulation Ran!'}, status=status.HTTP_202_ACCEPTED)