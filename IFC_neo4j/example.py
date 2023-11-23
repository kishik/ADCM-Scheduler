import pickle

from ifc_explorer import IfcToNxExplorer
from nxtoneo4jexplorer import NxToNeo4jExplorer

if __name__ == "__main__":
    ifc_exp = IfcToNxExplorer()
    ifc_exp.create_net_graph("dou/AR.ifc")
    # pickle.dump(exp.get_net_graph(), open('exp_AR.pickle', 'wb'))
    # G = pickle.load(open('exp_AR.pickle', 'rb'))

    neo4j_exp = NxToNeo4jExplorer()
    # G = pickle.load(open('exp_AR.pickle', 'rb'))
    # print(G.nodes[104])

    G = ifc_exp.get_net_graph()
    neo4j_exp.create_neo4j(G)
    neo4j_exp.connect_chains()
