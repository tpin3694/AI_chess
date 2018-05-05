import numpy as np
import random
from anytree import Node, LevelGroupOrderIter, RenderTree
from copy import deepcopy
from game import opponent
from utilities.constants import *
from scipy.stats import beta
import logging
logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filename='tree_search.log')



class MCTS:
    def __init__(self, board_env, exploration = 0.7):
        """
        An implementation of Monte-Carlo Tree Search for game play. An exploration rate 0.7 is set, as per the advice
        of Martin Mueller (https://scholar.google.com/scholar_url?url=https://link.springer.com/chapter/10.1007/978-3-642-12993-3_6&hl=en&sa=T&oi=gsb&ct=res&cd=0&ei=ME_oWqmzLovCmgH0j73gAQ&scisig=AAGBfm0KuSPQZ3FzXJi9WyFY7n-xi0nrmA)
        :param board_env: The game's board
        :param exploration: C Parameter for UCT. 0.7 s
        """
        self.board = board_env
        self.initial_node = {'visit_count': 0, 'win_count': 0, 'total_reward': 0} # Starting params for every node
        self.root = Node('0', board = self.board, action = None, **self.initial_node)
        self.max_player = board_env.current_player
        self.current_depth = 0
        self.max_depth = uct_max_depth
        self.exploration = exploration
        self.maximisation = True
        self.opponent = opponent.Adversary(verbose=False, search_depth=2, max_think=1)
        self.opponent.initialise_engine(self.board.board)

    def ucb(self, candidate_list, explore_param, maximise=True):
        """
        Calculate UCB values for each node in a given set
        :param candidate_list: List of nodes
        :param explore_param: C parameter, controlling the level of exploration
        :param maximise: Bool whether the value should be maximised
        :return: The optimal node
        """
        total_visits = np.sum([node.visit_count for node in candidate_list])
        means = np.array([node.total_reward/node.visit_count+np.random.uniform(low=0.01, high = 0.05) for node in candidate_list])
        cis = np.array([np.sqrt(2*np.log(node.visit_count)/total_visits) for node in candidate_list])
        uct_values = means + explore_param * cis
        max_value = np.argmax(uct_values)
        return candidate_list[max_value]

    def epsilon_greedy(self, candidate_list, epsilon=0.1):
        means = np.array([node.total_reward/node.visit_count+np.random.uniform(low=0.01, high = 0.05) for node in candidate_list])
        uniform_sample = np.random.uniform(0, 1, size=1)
        if uniform_sample>epsilon:
            return candidate_list[np.argmax(means)]
        else:
            return random.choice(candidate_list)

    def boltzmann(self):
        pass

    def thompson_sampling(self, candidate_list):
        samples = [beta.rvs(a=node.win_count+1, b=node.visit_count-node.win_count+1, size = 1)[0] for node in candidate_list]
        return candidate_list[np.argmax(samples)]

    def ucb1(self, candidate_list, explore_param):
        total_visits = np.sum([node.visit_count for node in candidate_list])
        means = np.array([node.total_reward / node.visit_count + np.random.uniform(low=0.01, high=0.05) for node in candidate_list])
        cis = np.array([np.sqrt(2*np.log(node.visit_count)/total_visits) for node in candidate_list])

    def mini_maxi_update(self):
        """
        Potential legacy function if we wish to select the lowest scoring action for adversary.
        :return:
        """
        if self.maximisation:
            self.maximisation=False
        else:
            self.maximisation=True

    def selection(self):
        # Root the tree and initialise maximisation
        root_node = self.root
        self.maximisation=True
        self.current_depth = 0
        # Test all of the nodes potential children
        while root_node.children and self.current_depth < self.max_depth:
            children_nodes = list(root_node.children)

            # Update the boards current legal moves
            root_node.board.update_l_moves()

            # Test if every legal move has been already explored. If not, explore the unexplored
            potential_actions = root_node.board.l_moves
            explored = [child_node.action for child_node in children_nodes]
            if set(potential_actions) > set(explored):
                logging.info('Unexplored Child Nodes Still Exist')
                logging.info('Expanding {}'.format(root_node.name))
                return root_node

            # If every move has been taken, proceed down the tree
            else:
                logging.info('{} Expanded'.format(root_node.name))
                # Update root node based upon optimal UCB evaluation
                root_node = self.ucb(children_nodes, self.exploration, maximise=self.maximisation)
                logging.info('Expansion Yielded {}'.format(root_node.name))
                # Update to reflect whether maximisation or minimisation should take place next time around
                self.mini_maxi_update()
            self.current_depth += 1
        return root_node

    def expansion(self, parent):
        # Check for any unexplored child nodes
        parent.board.update_l_moves()
        explored = [node.action for node in list(parent.children)]
        to_explore = [action for action in parent.board.l_moves if action not in explored]

        # If any do exist, explore expand them
        if len(to_explore) > 0:
            move = random.choice(to_explore)

            # Add a node corresponding to this move to the game tree
            sim_game = deepcopy(parent.board)
            sim_game.board.push(move)
            child_node = Node(name='{}_{}'.format(parent.name, len(parent.children)), parent=parent, action = move,
                              board = sim_game, **self.initial_node)
            return child_node
        # In the absence of unexplored nodes, return the parent
        else:
            return parent

    def evaluate(self, node, n_simulation):
        # TODO: Add score bonus to differentiate between a good and bad win. - Martin Mueller
        win_count = 0
        reward = 0
        i = 0
        while i < n_simulation:
            current_board = deepcopy(node.board)
            current_board.player_update()
            active = current_board.current_player
            while current_board.active:
                current_board.play_random()
            #     if active == 'w':
            #         # If we're playing, move randomly
            #
            #         current_board.play_random(verbose=True)
            #     else:
            #         # Set stockfish to simulate
            #         move = self.opponent.calculate(current_board)
            #         current_board.make_move(str(move))
                current_board.terminal()
                current_board.update_methods()

            # Determine Winner and store result in node
            result = current_board.board.result()
            if result == '1-0':
                win_count += 1
                reward += 1
                logging.info('From Node: {}, Result: {}'.format(node.name, 'Win'))
            elif result == '1-0':
                reward -= 1
                logging.info('From Node: {}, Result: {}'.format(node.name, 'Loss'))
            else:
                logging.info('From Node: {}, Result: {}'.format(node.name, 'Draw'))
            i += 1
        return win_count, reward

    @staticmethod
    def backprop(node, visits, win_count, reward):
        node.visit_count += visits
        node.win_count += win_count
        node.total_reward += reward

        # Now loop through all parents and their respective parents
        for parent in node.ancestors:
            parent.visit_count += visits
            parent.win_count += win_count
            parent.total_reward += reward

    def search(self, nits, tree_simulations, verbose = False):
        i = 0
        root_node = self.root
        logging.info('Tree Search Beginning From: {}'.format(root_node.board.board.fen()))
        while i < nits:
            if i%(nits/10)==0:
                print('{}% Complete'.format(np.round(i*100/nits, 0)))
            root_node = self.selection()
            expand_node = self.expansion(root_node)
            win_count, total_reward = self.evaluate(expand_node, tree_simulations)
            self.backprop(expand_node, tree_simulations, win_count, total_reward)
            i += 1
        if verbose:
            self.print_tree()

    def get_best_action(self):
        all_nodes = list(LevelGroupOrderIter(self.root))
        if all_nodes:
            direct_children = all_nodes[1]
            best_node = self.ucb(direct_children, 0)
            return best_node.action

    def print_tree(self):
        for pre, fill, node in RenderTree(self.root):
            print('{}{}, mean_reward: {}, Visits: {}, Wins: {}'.format(pre, node.action,
                                                             np.round(node.total_reward/node.visit_count, 5),
                                                             node.visit_count, node.win_count))
