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
def get_keyframe(request):
    """
    Get the keyframes of the simulation.

    GET Parameters:
    - time: Frame number (required).
    - building_id: ID of the building (default: 1).
    - ignite_cell: Comma-separated cell indices (optional).
    - shape: Comma-separated shape dimensions (optional).
    - steps: Number of steps (optional).

    Returns:
    - Key frame data or an error message.
    """
    frame_number = request.query_params.get('time')
    building_id = int(request.query_params.get('building_id', 1))
    ignite_cell_str = request.query_params.get('ignite_cell', '')
    shape_str = request.query_params.get('shape', '')
    steps = request.query_params.get('steps')

    if frame_number is None:
        return Response({'error': 'time is a required parameter'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        frame_number = int(frame_number)
    except ValueError:
        return Response({'error': 'time must be an integer'}, status=status.HTTP_400_BAD_REQUEST)

    ignite_cell = [int(i) for i in ignite_cell_str.split(',')] if ignite_cell_str else None
    shape = [int(i) for i in shape_str.split(',')] if shape_str else None

    key = f'{building_id}'
    if ignite_cell and shape:
        key = f'{ignite_cell}:{shape}:{steps}:{building_id}'

    if key in cache:
        frame = cache[key].get(frame_number)
        if frame is not None:
            return Response({'key_frame': frame})
        return Response({'error': 'time frame not found'}, status=status.HTTP_400_BAD_REQUEST)

    for k, val in cache.items():
        if key in k:
            frame = val.get(frame_number)
            if frame is not None:
                return Response({'key_frame': frame})
            return Response({'error': 'time frame not found'}, status=status.HTTP_400_BAD_REQUEST)

    return Response({'error': 'time frame not found'}, status=status.HTTP_400_BAD_REQUEST)


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

    key = f'{ignite_cell}:{shape}:{steps}:{building_id}'
    if key in cache: 
        if send_frames: return Response({'keyframes': list(cache[key].values())}, status=status.HTTP_202_ACCEPTED)
        else: return Response({'keyframes': 'Frames have ben stored'}, status=status.HTTP_200_OK)
    
    if ignite_cell is None or shape is None or steps is None:
        err = {'error': 'ignite_cell, shape, and steps are required parameters'}
        return Response(err, status=status.HTTP_400_BAD_REQUEST)
    
    frames = simulate_fire.simulate_fire(ignite_cell, shape, alpha, beta, gamma, steps, warn_threshold)

    cache[key] = {}
    for frame_number, frame in enumerate(frames):
        cache[key][frame_number] = frame
    
    if send_frames: return Response({'keyframes': list(cache[key].values())}, status=status.HTTP_202_ACCEPTED)
    else: return Response({'keyframes': 'Frames have ben stored'}, status=status.HTTP_200_OK)