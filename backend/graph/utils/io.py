import json
import pickle
from pathlib import Path

def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data, filepath):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def save_graph(graph, filepath):
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("wb") as f:
        pickle.dump(graph, f)


def load_graph(filepath):
    with Path(filepath).open("rb") as f:
        return pickle.load(f)
