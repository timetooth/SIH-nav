from scipy.signal import convolve2d
import numpy as np
import random
import redis
import io

cache = redis.StrictRedis(host='localhost', port=6379, db=0)

'''
The module contains the functions to simulate the spread of fire 
in a grid using cellular automata algorithm based on a heuristics based probabalistic model.

The model is based on the following assumptions:
1. The probability of a cell catching fire is based on the number of active neighbours and their distance.
2. The probability of a cell catching fire is based on the time to ignition of the cell.
max_tti: maximum time to ignition of a cell, a hyperparameter to standardize the time to ignition values.
'''

max_tti = 500

def initialize_grid(ignite_cell, shape=(15,26)):
    start_x, start_y = ignite_cell
    grid = np.zeros(shape)
    # not-burning-0, burning-1, burnt-2, protected-3, barrier-4 for future implementation
    tti = np.random.randint(1, max_tti, size=shape)
    grid[start_x][start_y] = 1
    return grid, tti

def is_valid(grid, coordinates):
    x, y = coordinates[0], coordinates[1]
    if x < 0 or x >= grid.shape[0] or y < 0 or y >= grid.shape[1]:
        return False
    return True

def neighbour_factor(grid, coordinates):
    x, y = coordinates[0], coordinates[1]
    nearest_active = 0
    for i in range(-1, 2):
        for j in range(-1, 2):
            if is_valid(grid, (x+i, y+j)) and grid[x+i][y+j] == 1:
                nearest_active += 1
    farther_active = 0
    for i in range(-2, 3):
        for j in range(-2, 3):
            if is_valid(grid, (x+i, y+j)) and grid[x+i][y+j] == 1:
                if abs(i) < 2 and abs(j) < 2: nearest_active += 1
                else: farther_active += 1
    return (nearest_active, farther_active)

def spread_probability(grid, tti, alpha=1, beta=0.5):
    '''
    Calculates the probability of cells catching fire based on neighborhood and tti.
    '''
    near_kernel = np.array([[1, 1, 1],
                            [1, 0, 1],
                            [1, 1, 1]])
    far_kernel = np.array([[1, 1, 1, 1, 1],
                           [1, 0, 0, 0, 1],
                           [1, 0, 0, 0, 1],
                           [1, 0, 0, 0, 1],
                           [1, 1, 1, 1, 1]])
    
    near_neighbors = convolve2d(grid == 1, near_kernel, mode='same', boundary='fill', fillvalue=0)
    far_neighbors = convolve2d(grid == 1, far_kernel, mode='same', boundary='fill', fillvalue=0) - near_neighbors

    near = near_neighbors / 8
    far = beta * (far_neighbors / 16)
    tti_scaled = tti / max_tti

    prob = 1 - np.exp(-alpha * (1 + near + far) * tti_scaled)
    return prob

def update_grid(grid, tti, alpha=1, beta=0.5, gamma=0.1, warn_threshold=0.8):
    '''
    Updates the grid for the next timestep based on spread probability.
    '''
    prob = spread_probability(grid, tti, alpha, beta)

    random_values = np.random.rand(*grid.shape) # Random values for annealing
    ignite = (random_values < gamma * prob) & (grid == 0)
    warn = (gamma * prob >= warn_threshold) & (grid == 0)

    # Update grid states
    grid[ignite] = 1
    grid[warn] = 2
    return grid

def store_array(key, array, timeout=3600):
    """
    Serialize and store a NumPy array in Redis.
    """
    buffer = io.BytesIO()
    np.save(buffer, array)
    buffer.seek(0) 
    cache.set(key, buffer.read(), ex=timeout)

def retrieve_array(key):
    """
    Retrieve and deserialize a NumPy array from Redis,
    then convert it to a JSON-serializable format.
    """
    array_data = cache.get(key)
    if array_data is None:
        return None
    buffer = io.BytesIO(array_data)
    buffer.seek(0)
    array = np.load(buffer)
    return array.tolist()

def simulate_fire(ignite_cell, shape, alpha=1, beta=0.5, gamma=0.1, steps=50, warn_threshold=0.8, grid=None, tti=None):
    '''
    Each grid acts a key frame for the simulation
    ignite_cell: tuple of x, y coordinates of the cell to ignite
    shape: tuple of rows and columns of the grid
    alpha: hyperparameter for final scaling in spread_probability
    beta: hyperparameter, weight for farther active cells in spread_probability
    gamma: speed factor (resolution) for the spread of fire
    steps: number of steps to simulate/frames to generate
    Returns: an array of size steps containing the situation of gid at each step
    0 - not burning, 1 - burning, 2 - warning
    '''
    cache.flushdb()
    if grid is None or tti is None:
        grid, tti = initialize_grid(ignite_cell, shape=shape)
    for frame_number in range(steps):
        grid = update_grid(grid, tti, alpha, beta, gamma, warn_threshold)
        cache_key = f"building:{1}:frame:{frame_number}"
        store_array(cache_key, grid,3600)
    return
