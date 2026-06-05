import pickle

with open("/Users/jangbinlee/Desktop/Projects/Veri-RAG/backend/graph/data/latest_graph.pkl", "rb") as f:
    graph = pickle.load(f)

print(type(graph))

G = graph

print("nodes:", G.number_of_nodes())
print("edges:", G.number_of_edges())

node = list(G.nodes(data=True))[0]
print(node)

edge = list(G.edges(data=True))[0]
print(edge)