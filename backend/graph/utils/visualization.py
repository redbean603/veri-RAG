from pyvis.network import Network
from utils.logger import get_logger
import networkx as nx

logger = get_logger(__name__)

def visualize_graph(G, output_file="graph.html"):
    """
    NetworkX 그래프를 PyVis를 이용하여 HTML로 시각화합니다.
    """
    logger.info(f"Generating graph visualization: {output_file}...")
    
    # PyVis 네트워크 객체 생성 (노트북 환경이 아님)
    net = Network(height="750px", width="100%", bgcolor="#222222", font_color="white", directed=True)
    
    # 물리 엔진 설정 적용 (스프링 모델)
    net.force_atlas_2based()
    
    # NetworkX 그래프 노드와 엣지 추가
    # 각 타입에 따른 색상이나 형태 등을 부여할 수 있습니다
    for node_id, data in G.nodes(data=True):
        node_type = data.get("type", "Unknown")
        label = data.get("name", str(node_id))
        title = f"[{node_type}] {label}\n{data.get('desc', '')}"
        
        # 타입별 색상 매핑
        color_map = {
            "Industry": "#FFD700", # Gold
            "Company": "#1E90FF",  # DodgerBlue
            "Person": "#FF69B4",   # HotPink
            "Org": "#32CD32",      # LimeGreen
            "Policy": "#FFA500",   # Orange
            "Event": "#8A2BE2",    # BlueViolet
            "Asset": "#00CED1",    # DarkTurquoise
            "News": "#FF4500",     # OrangeRed
            "Claim": "#DC143C",    # Crimson
            "Source": "#A9A9A9",   # DarkGray
            "Image": "#DDA0DD"     # Plum
        }
        color = color_map.get(node_type, "#97C2FC")
        
        net.add_node(node_id, label=label, title=title, color=color, group=node_type)
        
    for source, target, edge_data in G.edges(data=True):
        rel = edge_data.get("relation", edge_data.get("rel", ""))
        title = str(edge_data) # 엣지의 추가 속성을 호버로 볼 수 있게
        net.add_edge(source, target, label=rel, title=title)
        
    # 물리 시뮬레이션 버튼 표시 옵션
    net.show_buttons(filter_=['physics'])
    
    # HTML 저장
    net.write_html(output_file)
    logger.info(f"✅ 시각화 완료! 파일이 저장되었습니다: {output_file}")
