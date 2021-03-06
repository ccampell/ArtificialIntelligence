"""
BayesNetwork.py
An implementation of a Bayesian Network for Programming Assignment Four.
"""

import pandas as pd
import json
import itertools
import numpy as np

__author__ = "Chris Campell"
__version__ = "11/28/2017"

prob_tables = None


class BayesNetwork:
    topology = None
    observations = None
    cpts = None
    bn_vars = None

    def __init__(self, bayes_net_topology, observations, cpts=None):
        """
        __init__: Initialization method for the Bayesian network. Instantiates a queryable bayesian net.
        :param bayes_net_topology: The topology of the network (connections between nodes).
        :param observations: The empirical evidence used to determine the conditional probability tables
            (if not provided during initialization).
        :param cpts: <optional> The conditional probabilities associated with each node in the Bayesian network.
        """
        self.topology = bayes_net_topology
        self.observations = observations
        if cpts is not None:
            self.cpts = cpts

    def build_probability_table(self, node, observations, probability_tables=None, dependencies=None):
        """
        build_probability_table: Builds the probability tables for the provided node in the Bayesian network
            given a set of observations.
        :param node: The node for which the probability tables are to be constructed for.
        :param observations: A series of empirical observations used to estimate associated event probabilities.
        :param probability_tables: Any pre-existing probability tables for dependencies of this node that may be used
            to speed up computation.
        :param dependencies: Nodes that the provided node is conditionally dependent upon.
        :return probability_table: The theoretical probability tables for the provided node given the observation set.
        """
        if dependencies is None or dependencies is False:
            # Calculate the probability of the independent variable given the observations:
            num_true = observations[node].value_counts()[True]
            total_num_obs = len(observations[node])
            key = 'P(%s=True)' % node
            probability_true = (num_true / total_num_obs)
            probability_tables[key] = probability_true
            key = 'P(%s=False)' % node
            probability_tables[key] = 1 - probability_true
        else:
            # The variable is conditionally dependent, construct the CPT:
            query = 'P(' + node + "|"
            for dependency in dependencies:
                query = query + dependency + ","
            query = query[0:-1]
            query += ')'
            # Construct the CPT for the query:
            observation_subset_cols = []
            observation_subset_cols.append(node)
            for dependency in dependencies:
                observation_subset_cols.append(dependency)
            # Subset the observations by the dependent variables.
            observation_subset = observations[observation_subset_cols]
            # Create a truth table:
            truth_table = list(itertools.product([False, True], repeat=len(observation_subset_cols)))
            for tuple in truth_table:
                df_query_with_node = ''
                df_query_without_node = ''
                human_readable_df_query = ''
                for i in range(len(tuple)):
                    if i == 0:
                        human_readable_df_query = human_readable_df_query + 'P(%s=%s|' %(observation_subset_cols[i], tuple[i])
                    else:
                        human_readable_df_query = human_readable_df_query + '%s=%s,' %(observation_subset_cols[i], tuple[i])
                        df_query_without_node = df_query_without_node + "%s == %s & " % (observation_subset_cols[i], tuple[i])
                    df_query_with_node = df_query_with_node + "%s == %s & " %(observation_subset_cols[i], tuple[i])
                human_readable_df_query = human_readable_df_query[0:-1] + ')'
                df_query_with_node = df_query_with_node[0:-3]
                df_query_without_node = df_query_without_node[0:-3]
                # Query the observation_subset:
                num_observed = observation_subset.query(df_query_with_node).count()[0]
                num_total_subset = observation_subset.query(df_query_without_node).count()[0]
                probability_tables[human_readable_df_query] = (num_observed / num_total_subset)
        return probability_tables

    def enumeration_ask(self,X,e,cpts):
        """
        enumeration_ask: Returns a probability distribution over X.
        :param X: The query variable for which probabilities are to be inferred. For example HighCarValue.
        :param e: The observed values for variables E. For example e:{GoodEngine:True, WorkingAC=False}
        :param bn: A Bayesian Network with variables {X} union E union Y (hidden variables).
        :return norm_dist_x: A normalized probability distribution over the query variable X.
        """
        # Sort vars in topological order:
        edge_list = []
        for parent, child_list in self.bayes_network.items():
            for child in child_list:
                edge_list.append([parent, child])
        vars = sort_direct_acyclic_graph(edge_list=edge_list)
        # x_i can only be True or False, no need for a loop:
        # Build keys based on evidence variable and query:
        query_true_key = 'P(%s=True|' % X
        query_false_key = 'P(%s=False|' % X
        for evidence, assignment in e.items():
            query_true_key = query_true_key + '%s=%s,' % (evidence, assignment)
            query_false_key = query_false_key + '%s=%s,' % (evidence, assignment)
        query_true_key = query_true_key[0:-1] + ')'
        query_false_key = query_false_key[0:-1] + ')'
        Q = {query_true_key: None, query_false_key: None}
        e_x_i = e.copy()
        e_x_i[X] = True
        joint_prob_query = 'P(%s=%s|' % (X,True)
        for evidence, observation in e.items():
            joint_prob_query = joint_prob_query + '%s=%s,' % (evidence, observation)
        joint_prob_query = joint_prob_query[0:-1] + ')'
        Q[joint_prob_query] = self.enumerate_all(vars=vars, e=e_x_i, cpts=cpts)
        e_x_i[X] = False
        joint_prob_query = 'P(%s=%s|' % (X,False)
        for evidence, observation in e.items():
            joint_prob_query = joint_prob_query + '%s=%s,' % (evidence, observation)
        joint_prob_query = joint_prob_query[0:-1] + ')'
        Q[joint_prob_query] = self.enumerate_all(vars=vars, e=e_x_i, cpts=cpts)
        # Return the normalization of Q (take each value of Q and divide it by the sum of all the values).
        q_norm = Q.copy()
        for query, probabilty in Q.items():
            q_norm[query] = probabilty / sum(Q.values())
        return q_norm


def is_independent(bayes_net_topology, node):
    """
    is_independent: Returns True if the node is an independent node in the Bayesian Network.
    :param node: The node for which to determine dependency.
    :param bayes_net: The topology of the Bayesian Network.
    :return boolean: True if the node is independent as specified in the topology of the Bayesian Network;
        False otherwise.
    """
    for parent, child_list in bayes_net_topology.items():
        if node in child_list:
            # The node is a child of another node, it is dependent.
            return False
    # The node is not a child of another node, it is independent.
    return True


def get_dependencies(bayes_net_topology, node):
    """
    get_dependencies: Returns the nodes that the provided node is conditionally dependent upon.
    :param node: The node to calculate dependencies for.
    :param bayes_net: The topology of the Bayesian Network.
    :return dependencies: A list of nodes that the provided node is dependent upon. Returns None if the provided node
        is independent.
    """
    if is_independent(bayes_net_topology=bayes_net_topology, node=node):
        # If the node is independent, it has no dependencies:
        return None
    dependencies = []
    for parent, child_list in bayes_net_topology.items():
        if node in child_list:
            # The node is a child of another node, it is dependent.
            dependencies.append(parent)
    return dependencies


def build_conditional_probability_tables(observations, node, dependencies=None):
    """
    build_conditional_probability_tables: Constructs the conditional probability tables required for the provided node.
    :param observations: The set of empirical observations used to estimate probabilistic occurrence of events.
    :param node: The Bayesian Network node for which the conditional probability table is to be constructed.
    :param dependencies: The other nodes in the Bayesian Network for which the provided node is conditionally dependent
        upon.
    :return cpt: The conditional probability tables associated with the provided node given the set of observations.
    """
    if dependencies is None or dependencies is False:
        # Calculate the probability of the independent variable given the observations:
        num_true = observations[node].value_counts()[True]
        total_num_obs = len(observations[node])
        probability_true = (num_true / total_num_obs)
        # P(Indpendent) = [F, T]
        return [1 - probability_true, probability_true]
    else:
        # The variable is conditionally dependent, construct the CPT:
        dim_prob_tables = tuple([2 for i in range(len(dependencies) + 1)])
        cpt = np.ndarray(dim_prob_tables)
        cpt[:] = np.NaN
        # Construct a list of columns to query the df of observations with:
        observation_subset_cols = []
        observation_subset_cols.append(node)
        observation_subset_cols = observation_subset_cols + dependencies
        # Subset the observations by the dependent variables:
        observation_subset = observations[observation_subset_cols]
        # Create a truth table to iterate over every possible combination of the query variable and its dependencies:
        truth_table = list(itertools.product([False, True], repeat=len(dependencies) + 1))
        for permutation in truth_table:
            df_query_with_node = ''
            df_query_without_node = ''
            for i in range(len(permutation)):
                if i != 0:
                    df_query_without_node = df_query_without_node + "%s == %s & " % (observation_subset_cols[i], permutation[i])
                df_query_with_node = df_query_with_node + "%s == %s & " %(observation_subset_cols[i], permutation[i])
            df_query_with_node = df_query_with_node[0:-3]
            df_query_without_node = df_query_without_node[0:-3]
            # query the observation subset:
            num_observed = observation_subset.query(df_query_with_node).count()[0]
            num_total_subset = observation_subset.query(df_query_without_node).count()[0]
            logical_index = [1 if x is True else 0 for x in permutation]
            cpt[tuple(logical_index)] = (num_observed / num_total_subset)
    return cpt


def _get_cpts(bayes_net_topology, observations):
    """
    _get_cpts: Returns all conditional probability tables required in the Bayesian Network.
    :param bayes_net_topology: The graph topology of the Bayesian network.
    :param observations:
    :return:
    """
    dim_prob_tables = tuple([2 for i in range(len(bayes_net_topology))])
    cpts = {}
    for node in bayes_net_topology:
        if is_independent(bayes_net_topology, node):
            # The node has no parent, it is independent.
            if node not in cpts:
                # The node is not already in the CPTs:
                cpts[node] = build_conditional_probability_tables(observations=observations, node=node)
        else:
            # The node is the child of another node, it is dependent upon its parent.
            if node not in cpts:
                # The node is not already in the probability tables.
                # Get the nodes that the current node is conditionally dependent upon:
                dependencies = get_dependencies(bayes_net_topology=bayes_net_topology, node=node)
                # Build the probability table for this node:
                cpt_name = node + '|'
                for dependency in dependencies:
                    cpt_name  = cpt_name + dependency + ','
                cpt_name = cpt_name[0:-1]
                cpts[cpt_name] = build_conditional_probability_tables(node=node, observations=observations, dependencies=dependencies)
    return cpts


def sort_direct_acyclic_graph(edge_list):
    """
    sot_direct_acyclic_graph: Sorts the input in topological order.
    :source: http://code.activestate.com/recipes/578406-topological-sorting-again/
    :param edge_list: A list of edges [['a','b'],['b','c']] implies a->b, and b->c.
    :return node_list: The nodes sorted topographically.
    """
    # edge_set is consumed, need a copy
    edge_set = set([tuple(i) for i in edge_list])
    # node_list will contain the ordered nodes
    node_list = list()
    #  source_set is the set of nodes with no incoming edges
    node_from_list, node_to_list = zip(* edge_set)
    source_set = set(node_from_list) - set(node_to_list)
    while len(source_set) != 0 :
        # pop node_from off source_set and insert it in node_list
        node_from = source_set.pop()
        node_list.append(node_from)
        # find nodes which have a common edge with node_from
        from_selection = [e for e in edge_set if e[0] == node_from]
        for edge in from_selection :
            # remove the edge from the graph
            node_to = edge[1]
            edge_set.discard(edge)
            # if node_to don't have any remaining incoming edge :
            to_selection = [e for e in edge_set if e[1] == node_to]
            if len(to_selection) == 0 :
                # add node_to to source_set
                source_set.add(node_to)
    if len(edge_set) != 0 :
        raise IndexError # not a direct acyclic graph
    else:
        return node_list


def get_parents(bayes_net_topology, node):
    """
    get_parents: Returns the topological parents of the provided Bayesian node.
    :param bayes_net_topology: The topology of the Bayesian netowrk provided during instantiation.
    :param node: The node for which parents are to be determined.
    :return parents: A list of the parents of the provided node (if any exist); otherwise an empty list.
    """
    parents = []
    for parent, child_list in bayes_net_topology.items():
        if node in child_list:
            parents.append(parent)
    return parents


def enumeration_ask(X,e,bn):
    """
    enumeration_ask: Returns a probability distribution over X.
    :param X: The query variable for which probabilities are to be inferred. For example HighCarValue.
    :param e: The observed values for variables E. For example e:{GoodEngine:True, WorkingAC=False}
    :param bn: A Bayesian Network with variables {X} union E union Y (hidden variables).
    :return norm_dist_x: A normalized probability distribution over the query variable X.
    """
    if len(X) > 1:
        return NotImplementedError
    X = list(X.keys())[0]
    # x_i can only be True or False, no need for a loop:
    # Build keys based on evidence variable and query:
    cpts_query = X + '|'
    logical_query = [1]
    # Q = [P(Q=F|Evidence),P(Q=T|Evidence)]
    Q = [None, None]
    e_x_i = e.copy()
    e_x_i[X] = True
    Q[1] = enumerate_all(variables=bn.bn_vars, e=e_x_i, bn=bn)
    e_x_i[X] = False
    Q[0] = enumerate_all(variables=bn.bn_vars, e=e_x_i, bn=bn)
    # Return the normalization of Q (take each value of Q and divide it by the sum of all the values).
    q_norm = Q.copy()
    for truth_value, probabilty in enumerate(Q):
        q_norm[truth_value] = probabilty / sum(Q)
    return q_norm


def enumerate_all(variables, e, bn):
    """
    enumerate_all: Helper method for enumeration_ask, computes the joint probability distribution of the provided
        variables, given a set of observations.
    :param vars: A list of input variables for which to construct the joint from.
    :param e: A list of observations of the input variables which influence the joint distribution.
    :param cpts: The conditional probability tables for the Bayesian Network.
    :return joint_prob: The joint distribution of the provided 'vars' with the supplied observations 'e'.
    """
    if not variables:
        # Base case, return 1.0
        return 1.0
    # Initially the query variable Y is just the first in the list of query variables.
    Y = variables[0]
    # The rest of the variables are everything but Y:
    rest = variables.copy()
    rest.remove(Y)
    # Does the query variable Y have a known value in the observed evidence variables?
    if Y in e.keys():
        # The query variable Y=y as given in the observed evidence variables:
        y = e[Y]
        # Get the parents of the query variable:
        parents = get_parents(bn.topology, Y)
        cpts_query = Y
        logical_query = [1 if y is True else 0]
        if parents:
            cpts_query = cpts_query + '|'
            for evidence, assignment in e.items():
                if evidence in parents:
                    # Y is assigned a value in e.
                    cpts_query = cpts_query + evidence + ','
                    logical_query.append(1 if assignment is True else 0)
            cpts_query = cpts_query[0:-1]
            try:
                prob_Y_is_y = bn.cpts[cpts_query]
            except KeyError:
                logical_query = [1 if y is True else 0]
                cpts_query = Y + '|'
                reversed_evidence = list(e.items())[::-1]
                for evidence, assignment in reversed_evidence:
                    if evidence in parents:
                        cpts_query = cpts_query + evidence + ','
                        logical_query.append(1 if assignment is True else 0)
                cpts_query = cpts_query[0:-1]
        prob_Y_is_y = bn.cpts[cpts_query]
        if len(logical_query) > 1:
            prob_Y_is_y = prob_Y_is_y[tuple(logical_query)]
        else:
            prob_Y_is_y = prob_Y_is_y[logical_query[0]]
        return prob_Y_is_y * enumerate_all(variables=rest, e=e, bn=bn)
    else:
        # The query variable Y has no observed evidence (y):
        # Build a query for the CPT
        # Sum up over every possible value for Y=y given Y's parents in e:
        y_i = True
        e_y_i = e.copy()
        e_y_i[Y] = y_i
        cpts_query = Y
        logical_query = [1 if y_i is True else 0]
        parents = get_parents(bn.topology, Y)
        prob_Y_is_y = None
        if parents:
            cpts_query = cpts_query + '|'
            # build a cpts query (terms may be out of order due to inconsistent dict ordering during construction).
            # TODO: Use parents to index e? sort e topologically?
            for evidence, assignment in e.items():
                if evidence in parents:
                    cpts_query = cpts_query + evidence + ','
                    logical_query.append(1 if assignment is True else 0)
            cpts_query = cpts_query[0:-1]
            # TODO: Replace this terrible, atrocious code:
            try:
                prob_Y_is_y = bn.cpts[cpts_query]
            except KeyError:
                logical_query = [1 if y_i is True else 0]
                cpts_query = Y + '|'
                reversed_evidence = list(e.items())[::-1]
                for evidence, assignment in reversed_evidence:
                    if evidence in parents:
                        cpts_query = cpts_query + evidence + ','
                        logical_query.append(1 if assignment is True else 0)
                cpts_query = cpts_query[0:-1]
        prob_Y_is_y = bn.cpts[cpts_query]
        if len(logical_query) > 1:
            prob_Y_is_y = prob_Y_is_y[tuple(logical_query)]
        else:
            prob_Y_is_y = prob_Y_is_y[logical_query[0]]
        prob_Y_is_true = prob_Y_is_y * enumerate_all(variables=rest, e=e_y_i, bn=bn)
        logical_query[0] = 0
        y_i = False
        e_y_i[Y] = y_i
        prob_Y_is_y2 = bn.cpts[cpts_query]
        if len(logical_query) > 1:
            prob_Y_is_y2 = bn.cpts[cpts_query][tuple(logical_query)]
        else:
            prob_Y_is_y2 = prob_Y_is_y2[logical_query[0]]
        prob_Y_is_false = prob_Y_is_y2 * enumerate_all(variables=rest, e=e_y_i, bn=bn)
        return sum([prob_Y_is_true, prob_Y_is_false])


def import_data(bns_path, observations_path):
    """
    import_data: Loads the provided topology and observations into memory.
    :param bns_path: The path to a file containing the topology of the Bayesian network.
    :param observations_path: The path to a file containing the observations associated with the Bayesian network.
    :return bns_top, obs: The topology of the Bayesian network (sorted in topographical order) and the
        associated observations.
    """
    with open(bns_path, 'r') as fp:
        bns_with_spaces = json.load(fp=fp)
    with open(observations_path, 'r') as fp:
        obs = pd.read_csv(fp)
    # Strip the spaces from the observations column headers:
    obs.columns = [_.replace(' ', '') for _ in obs.columns]
    # Strip the spaces from the bayes network node names:
    bns_top = {}
    for node, dependencies in bns_with_spaces.items():
        bns_top[node.replace(' ', '')] = [dependent.replace(' ', '') for dependent in dependencies]
    return bns_top, obs


def main():
    # Prompt user for input and answer any queries:
    user_query_verbatim = input("Enter a Query for the Network of the form P(Query={True,False}|{Evidence}):")
    user_query = user_query_verbatim[2:-1]
    query_type = None
    # Determine the type of query:
    if '|' in user_query_verbatim:
        query_type = 'conditional'
    else:
        if user_query_verbatim.count('=') == 1:
            query_type = 'singular'
        elif user_query_verbatim.count(',') > 0:
            query_type = 'joint'
        else:
            print('ERROR: Input Query Malformed. Expected {\'P(A=True)\',\'P(A=False)\'}. Recieved: %s'
                  % user_query_verbatim)
    # Extract query and evidence variables:
    user_query_vars = {}
    user_evidence_vars = {}
    if query_type == 'conditional':
        query_vars = user_query[0:user_query.find('|')]
        user_evidence = user_query[user_query.find('|')+1:]
        user_query_list= query_vars.split(',')
        user_query_list = [query.split('=') for query in user_query_list]
        for var in user_query_list:
            user_query_vars[var[0]] = var[1] == 'True'
        user_evidence_list = user_evidence.split(',')
        user_evidence_list = [obs.split('=') for obs in user_evidence_list]
        for var in user_evidence_list:
            user_evidence_vars[var[0]] = var[1] == 'True'
        distribution = enumeration_ask(X=user_query_vars, e=user_evidence_vars, bn=bns)
        if len(user_query_vars) > 1:
            print("NotImplementedError")
        else:
            x = 1 if list(user_query_vars.values())[0] is True else 0
            print("Enumeration-Ask %s: %s"
                  % (user_query_verbatim, distribution[x]))
    elif query_type == 'joint':
        # There is no query variable:
        user_query_vars = None
        user_evidence_list = user_query.split(',')
        user_evidence_list = [obs.split('=') for obs in user_evidence_list]
        for var in user_evidence_list:
            user_evidence_vars[var[0]] = var[1] == 'True'
        print("Enumerate-All %s): %s"
              % (user_query_verbatim, enumerate_all(variables=bns.bn_vars, e=user_evidence_vars, bn=bns)))
    elif query_type == 'singular':
        # There is no evidence variable:
        user_evidence_vars = None
        user_query_list = user_query.split('=')
        user_query_vars[user_query_list[0]] = user_query_list[1] == 'True'
        # The evidence is the user's query.
        print("Enumerate-All %s): %s"
              % (user_query_verbatim, enumerate_all(variables=bns.bn_vars, e=user_query_vars, bn=bns)))
    else:
        print("Query Type Identification Error: The provided input query \'%s\' may be malformed.\n"
              "\tExpected: a query of type {joint,conditional,singular}.\n\tReceived: a query of type UNKNOWN."
              % user_query_verbatim)
        exit(-1)


def logarithmic_likelihood(model, data):
    ''' Compute P(Data|Model) '''
    prob_data_given_model = 0
    for i in range(len(data)):
        df_series = data.loc[i]
        evidence_vars = {}
        for variable, assignment in df_series.items():
            evidence_vars[variable] = assignment
            prob_data_given_model += np.log(enumerate_all(variables=model.bn_vars, e=evidence_vars, bn=model))
    return prob_data_given_model

if __name__ == '__main__':
    bns_topology = None
    observations = None
    ''' Perform Initial Setup and Read in Network Topology and Observations '''
    bn_one_path = 'bn1.json'
    observations_one_path = 'data1.csv'
    bn_two_path = 'bn2.json'
    observations_two_path = 'data2.csv'
    model_one_path = 'model1.json'
    model_two_path = 'model2.json'
    model_three_path = 'model3.json'
    obs_three_path = 'data3.csv'
    obs_four_path = 'data4.csv'
    obs_five_path = 'data5.csv'
    ''' Load Bayesian Network Topology and Empirical Observations '''
    user_option_verbatim = input("Select an Option:\n\t"
                                 "[1] Query the Bayesian Network.\n\t"
                                 "[2] Compute the Log-Likelihood for model-data pairs.\n")
    if user_option_verbatim == "1":
        user_bns_verbatim = input("Select a Bayesian Network to Query:\n\t"
                              "[1]: <bn1.json> {HighMileage,GoodEngine,WorkingAirConditioner,HighCarValue}\n\t"
                              "[2]: <bn2.json> {BadBattery,EmptyFuel,EmptyGauge,NoStart}\n")
        if user_bns_verbatim == "1":
            bns_topology, observations = import_data(bns_path=bn_one_path, observations_path=observations_one_path)
        elif user_bns_verbatim == "2":
            bns_topology, observations = import_data(bns_path=bn_two_path, observations_path=observations_two_path)
        else:
            print("Error: Malformed selection. Expected a BNS Id: {1,2}. User Provided: %s" % user_bns_verbatim)
            exit(-1)
    elif user_option_verbatim == "2":
        print("Now calculating the Log-Likelihood for each Model-Data pair, please stand by...")
        ''' Log-Likelihood'''
        obs_paths = ['data3.csv','data4.csv','data5.csv']
        models = ['model1.json', 'model2.json', 'model3.json']
        for i, obs in enumerate(obs_paths):
            for j, model in enumerate(models):
                bns_topology, observations = import_data(bns_path=model, observations_path=obs)
                bns = BayesNetwork(bayes_net_topology=bns_topology, observations=observations)
                bns.cpts = _get_cpts(bayes_net_topology=bns_topology, observations=observations)
                # For convenience sake, store the bayes net variables in topographical ordering:
                edge_list = []
                for parent, child_list in bns_topology.items():
                    for child in child_list:
                        edge_list.append([parent, child])
                # Assign topological ordering to Bayes Network Instance:
                bns.bn_vars = sort_direct_acyclic_graph(edge_list=edge_list)
                ''' Compute Log Likelihoods '''
                log_likelihood = logarithmic_likelihood(model=bns, data=observations)
                print("Log-Likelihood P(Data=%s|Model=%s): %.2f" % (obs, model, log_likelihood))
        exit(0)
    else:
        print("Error: Malformed selection. Expected an integer: {1,2}. User Provided: %s" % user_option_verbatim)
        exit(-1)
    ''' Initialize the Bayesian Network '''
    # Initialize the Bayes Network with the observations data frame and the topology of the network:
    bns = BayesNetwork(bayes_net_topology=bns_topology, observations=observations)
    # Instantiate the conditional probability tables associated with the network:
    bns.cpts = _get_cpts(bayes_net_topology=bns_topology, observations=observations)
    # For convenience sake, store the bayes net variables in topographical ordering:
    edge_list = []
    for parent, child_list in bns_topology.items():
            for child in child_list:
                edge_list.append([parent, child])
    # Assign topological ordering to Bayes Network Instance:
    bns.bn_vars = sort_direct_acyclic_graph(edge_list=edge_list)
    # Perform queries on the Bayesian Network:
    main()
