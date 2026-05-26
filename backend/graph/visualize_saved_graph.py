from utils.io import load_graph
from utils.visualization import visualize_graph


GRAPH_INPUT_FILE = "backend/graph/data/latest_graph.pkl"
HTML_OUTPUT_FILE = "graph.html"


if __name__ == "__main__":

    G = load_graph(GRAPH_INPUT_FILE)

    visualize_graph(
        G,
        output_file=HTML_OUTPUT_FILE
    )

    print(f"Graph visualized from {GRAPH_INPUT_FILE} to {HTML_OUTPUT_FILE}")
