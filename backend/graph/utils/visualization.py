
import html
import json
import logging
 
logger = logging.getLogger(__name__)
 
 
def dict_to_html(data: dict) -> str:
    lines = []
    for k, v in data.items():
        if isinstance(v, list) and len(v) > 5:
            v = v[:5] + ["..."]
        lines.append(
            f"<b>{html.escape(str(k))}</b>: "
            f"{html.escape(str(v))}"
        )
    return "<br>".join(lines)
 
 
def visualize_graph(G, output_file="graph.html"):
    """
    NetworkX 그래프를 향상된 UI의 HTML로 시각화합니다.
    """
    logger.info(f"Generating graph visualization: {output_file}...")
 
    # --------------------------------------------------
    # Node color & icon map
    # --------------------------------------------------
    NODE_STYLES = {
        "Industry": {"color": "#F59E0B", "bg": "#FEF3C7", "icon": "🏭"},
        "Company":  {"color": "#3B82F6", "bg": "#DBEAFE", "icon": "🏢"},
        "Person":   {"color": "#EC4899", "bg": "#FCE7F3", "icon": "👤"},
        "Org":      {"color": "#10B981", "bg": "#D1FAE5", "icon": "🏛"},
        "Policy":   {"color": "#F97316", "bg": "#FFEDD5", "icon": "📜"},
        "Event":    {"color": "#8B5CF6", "bg": "#EDE9FE", "icon": "📅"},
        "Asset":    {"color": "#06B6D4", "bg": "#CFFAFE", "icon": "💎"},
        "News":     {"color": "#EF4444", "bg": "#FEE2E2", "icon": "📰"},
        "Claim":    {"color": "#DC2626", "bg": "#FEE2E2", "icon": "💬"},
        "Source":   {"color": "#6B7280", "bg": "#F3F4F6", "icon": "📎"},
        "Image":    {"color": "#A78BFA", "bg": "#EDE9FE", "icon": "🖼"},
    }
    DEFAULT_STYLE = {"color": "#64748B", "bg": "#F1F5F9", "icon": "⬡"}
 
    # --------------------------------------------------
    # Serialize graph data for JS
    # --------------------------------------------------
    nodes_data = []
    for node_id, data in G.nodes(data=True):
        node_type = data.get("type", "Unknown")
        label = data.get("name", str(node_id))
        style = NODE_STYLES.get(node_type, DEFAULT_STYLE)
        tooltip = dict_to_html({"id": node_id, **data})
 
        nodes_data.append({
            "id": str(node_id),
            "label": label,
            "type": node_type,
            "color": style["color"],
            "bg": style["bg"],
            "icon": style["icon"],
            "tooltip": tooltip,
        })
 
    edges_data = []
    for source, target, edge_data in G.edges(data=True):
        relation = edge_data.get("relation", edge_data.get("rel", ""))
        effect = edge_data.get("current_state", edge_data.get("effect", ""))
        tooltip = dict_to_html({"source": source, "target": target, **edge_data})
 
        if effect in ("active", "strengthening", "positive"):
            edge_color = "#10B981"
            edge_style = "solid"
        elif effect in ("weakening", "negative"):
            edge_color = "#EF4444"
            edge_style = "dashed"
        elif effect == "inactive":
            edge_color = "#9CA3AF"
            edge_style = "dotted"
        else:
            edge_color = "#CBD5E1"
            edge_style = "solid"

        edges_data.append({
            "id": f"edge-{len(edges_data)}",
            "from": str(source),
            "to": str(target),
            "label": relation,
            "color": edge_color,
            "style": edge_style,
            "tooltip": tooltip,
        })
 
    nodes_json = json.dumps(nodes_data, ensure_ascii=False)
    edges_json = json.dumps(edges_data, ensure_ascii=False)
 
    node_types = sorted(set(n["type"] for n in nodes_data))
    legend_items = ""
    for t in node_types:
        style = NODE_STYLES.get(t, DEFAULT_STYLE)
        legend_items += (
            f'<div class="legend-item" data-type="{html.escape(t)}">'
            f'<span class="legend-dot" style="background:{style["color"]}"></span>'
            f'<span class="legend-icon">{style["icon"]}</span>'
            f'<span class="legend-label">{html.escape(t)}</span>'
            f'</div>\n'
        )
 
    # --------------------------------------------------
    # HTML template
    # --------------------------------------------------
    html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Knowledge Graph</title>
<script src="https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js"></script>
<style>
  :root {{
    --bg: #0F1117;
    --surface: #1A1D27;
    --surface2: #22263A;
    --border: rgba(255,255,255,0.08);
    --border2: rgba(255,255,255,0.14);
    --text: #E2E8F0;
    --text2: #94A3B8;
    --text3: #64748B;
    --accent: #6366F1;
    --accent2: #818CF8;
    --radius: 12px;
    --radius-sm: 8px;
    --shadow: 0 4px 24px rgba(0,0,0,0.4);
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    background: var(--bg);
    color: var(--text);
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }}
 
  /* ── Header ── */
  header {{
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 0 20px;
    height: 56px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
    z-index: 10;
  }}
  .logo {{
    width: 30px; height: 30px;
    background: linear-gradient(135deg, var(--accent), #A78BFA);
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 14px;
  }}
  .title {{ font-size: 15px; font-weight: 600; letter-spacing: -0.01em; }}
  .subtitle {{ font-size: 12px; color: var(--text2); margin-left: 4px; }}
  .header-right {{ margin-left: auto; display: flex; align-items: center; gap: 8px; }}
  .stat-badge {{
    padding: 4px 10px;
    border-radius: 20px;
    background: var(--surface2);
    border: 1px solid var(--border);
    font-size: 12px;
    color: var(--text2);
  }}
  .stat-badge strong {{ color: var(--text); font-weight: 600; }}
 
  /* ── Layout ── */
  .workspace {{
    flex: 1;
    display: flex;
    overflow: hidden;
    position: relative;
  }}
 
  /* ── Sidebar ── */
  .sidebar {{
    width: 240px;
    background: var(--surface);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
    overflow: hidden;
  }}
  .sidebar-section {{
    padding: 14px 16px 10px;
    border-bottom: 1px solid var(--border);
  }}
  .sidebar-label {{
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text3);
    margin-bottom: 10px;
  }}
 
  /* Search */
  .search-wrap {{
    position: relative;
  }}
  .search-icon {{
    position: absolute;
    left: 10px; top: 50%;
    transform: translateY(-50%);
    font-size: 13px;
    color: var(--text3);
    pointer-events: none;
  }}
  #search {{
    width: 100%;
    padding: 7px 10px 7px 30px;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    color: var(--text);
    font-size: 13px;
    outline: none;
    transition: border-color .2s;
  }}
  #search:focus {{ border-color: var(--accent2); }}
  #search::placeholder {{ color: var(--text3); }}
 
  /* Legend */
  .legend {{
    padding: 8px 16px;
    overflow-y: auto;
    flex-shrink: 0;
  }}
  .legend-item {{
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 5px 8px;
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: background .15s;
    user-select: none;
  }}
  .legend-item:hover {{ background: var(--surface2); }}
  .legend-item.active {{ background: var(--surface2); }}
  .legend-item.dimmed {{ opacity: 0.35; }}
  .legend-dot {{
    width: 10px; height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
  }}
  .legend-icon {{ font-size: 13px; }}
  .legend-label {{ font-size: 13px; color: var(--text2); flex: 1; }}
  .legend-count {{
    font-size: 11px;
    color: var(--text3);
    background: var(--surface);
    padding: 1px 6px;
    border-radius: 10px;
    border: 1px solid var(--border);
  }}
 
  /* Physics controls */
  .controls {{
    padding: 12px 16px;
    border-top: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    gap: 10px;
  }}
  .control-row {{
    display: flex;
    align-items: center;
    gap: 8px;
    justify-content: space-between;
  }}
  .control-label {{ font-size: 12px; color: var(--text2); }}
  input[type=range] {{
    -webkit-appearance: none;
    height: 4px;
    border-radius: 2px;
    background: var(--surface2);
    outline: none;
    cursor: pointer;
    flex: 1;
  }}
  input[type=range]::-webkit-slider-thumb {{
    -webkit-appearance: none;
    width: 14px; height: 14px;
    border-radius: 50%;
    background: var(--accent2);
    cursor: pointer;
  }}
  .btn-small {{
    padding: 5px 12px;
    border-radius: var(--radius-sm);
    background: var(--surface2);
    border: 1px solid var(--border);
    color: var(--text2);
    font-size: 12px;
    cursor: pointer;
    transition: all .15s;
    white-space: nowrap;
  }}
  .btn-small:hover {{ border-color: var(--border2); color: var(--text); }}
  .btn-row {{
    display: flex;
    gap: 6px;
  }}
 
  /* ── Canvas ── */
  #graph-canvas {{
    flex: 1;
    background: var(--bg);
    position: relative;
  }}
  #graph {{ width: 100%; height: 100%; }}
 
  /* ── Tooltip ── */
  #tooltip {{
    position: fixed;
    background: var(--surface);
    border: 1px solid var(--border2);
    border-radius: var(--radius);
    padding: 12px 14px;
    font-size: 12.5px;
    line-height: 1.6;
    color: var(--text2);
    max-width: 280px;
    box-shadow: var(--shadow);
    pointer-events: none;
    opacity: 0;
    transform: translateY(4px);
    transition: opacity .15s, transform .15s;
    z-index: 999;
  }}
  #tooltip.visible {{ opacity: 1; transform: translateY(0); }}
  #tooltip b {{ color: var(--text); }}
 
  /* ── Info panel (selected node) ── */
  #info-panel {{
    position: absolute;
    bottom: 20px;
    right: 20px;
    width: 260px;
    background: var(--surface);
    border: 1px solid var(--border2);
    border-radius: var(--radius);
    padding: 16px;
    box-shadow: var(--shadow);
    opacity: 0;
    transform: translateY(8px);
    transition: opacity .2s, transform .2s;
    pointer-events: none;
    z-index: 100;
  }}
  #info-panel.visible {{ opacity: 1; transform: translateY(0); pointer-events: all; }}
  .info-type {{
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 4px;
  }}
  .info-name {{
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 10px;
    word-break: break-word;
  }}
  .info-row {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding: 4px 0;
    border-bottom: 1px solid var(--border);
    font-size: 12px;
  }}
  .info-row:last-child {{ border-bottom: none; }}
  .info-key {{ color: var(--text3); }}
  .info-val {{ color: var(--text2); text-align: right; max-width: 140px; word-break: break-word; }}
  .info-close {{
    position: absolute;
    top: 12px; right: 12px;
    background: none; border: none;
    color: var(--text3); font-size: 16px;
    cursor: pointer; line-height: 1;
    transition: color .15s;
  }}
  .info-close:hover {{ color: var(--text); }}
 
  /* ── Mini-map placeholder ── */
  #minimap {{
    position: absolute;
    bottom: 20px;
    left: 260px;
    width: 140px;
    height: 90px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    opacity: 0.7;
    pointer-events: none;
    z-index: 50;
  }}
</style>
</head>
<body>
 
<!-- Header -->
<header>
  <div class="logo">🕸</div>
  <span class="title">Knowledge Graph</span>
  <span class="subtitle">Interactive Explorer</span>
  <div class="header-right">
    <span class="stat-badge">Nodes <strong id="node-count">0</strong></span>
    <span class="stat-badge">Edges <strong id="edge-count">0</strong></span>
    <span class="stat-badge" id="selected-badge" style="display:none">
      Selected <strong id="selected-count">0</strong>
    </span>
  </div>
</header>
 
<div class="workspace">
 
  <!-- Sidebar -->
  <div class="sidebar">
 
    <div class="sidebar-section">
      <div class="sidebar-label">Search</div>
      <div class="search-wrap">
        <span class="search-icon">🔍</span>
        <input type="text" id="search" placeholder="노드 이름 검색...">
      </div>
    </div>
 
    <div class="sidebar-section" style="padding-bottom:4px">
      <div class="sidebar-label">Node Types</div>
    </div>
    <div class="legend" id="legend">
      {legend_items}
    </div>
 
    <div class="controls">
      <div class="sidebar-label" style="margin-bottom:2px">Layout & Physics</div>
      <div class="control-row">
        <span class="control-label">Repulsion</span>
        <input type="range" id="repulsion" min="-500" max="-50" value="-200">
      </div>
      <div class="control-row">
        <span class="control-label">Spring</span>
        <input type="range" id="spring" min="1" max="300" value="100">
      </div>
      <div class="control-row">
        <span class="control-label">Damping</span>
        <input type="range" id="damping" min="1" max="100" value="60">
      </div>
      <div class="btn-row">
        <button class="btn-small" onclick="fitGraph()">⊞ Fit</button>
        <button class="btn-small" onclick="freezeGraph()">❄ Freeze</button>
        <button class="btn-small" onclick="resetGraph()">↺ Reset</button>
      </div>
    </div>
 
  </div>
 
  <!-- Graph Canvas -->
  <div id="graph-canvas">
    <div id="graph"></div>
  </div>
 
</div>
 
<!-- Tooltip -->
<div id="tooltip"></div>
 
<!-- Info Panel -->
<div id="info-panel">
  <button class="info-close" onclick="closeInfo()">×</button>
  <div class="info-type" id="info-type"></div>
  <div class="info-name" id="info-name"></div>
  <div id="info-rows"></div>
</div>
 
<script>
const NODES_DATA = {nodes_json};
const EDGES_DATA = {edges_json};
 
// ── Build vis-network datasets ──────────────────────────────────────
const nodeMap = {{}};
NODES_DATA.forEach(n => {{ nodeMap[n.id] = n; }});
const edgeMap = {{}};
EDGES_DATA.forEach(e => {{ edgeMap[e.id] = e; }});
 
function makeVisNode(n, dimmed) {{
  const opacity = dimmed ? 0.2 : 1;
  return {{
    id: n.id,
    label: n.label.length > 20 ? n.label.slice(0,18)+'…' : n.label,
    color: {{
      background: n.bg,
      border: n.color,
      highlight: {{ background: n.bg, border: n.color }},
      hover: {{ background: n.bg, border: n.color }},
    }},
    font: {{
      color: n.color,
      size: 12,
      face: '-apple-system, system-ui, sans-serif',
    }},
    borderWidth: 2,
    borderWidthSelected: 3,
    shape: 'dot',
    size: 14,
    opacity: opacity,
    _raw: n,
  }};
}}
 
function makeVisEdge(e) {{
  return {{
    id: e.id,
    from: e.from,
    to: e.to,
    label: e.label || '',
    color: {{ color: e.color, highlight: e.color, hover: e.color }},
    dashes: e.style === 'dashed' ? [6,3] : (e.style === 'dotted' ? [2,4] : false),
    arrows: {{ to: {{ enabled: true, scaleFactor: 0.6 }} }},
    font: {{ color: '#94A3B8', size: 10, align: 'middle', strokeWidth: 0 }},
    width: 1.5,
    smooth: {{ type: 'curvedCW', roundness: 0.1 }},
  }};
}}
 
const visNodes = new vis.DataSet(NODES_DATA.map(n => makeVisNode(n, false)));
const visEdges = new vis.DataSet(EDGES_DATA.map(e => makeVisEdge(e)));
 
// ── Network options ─────────────────────────────────────────────────
const options = {{
  physics: {{
    solver: 'forceAtlas2Based',
    forceAtlas2Based: {{
      gravitationalConstant: -200,
      springLength: 100,
      springConstant: 0.05,
      damping: 0.6,
      avoidOverlap: 0.5,
    }},
    stabilization: {{ iterations: 200, updateInterval: 30 }},
  }},
  interaction: {{
    hover: true,
    tooltipDelay: 150,
    zoomView: true,
    dragView: true,
  }},
  nodes: {{
    chosen: true,
  }},
  edges: {{
    chosen: true,
  }},
}};
 
const container = document.getElementById('graph');
const network = new vis.Network(container, {{ nodes: visNodes, edges: visEdges }}, options);
 
// ── Update stats ────────────────────────────────────────────────────
document.getElementById('node-count').textContent = NODES_DATA.length;
document.getElementById('edge-count').textContent = EDGES_DATA.length;
 
// Update legend counts
const typeCounts = {{}};
NODES_DATA.forEach(n => {{ typeCounts[n.type] = (typeCounts[n.type] || 0) + 1; }});
document.querySelectorAll('.legend-item').forEach(el => {{
  const t = el.dataset.type;
  if (typeCounts[t]) {{
    const badge = document.createElement('span');
    badge.className = 'legend-count';
    badge.textContent = typeCounts[t];
    el.appendChild(badge);
  }}
}});
 
// ── Tooltip ─────────────────────────────────────────────────────────
const tooltip = document.getElementById('tooltip');

function showTooltip(title, body) {{
  tooltip.innerHTML = `<b>${{title}}</b><br>${{body}}`;
  tooltip.classList.add('visible');
}}

function hideTooltip() {{
  tooltip.classList.remove('visible');
}}

network.on('hoverNode', e => {{
  const n = nodeMap[e.node];
  if (!n) return;
  showTooltip(n.type, n.tooltip);
}});
network.on('blurNode', hideTooltip);
network.on('hoverEdge', e => {{
  const edge = edgeMap[e.edge];
  if (!edge) return;
  showTooltip(edge.label || 'Relation', edge.tooltip);
}});
network.on('blurEdge', hideTooltip);
document.addEventListener('mousemove', e => {{
  tooltip.style.left = (e.clientX + 16) + 'px';
  tooltip.style.top  = (e.clientY - 10) + 'px';
}});
 
// ── Info Panel ──────────────────────────────────────────────────────
network.on('click', params => {{
  if (params.nodes.length) {{
    const n = nodeMap[params.nodes[0]];
    if (n) showInfo(n);
  }} else {{
    closeInfo();
  }}
}});
 
function showInfo(n) {{
  document.getElementById('info-type').textContent = n.type;
  document.getElementById('info-type').style.color = n.color;
  document.getElementById('info-name').textContent = n.label;
  const rows = document.getElementById('info-rows');
  rows.innerHTML = '';
  const raw = n._raw || n;
  Object.entries(raw).forEach(([k, v]) => {{
    if (['id','label','type','color','bg','icon','tooltip'].includes(k)) return;
    const row = document.createElement('div');
    row.className = 'info-row';
    let display = Array.isArray(v) ? v.slice(0,4).join(', ') + (v.length>4?' …':'') : String(v);
    row.innerHTML = `<span class="info-key">${{k}}</span><span class="info-val">${{display}}</span>`;
    rows.appendChild(row);
  }});
  document.getElementById('info-panel').classList.add('visible');
  const deg = network.getConnectedEdges(n.id).length;
  const row = document.createElement('div');
  row.className = 'info-row';
  row.innerHTML = `<span class="info-key">connections</span><span class="info-val">${{deg}}</span>`;
  rows.appendChild(row);
}}
 
function closeInfo() {{
  document.getElementById('info-panel').classList.remove('visible');
}}
 
// ── Search ──────────────────────────────────────────────────────────
document.getElementById('search').addEventListener('input', function() {{
  const q = this.value.toLowerCase().trim();
  if (!q) {{
    visNodes.update(NODES_DATA.map(n => ({{ id: n.id, opacity: 1 }})));
    return;
  }}
  const matches = new Set(NODES_DATA.filter(n =>
    n.label.toLowerCase().includes(q) || n.type.toLowerCase().includes(q)
  ).map(n => n.id));
  visNodes.update(NODES_DATA.map(n => ({{ id: n.id, opacity: matches.has(n.id) ? 1 : 0.1 }})));
  if (matches.size) network.selectNodes([...matches]);
}});
 
// ── Legend filter ────────────────────────────────────────────────────
const activeFilters = new Set();
document.querySelectorAll('.legend-item').forEach(el => {{
  el.addEventListener('click', () => {{
    const t = el.dataset.type;
    if (activeFilters.has(t)) {{
      activeFilters.delete(t);
      el.classList.remove('active');
    }} else {{
      activeFilters.add(t);
      el.classList.add('active');
    }}
    applyFilter();
  }});
}});
 
function applyFilter() {{
  if (!activeFilters.size) {{
    visNodes.update(NODES_DATA.map(n => ({{ id: n.id, opacity: 1 }})));
    document.querySelectorAll('.legend-item').forEach(el => el.classList.remove('dimmed'));
    return;
  }}
  const shown = new Set(NODES_DATA.filter(n => activeFilters.has(n.type)).map(n => n.id));
  visNodes.update(NODES_DATA.map(n => ({{ id: n.id, opacity: shown.has(n.id) ? 1 : 0.08 }})));
  document.querySelectorAll('.legend-item').forEach(el => {{
    el.classList.toggle('dimmed', !activeFilters.has(el.dataset.type));
  }});
}}
 
// ── Physics sliders ──────────────────────────────────────────────────
document.getElementById('repulsion').addEventListener('input', function() {{
  network.setOptions({{ physics: {{ forceAtlas2Based: {{ gravitationalConstant: +this.value }} }} }});
}});
document.getElementById('spring').addEventListener('input', function() {{
  network.setOptions({{ physics: {{ forceAtlas2Based: {{ springLength: +this.value }} }} }});
}});
document.getElementById('damping').addEventListener('input', function() {{
  network.setOptions({{ physics: {{ forceAtlas2Based: {{ damping: this.value/100 }} }} }});
}});
 
// ── Buttons ──────────────────────────────────────────────────────────
let frozen = false;
function fitGraph() {{ network.fit({{ animation: {{ duration: 500, easingFunction: 'easeInOutQuad' }} }}); }}
function freezeGraph() {{
  frozen = !frozen;
  network.setOptions({{ physics: {{ enabled: !frozen }} }});
  document.querySelector('.btn-small:nth-child(2)').textContent = frozen ? '▶ Unfreeze' : '❄ Freeze';
}}
function resetGraph() {{
  network.setOptions({{ physics: {{ enabled: true }} }});
  frozen = false;
  document.querySelector('.btn-small:nth-child(2)').textContent = '❄ Freeze';
  network.stabilize(150);
  setTimeout(fitGraph, 800);
}}
</script>
</body>
</html>"""
 
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)
 
    logger.info(f"✅ 시각화 완료! 파일이 저장되었습니다: {output_file}")
