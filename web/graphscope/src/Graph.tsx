import { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import type { Core } from 'cytoscape';
import type { Atlas } from './data';
import { neighborsOf } from './data';

type Props = { data: Atlas; selected: number | null; onSelect: (id: number) => void; visible?: number[]; compact?: boolean };

export function Graph({ data, selected, onSelect, visible, compact = false }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const cy = useRef<Core | null>(null);
  const choose = useRef(onSelect);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  choose.current = onSelect;
  useEffect(() => {
    if (!container.current) return;
    try {
      const graph = cytoscape({
        container: container.current, minZoom: 0.03, maxZoom: 5, hideEdgesOnViewport: true,
        elements: [
          ...data.nodes.map((node, i) => ({ data: { id: String(node.id), target: node.target ? 1 : 0 },
            position: { x: Math.cos(i * 2.39996) * Math.sqrt(i) * 18, y: Math.sin(i * 2.39996) * Math.sqrt(i) * 18 } })),
          ...data.edges.map(e => ({ data: { id: `e${e.source}-${e.target}`, source: String(e.source), target: String(e.target) } })),
        ],
        style: [
          { selector: 'node', style: { 'background-color': '#aaa398', width: 12, height: 12, 'border-width': 0 } },
          { selector: 'node[target = 1]', style: { 'background-color': '#b45b40', width: 22, height: 22 } },
          { selector: 'edge', style: { width: 1.8, 'line-color': '#b8ae9f', opacity: 0.7, 'curve-style': 'haystack' } },
          { selector: '.dim', style: { opacity: 0.1 } },
          { selector: '.match', style: { 'border-width': 2, 'border-color': '#244f50' } },
          { selector: '.near', style: { 'background-color': '#3f7372', 'border-width': 3, 'border-color': '#f7f5ef', width: 24, height: 24, opacity: 1 } },
          { selector: '.incident', style: { 'line-color': '#477875', width: 3.5, opacity: 1 } },
          { selector: '.focus', style: { 'background-color': '#a6402a', width: 32, height: 32, 'border-width': 6, 'border-color': '#f1d9ca', label: 'data(id)', color: '#302e29', 'font-size': 24, 'text-margin-y': -14, 'text-valign': 'top', 'text-background-color': '#f7f5ef', 'text-background-opacity': 0.9, 'text-background-padding': '3px', opacity: 1 } },
        ],
        // Large topology uses deterministic display positions; avoid quadratic force-layout work.
        layout: { name: data.nodes.length > 1000 ? 'preset' : 'cose', animate: false, randomize: false, nodeRepulsion: () => 9000, idealEdgeLength: () => 65,
          componentSpacing: 42, numIter: 500, padding: compact ? 12 : 34 },
      });
      cy.current = graph;
      graph.on('tap', 'node', event => choose.current(Number(event.target.id())));
      graph.on('mouseover', 'node', event => {
        graph.elements().removeClass('near incident');
        event.target.closedNeighborhood().nodes().addClass('near');
        event.target.connectedEdges().addClass('incident');
      });
      graph.on('mouseout', 'node', () => graph.elements().removeClass('near incident'));
      const observer = new ResizeObserver(() => { graph.resize(); graph.fit(undefined, compact ? 14 : 34); });
      observer.observe(container.current);
      setReady(true);
      return () => { observer.disconnect(); graph.destroy(); cy.current = null; };
    } catch {
      setFailed(true);
    }
  }, [data, compact]);
  useEffect(() => {
    const graph = cy.current;
    if (!graph) return;
    graph.elements().removeClass('focus');
    if (selected !== null) graph.getElementById(String(selected)).addClass('focus');
  }, [selected, ready]);
  useEffect(() => {
    const graph = cy.current;
    if (!graph) return;
    graph.elements().removeClass('dim match');
    if (visible && visible.length !== data.nodes.length) {
      const ids = new Set(visible.map(String));
      graph.nodes().forEach(n => { n.addClass(ids.has(n.id()) ? 'match' : 'dim'); });
      graph.edges().forEach(e => { if (!ids.has(e.source().id()) && !ids.has(e.target().id())) e.addClass('dim'); });
    }
  }, [visible, data.nodes.length, ready]);
  const reset = () => { cy.current?.fit(undefined, 34); cy.current?.elements().removeClass('near incident'); };
  return <div className={`graph-frame ${compact ? 'compact' : ''}`}>
    <div ref={container} className="graph-canvas" role="region" aria-label="Cora topology graph. Use node list for accessible selection."
      tabIndex={0} onKeyDown={event => {
        if (event.key === '+' || event.key === '=') cy.current?.zoom(cy.current.zoom() * 1.2);
        if (event.key === '-') cy.current?.zoom(cy.current.zoom() / 1.2);
        if (event.key === 'Home') reset();
        if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
          event.preventDefault();
          const adjacent = selected === null ? [] : neighborsOf(data, selected);
          const next = event.key === 'ArrowRight' ? adjacent[0] : adjacent.at(-1);
          if (next !== undefined) onSelect(next);
        }
      }} />
    {!ready && !failed && <div className="graph-message" role="status">Arranging recorded evidence…</div>}
    {failed && <div className="graph-message" role="alert">Graph could not load. Use the node list to inspect all recorded evidence.</div>}
    <div className="graph-watermark"><span>CORA / GLOBAL NODE IDS</span><span>DISPLAY LAYOUT</span></div>
    <div className="graph-controls" aria-label="Graph controls">
      <button aria-label="Zoom in" onClick={() => cy.current?.zoom(cy.current.zoom() * 1.3)}>+</button>
      <button aria-label="Zoom out" onClick={() => cy.current?.zoom(cy.current.zoom() / 1.3)}>−</button>
      <button onClick={() => cy.current?.fit(undefined, 34)}>Fit</button>
      {!compact && <button onClick={reset}>Reset</button>}
    </div>
    {!compact && <p className="graph-hint">Drag to pan · Scroll to zoom · Select to inspect</p>}
  </div>;
}
