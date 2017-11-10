"""
ObsidianWorld.py
"""

from collections import OrderedDict
import numpy as np

__author__ = "Chris Campell"
__version__ = '11/6/2017'


class ObsidianWorldMDP:
    initial_state = None
    terminal_states = None
    states = None
    edges = None
    movement_cpts = None
    gamma = None
    # The number of states:
    n = None
    # The number of edges:
    m = None
    # The number of terminal states:
    n_t = None

    def __init__(self, initial_state, terminal_states, states, edges, movement_cpts, gamma):
        """
        __init__: Constructor for objects of type ObsidianWorld. Creates an obsidian world instance with data parsed
            from the text file.
        :param initial_state: The starting state.
        :param terminal_states: The terminal states.
        :param states: A list of all the states and their associated rewards.
        :param edges: A list of all the directed edge connections.
        :param movement_cpts: The conditional probability tables associated with movement in a stochastic environment.
        :param gamma: The discount factor to penalize long action sequences.
        """
        for state, reward in states:
            if state == initial_state:
                self.initial_state = (state, reward)
        self.terminal_states = []
        # Keep track of the reward associated with each terminal state:
        for term_state in terminal_states:
            for state, reward in states:
                if state == term_state:
                    self.terminal_states.append((term_state, reward))
        self.states = states
        # Maintain a list of non-terminal states:
        self.nonterm_states = states.copy()
        for term_state, reward in self.terminal_states:
            self.nonterm_states.remove((term_state, reward))
        self.edges = edges
        self.movement_cpts = movement_cpts
        self.gamma = gamma
        # Set the number of states 'n':
        self.n = len(states)
        # Set the number of edges 'm':
        self.m = len(edges)
        # Set the number of terminal states 'n_t':
        self.n_t = len(terminal_states)


def parse_information(input_file):
    world_info = {'initial_state': None, 'states': [], 'terminal_states': None, 'movement_cpts': {}, 'gamma': None, 'edges': {}}
    with open(input_file, 'r') as fp:
        input_file = fp.read()
    input_text = input_file.split('\n')[:-1]
    loop_locations = {}
    for line_num, line in enumerate(input_text):
        if line.isnumeric():
            loop_start = line_num + 1
            loop_end = line_num + int(line) + 1
            loop_locations[len(loop_locations)] = [loop_start, loop_end]
    for loop_id, loop_info in loop_locations.items():
        if loop_id == 0:
            # States loop:
            for i in range(loop_info[0], loop_info[1]):
                split_state_text = input_text[i].split(' ')
                state = (split_state_text[0], int(split_state_text[1]))
                world_info['states'].append(state)
            # Get terminal states:
            terminal_states_text = input_text[loop_info[1]].split(' ')
            world_info['terminal_states'] = terminal_states_text
        elif loop_id == 1:
            # Movement cpts loop:
            for i in range(loop_info[0], loop_info[1]):
                split_cpt_dir = input_text[i].split(' ')
                # The desired move is north (key one)
                source_dir = split_cpt_dir[0]
                # The value is the probability in ending up in key '{N,E,S,W}' given the source_dir:
                world_info['movement_cpts'][source_dir] = {
                    'N': float(split_cpt_dir[1]),
                    'E': float(split_cpt_dir[2]),
                    'S': float(split_cpt_dir[3]),
                    'W': float(split_cpt_dir[4])
                }
        elif loop_id == 2:
            # State edges loop:
            for i in range(loop_info[0], loop_info[1]):
                state_trans_pair = input_text[i].split(' ')
                s = state_trans_pair[0]
                action = state_trans_pair[1]
                s_prime = state_trans_pair[2]
                if s in world_info['edges']:
                    world_info['edges'][s][action] = s_prime
                else:
                    world_info['edges'][s] = {}
                    world_info['edges'][s][action] = s_prime
        else:
            print("Warning: This input loop is extraneous or does not exist.")
    # Get the initial state (the last line)
    world_info['initial_state'] = input_text[-1]
    # Get gamma (the second to last line)
    world_info['gamma'] = float(input_text[-2])
    return world_info

def value_iteration(mdp, epsilon):
    # TODO: Topological sorting of graph from initial state? Edge wise traversal outward? Values converge incorrectly.
    # Perform value iteration beginning in the specified initial state:
    start_state_index = mdp.states.index(mdp.initial_state)
    swap_state_index = 0 if start_state_index != 0 else 1
    mdp.states[swap_state_index], mdp.states[start_state_index] = mdp.states[start_state_index], mdp.states[swap_state_index]
    # index_1d = lambda state : (((ord(state[0]) - 96) - 1) * num_cols) + (int(state[1]) - 1)
    U = {state: 0 for (state, reward) in mdp.states}
    # Insert the utilities of the terminal states:
    for term_state, reward in mdp.terminal_states:
        U[term_state] = reward
    U_prime = U.copy()
    delta = None
    converged = False
    while not converged:
        U = U_prime.copy()
        delta = 0.0
        # Perform value iteration from the specified start state:
        for i, (state, reward) in enumerate(mdp.states):
            if state not in [state for state, reward in mdp.terminal_states]:
                expected_utility = OrderedDict()
                for desired_action, desired_s_prime in mdp.edges[state].items():
                    # Where could we end up?
                    remaining_states = mdp.edges[state].copy()
                    remaining_states.pop(desired_action)
                    expected_utility[desired_action] = mdp.movement_cpts[desired_action][desired_action]*U[desired_s_prime]
                    for stochastic_action, stochastic_s_prime in remaining_states.items():
                        expected_utility[desired_action] += mdp.movement_cpts[desired_action][stochastic_action]*U[stochastic_s_prime]
                    # expected_utility[desired_action] = sum([prob_action*U[s_prime] for prob_action in mdp.movement_cpts[desired_action].values()])
                # Perform utility update:
                U_prime[state] = reward + (mdp.gamma * np.max(list(expected_utility.values())))
            delta_update = np.abs(U_prime[state] - U[state])
            if delta_update > delta:
                delta = delta_update
        if delta <= epsilon*((1 - mdp.gamma)/mdp.gamma):
            converged = True
    return U

def main(input_file):
    metadata = parse_information(input_file)
    mdp = ObsidianWorldMDP(
        initial_state=metadata['initial_state'],
        terminal_states=metadata['terminal_states'],
        states=metadata['states'],
        edges=metadata['edges'],
        movement_cpts=metadata['movement_cpts'],
        gamma=metadata['gamma']
    )
    value_iteration(mdp=mdp, epsilon=10**-5)

if __name__ == '__main__':
    input_files = []
    main(input_file='value_iteration/fig_17_3.txt')