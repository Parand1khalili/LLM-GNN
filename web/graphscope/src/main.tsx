import { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import type { Atlas } from './data';
import { validateAtlas } from './data';
import { ATLAS_SHA256 } from './data-pin';
import { Desk, Experiments, Methods, Overview, Workflow } from './sections';
import { Agents } from './Agents';
import './style.css';
import './atlas-design.css';
import './core.css';
import { ScenarioDesk } from './ScenarioDesk';
import { GraphExplorer } from './GraphExplorer';
import { ResearchProvider, useResearch, OwnerAccess } from './ResearchContext';
import { CoreHome, BenchmarkLedger, CoreWorkflow, CoreNodeTrace } from './BenchmarkViews';

const pages = [['overview', 'Overview'], ['explore', 'Graph Explorer'], ['workflow', 'SARA-Core Workflow'], ['agents', 'Research Extensions'], ['methods', 'Methods'], ['experiments', 'Experiments'], ['desk', 'Node Inspector'], ['workbench', 'Replay & What-if']];
function readLocation() {
  const [path, query] = location.hash.slice(1).split('?');
  const params = new URLSearchParams(query);
  const node = params.get('node');
  return { page: pages.some(([id]) => id === path) ? path : 'overview', selected: node===null ? 1528 : /^\d+$/.test(node) ? Number(node) : -1, experimentId: params.get('experiment') ?? 'primary-ce-nops' };
}
function Mark() {
  return <svg viewBox="0 0 40 40" fill="none" aria-hidden="true"><path d="m7 31 10-22 17 18Z" stroke="currentColor" strokeWidth="1.1" /><path d="m17 9 5 17L7 31m15-5 12 1" stroke="currentColor" strokeWidth="1.1"/><circle cx="17" cy="9" r="3" fill="currentColor"/><circle cx="7" cy="31" r="2.4" fill="currentColor"/><circle cx="22" cy="26" r="2" fill="currentColor"/><circle cx="34" cy="27" r="4" fill="var(--paper)" stroke="currentColor"/></svg>;
}
function App() {
  const { benchmark, owner } = useResearch();
  const [data, setData] = useState<Atlas | null>(null);
  const [error, setError] = useState('');
  const [route, setRoute] = useState(readLocation);
  const [menu, setMenu] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    fetch(`${import.meta.env.BASE_URL}data/atlas.v2.json`, { signal: controller.signal }).then(async response => {
      if (!response.ok) throw new Error(`Research export could not load (HTTP ${response.status}).`);
      const bytes = await response.arrayBuffer();
      const digest = [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(v => v.toString(16).padStart(2, '0')).join('');
      if (digest !== ATLAS_SHA256) throw new Error('Research export checksum differs from the reviewed snapshot.');
      const atlas = validateAtlas(JSON.parse(new TextDecoder().decode(bytes)));
      setData(atlas);
    }).catch(e => { if (e.name !== 'AbortError') setError(String(e.message)); });
    return () => controller.abort();
  }, []);
  useEffect(() => { const change = () => { setRoute(readLocation()); setMenu(false); }; window.addEventListener('hashchange', change); return () => window.removeEventListener('hashchange', change); }, []);
  useEffect(() => {
    const page = pages.find(([id]) => id === route.page)?.[1];
    document.title = `${page} — GraphScope`;
    document.getElementById('main')?.focus({ preventScroll: true });
    window.scrollTo(0, 0);
  }, [route.page]);
  useEffect(() => {
    const shortcut = (event: KeyboardEvent) => {
      if (event.key === '/' && !/INPUT|TEXTAREA|SELECT/.test((event.target as HTMLElement).tagName)) { const input = document.querySelector<HTMLInputElement>('.search-field input'); if (input) { event.preventDefault(); input.focus(); } }
      if (event.key === 'Escape') setMenu(false);
    };
    window.addEventListener('keydown', shortcut); return () => window.removeEventListener('keydown', shortcut);
  }, []);
  const update = (page: string, selected = route.selected, experimentId = route.experimentId) => {
    const params = new URLSearchParams(location.hash.split('?')[1]); params.set('node',String(selected)); params.set('experiment',experimentId);
    location.hash = `${page}?${params}`;
  };
  const experimentId = data?.experiments.some(e => e.id === route.experimentId) ? route.experimentId : 'primary-ce-nops';
  const selected = route.selected !== null && route.selected >= 0 && route.selected < 2708 ? route.selected : null;
  const props = data ? { data, selected, onSelect: (id: number) => update(route.page, id, experimentId), navigate: (page: string) => update(page, route.selected, experimentId) } : null;
  return <><a className="skip-link" href="#main" onClick={event => { event.preventDefault(); document.getElementById('main')?.focus(); }}>Skip to research content</a>
    <header className="site-header"><a className="brand" href="#overview" aria-label="GraphScope overview"><Mark /><span>GraphScope<small>SARA-CORE RESEARCH ATLAS <b> / V3</b></small></span></a><button className="menu-toggle" aria-expanded={menu} aria-controls="site-nav" onClick={() => setMenu(!menu)}>{menu ? 'Close' : 'Menu'}</button>
      <nav id="site-nav" className={menu ? 'is-open' : ''} aria-label="Research sections">{pages.map(([id, title]) => <a key={id} href={`#${id}?${new URLSearchParams({...Object.fromEntries(new URLSearchParams(location.hash.split('?')[1])),node:String(route.selected),experiment:experimentId})}`} aria-current={route.page === id ? 'page' : undefined}>{title}</a>)}</nav></header>
    <div className="context-bar"><span><b className="cora-label">C</b> CORA <span className="context-divider" /> SARA-Core · selected exploratory method</span><span>Results · {benchmark.snapshotDate} · {owner ? "Owner-local" : "Public / sanitized"}</span></div>
    <main id="main" tabIndex={-1}>
      {error ? <section className="empty-state error-state" role="alert"><h1>Evidence unavailable.</h1><p>{error}</p><button className="button primary" onClick={() => location.reload()}>Retry loading</button><p className="small">No fallback or synthetic research data is displayed.</p></section> : !props ? <section className="empty-state" role="status"><h1>Opening the research record…</h1><p>Checking the export checksum and evidence schema.</p></section> : <>
        {route.selected !== null && selected === null && <p className="unavailable" role="status">Node #{route.selected} is outside canonical Cora IDs 0–2707. Choose a valid node in Graph Explorer.</p>}
        {route.page === 'overview' && <><CoreHome navigate={props.navigate} /><details className="archive-section"><summary>Archive · historical October study</summary><Overview {...props} /></details></>}
        {route.page === 'explore' && <GraphExplorer {...props} />}
        {route.page === 'workflow' && <><CoreWorkflow selected={selected} navigate={props.navigate} /><details className="archive-section"><summary>Archive · historical pipeline and research extension figure</summary><Workflow {...props} /></details></>}
        {route.page === 'workbench' && <ScenarioDesk navigate={props.navigate} />}
        {route.page === 'agents' && <Agents {...props} />}
        {route.page === 'methods' && <Methods data={props.data} />}
        {route.page === 'experiments' && <><BenchmarkLedger /><details className="archive-section"><summary>Archive · older B1/Narrative, Primary/Sensitivity, CE/WCE studies</summary><Experiments data={props.data} experimentId={experimentId} setExperimentId={id => update(route.page, route.selected, id)} /></details></>}
        {route.page === 'desk' && <><CoreNodeTrace selected={selected}/><OwnerAccess/><Desk {...props} experimentId={experimentId} setExperimentId={id => update(route.page, route.selected, id)} /></>}
      </>}
    </main><footer className="site-footer"><span><span className="footer-brand">GraphScope</span> / an instrument for inspecting evidence</span><span>Historical research preserved · Static inspection only</span><em>Understand before you infer.</em></footer>
  </>;
}

createRoot(document.getElementById('root')!).render(<ResearchProvider><App /></ResearchProvider>);
