import { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import type { Core } from 'cytoscape';
import type { Atlas } from './data';
import { neighborsOf } from './data';
import { loadLayout } from './layout-data';

const views=new Map<string,{zoom:number;pan:{x:number;y:number}}>();

type Props = { data: Atlas; selected: number | null; onSelect: (id: number) => void; visible?: number[]; compact?: boolean; statuses?: Record<number,string>; recordedIds?: number[] };

export function Graph({ data, selected, onSelect, visible, compact = false, statuses, recordedIds }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const cy = useRef<Core | null>(null);
  const choose = useRef(onSelect);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  choose.current = onSelect;
  const selectedRef=useRef(selected);selectedRef.current=selected;
  const highlightSelection=(graph:Core)=>{graph.elements().removeClass("near incident");if(selectedRef.current!==null){const n=graph.getElementById(String(selectedRef.current));n.neighborhood().nodes().addClass("near");n.connectedEdges().addClass("incident");}};
  useEffect(() => {
    if (!container.current) return;
    let disposed=false; let observer:ResizeObserver|undefined;
    const started=performance.now(); setReady(false); setFailed(false);
    loadLayout().then(layout => {
    if(disposed || !container.current) return;
    try {
      const graph = cytoscape({
        container: container.current, minZoom: 0.03, maxZoom: 5, hideEdgesOnViewport: true,
        elements: [
          ...data.nodes.map((node) => ({ data: { id: String(node.id), target: node.target ? 1 : 0, recorded: !recordedIds || recordedIds.includes(node.id) ? 1 : 0 },
            position: { x: layout.positions[node.id][1], y: layout.positions[node.id][2] } })),
          ...data.edges.map(e => ({ data: { id: `e${e.source}-${e.target}`, source: String(e.source), target: String(e.target) } })),
        ],
        style: [
          { selector: 'node', style: { 'background-color': '#a3aaa6', width: 12, height: 12, 'border-width': 0 } },
          { selector: 'node[target = 1]', style: { 'background-color': '#b4472d', width: 22, height: 22 } },
          { selector: 'node[recorded = 0]', style: { 'background-color':'#f5f2ea','border-width':1.5,'border-color':'#89948e' } },
          { selector: 'edge', style: { width: 1.8, 'line-color': '#b7bdb7', opacity: 0.7, 'curve-style': 'haystack' } },
          { selector: '.retained', style: { 'background-color':'#205b60', shape:'ellipse' } },
          { selector: '.withheld', style: { 'background-color':'#b4472d', shape:'diamond' } },
          { selector: '.dim', style: { opacity: 0.1 } },
          { selector: '.match', style: { 'border-width': 2, 'border-color': '#205b60' } },
          { selector: '.near', style: { 'background-color': '#205b60', 'border-width': 3, 'border-color': '#f7f5ef', width: 24, height: 24, opacity: 1 } },
          { selector: '.incident', style: { 'line-color': '#205b60', width: 3.5, opacity: 1 } },
          { selector: '.focus', style: { 'background-color': '#205b60', width: 32, height: 32, 'border-width': 6, 'border-color': '#d69a28', label: 'data(id)', color: '#302e29', 'font-size': 24, 'text-margin-y': -14, 'text-valign': 'top', 'text-background-color': '#f7f5ef', 'text-background-opacity': 0.9, 'text-background-padding': '3px', opacity: 1 } },
        ],
        // Precomputed topology-only positions; stable across scopes and inspector changes.
        layout: { name: 'preset', padding: compact ? 12 : 34 },
      });
      cy.current = graph;
      graph.on('tap', 'node', event => choose.current(Number(event.target.id())));
      graph.on('mouseover', 'node', event => {
        graph.elements().removeClass('near incident');
        event.target.closedNeighborhood().nodes().addClass('near');
        event.target.connectedEdges().addClass('incident');
      });
      graph.on('mouseout', 'node', () => highlightSelection(graph));
      observer = new ResizeObserver(() => { graph.resize(); });
      observer.observe(container.current);
      graph.fit(undefined,compact ? 14 : 34);
      if(!compact){const saved=views.get(data.graphHash+':'+data.nodes.map(n=>n.id).join(','));if(saved){graph.zoom(saved.zoom);graph.pan(saved.pan);}graph.on('pan zoom',()=>views.set(data.graphHash+':'+data.nodes.map(n=>n.id).join(','),{zoom:graph.zoom(),pan:graph.pan()}));}
      const recordViewport=()=>{if(container.current){container.current.dataset.zoom=String(graph.zoom());container.current.dataset.pan=JSON.stringify(graph.pan());}};
      graph.on('pan zoom',recordViewport);recordViewport();
      container.current.dataset.renderMs=(performance.now()-started).toFixed(1);
      container.current.dataset.nodeCount=String(graph.nodes().length);container.current.dataset.edgeCount=String(graph.edges().length);
      setReady(true);
    } catch {
      setFailed(true);
    }
    }).catch(()=>{if(!disposed)setFailed(true);});
    return ()=>{disposed=true;observer?.disconnect();cy.current?.destroy();cy.current=null;};
  }, [data, compact]);
  useEffect(() => {
    const graph = cy.current;
    if (!graph) return;
    graph.elements().removeClass('focus');
    if (selected !== null) graph.getElementById(String(selected)).addClass('focus');
    highlightSelection(graph);
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
  useEffect(()=>{const graph=cy.current;if(!graph)return;graph.nodes().removeClass('retained withheld');if(statuses)graph.nodes().forEach(n=>{const status=statuses[Number(n.id())];if(status==='retained'||status==='withheld')n.addClass(status);});},[statuses,ready]);
  const reset = () => { cy.current?.fit(undefined, 34); cy.current?.elements().removeClass('near incident'); };
  return <div className={`graph-frame ${compact ? 'compact' : ''}`}>
    <div ref={container} className="graph-canvas" role="region" aria-label="Cora topology graph. Use node list for accessible selection."
      tabIndex={0} onKeyDown={event => {
        if (event.key === '+' || event.key === '=') cy.current?.zoom(cy.current.zoom() * 1.2);
        if (event.key === '-') cy.current?.zoom(cy.current.zoom() / 1.2);
        if (event.key === 'Home') {event.preventDefault();reset();}
        if (event.key === 'Escape') cy.current?.elements().removeClass('near incident');
        if (event.key === 'f' && selected!==null) cy.current?.fit(cy.current.getElementById(String(selected)).closedNeighborhood(),80);
        if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
          event.preventDefault();
          const adjacent = selected === null ? [] : neighborsOf(data, selected);
          const next = event.key === 'ArrowRight' ? adjacent[0] : adjacent.at(-1);
          if (next !== undefined) onSelect(next);
        }
      }} />
    {!ready && !failed && <div className="graph-message" role="status">Loading verified structural layout…</div>}
    {failed && <div className="graph-message" role="alert">Graph could not load. Use the node list to inspect all recorded evidence.</div>}
    <div className="graph-watermark"><span>CORA / GLOBAL NODE IDS</span><span>DISPLAY LAYOUT</span></div>
    <div className="graph-controls" aria-label="Graph controls">
      <button aria-label="Zoom in" onClick={() => cy.current?.zoom(cy.current.zoom() * 1.3)}>+</button>
      <button aria-label="Zoom out" onClick={() => cy.current?.zoom(cy.current.zoom() / 1.3)}>−</button>
      <button onClick={() => cy.current?.fit(undefined, 34)}>Fit</button>
      {!compact && <><button disabled={selected===null||!data.nodes.some(n=>n.id===selected)} onClick={()=>{const n=cy.current?.getElementById(String(selected));if(n?.length)cy.current?.fit(n.closedNeighborhood(),80);}}>Focus selected</button><button onClick={reset}>Reset view</button></>}
    </div>
    {!compact && <p className="graph-hint">Drag to pan · Scroll to zoom · Edges temporarily hidden during motion</p>}
  </div>;
}
