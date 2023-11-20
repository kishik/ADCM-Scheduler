import pandas as pd

from create_group_graph import create_group_graph
from ifc_to_nx_converter import IfcToNxConverter
from nx_to_neo4j_converter import NxToNeo4jConverter

if __name__ == "__main__":
    create_group_graph()

    nx_exp = IfcToNxConverter()
    # nx_exp.create_net_graph("../Amundsena_IFC_24/АР_Амундсена_Син_R22.ifc")
    path = "C:\\Users\\naumo\\PycharmProjects\\IFC_test\\Amundsena_IFC_24"
    nx_exp.create_net_graph(path)
    G = nx_exp.get_net_graph()

    neo4j_exp = NxToNeo4jConverter()
    neo4j_exp.create_neo4j(G)

    node_df = pd.DataFrame(neo4j_exp.get_nodes())
    edge_df = pd.DataFrame(neo4j_exp.get_edges())
    with pd.ExcelWriter('../result/new.xlsx', engine='openpyxl') as writer:
        node_df.to_excel(writer, sheet_name="Работы", index=False)
        edge_df.to_excel(writer, sheet_name="Связи", index=False)

    neo4j_exp.close()