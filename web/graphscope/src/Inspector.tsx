import type { Annotation, Atlas, ResearchNode } from './data';
import { format, label, neighborsOf } from './data';

export function Badge({ children, tone = '' }: { children: React.ReactNode; tone?: string }) {
  return <span className={`badge ${tone}`}><span aria-hidden="true">●</span> {children}</span>;
}

export function AnnotationView({ name, value, expanded = false }: { name: string; value: Annotation; expanded?: boolean }) {
  return <section className={`annotation ${name.startsWith('Narrative') ? 'narrative' : ''}`}>
    <div className="annotation-head"><span>{name}</span><span>{format(value.confidence, 1)}<small> / 100</small></span></div>
    <h3>{label(value.label)}</h3>
    <div className="confidence-track" aria-label={`Self-reported confidence ${format(value.confidence, 1)} out of 100`}><span style={{ width: `${value.confidence}%` }} /></div>
    <details open={expanded || undefined}><summary>Parsed samples & vote provenance</summary>
      <ol className="samples">{value.samples.map(s => <li key={s.index}><span>Sample {s.index + 1} · {s.valid ? 'Grammar valid' : 'Grammar invalid'}</span><strong>{label(s.label)} · {s.confidence}</strong><code title={s.responseHash}>Response SHA {s.responseHash.slice(0, 16)}…</code></li>)}</ol>
      <p className="small">Three stored parsed samples. Historical consistency voting; {value.fallbackCount} all-invalid fallback(s). Raw response parsing was not rerun.</p>
      <p className="small">Prompt SHA-256</p><code className="hash">{value.promptHash}</code>
    </details>
  </section>;
}

export function Inspector({ data, node, onSelect, onDesk }: { data: Atlas; node?: ResearchNode; onSelect: (id: number) => void; onDesk?: () => void }) {
  if (!node) return <aside className="inspector empty"><span className="eyebrow">THE RESEARCH RECORD</span><h2>Every node,<br />a source trail.</h2><p>Select a point or find a node by its recorded text.</p></aside>;
  const neighbors = neighborsOf(data, node.id);
  return <aside className="inspector" aria-label="Node evidence inspector">
    <div className="inspector-title"><span className="eyebrow">THE RESEARCH RECORD</span><span className="node-number">#{node.id}</span></div>
    <h2>Node {node.id}</h2><Badge tone={node.target ? 'warm' : ''}>{node.target ? 'Annotation target' : 'Recorded context'}</Badge>
    <p className="small">Cora global node ID · FeatProp study</p>
    <section className="paper-evidence"><h3>Recorded article evidence</h3>
      <p>{node.text ?? 'Article text unavailable for this context node in the admitted export.'}</p>
      <p className="small muted">{node.textTruncated ? 'Recorded text excerpt · limited to 1,200 characters. ' : ''}Canonical title unavailable. Text is not split into an inferred title.</p>
    </section>
    {node.annotations ? <><div className="inspector-annotations"><AnnotationView name="B1 · text only" value={node.annotations.b1} /><AnnotationView name="Narrative v0 · local evidence" value={node.annotations.narrative} /></div>
      <p className="agreement">{node.annotations.b1.label === node.annotations.narrative.label ? '✓ Arms agree' : '↔ Arms disagree'}<span>Same underlying LLM</span></p>
      <p className="small muted">Confidence is self-reported and vote-derived. It is not a calibrated correctness probability.</p></> : <p className="unavailable">B1 and Narrative annotations unavailable: this node is recorded as context, not an annotation target.</p>}
    <section className="neighbor-section"><h3>Recorded neighborhood</h3>
      <p className="small">{neighbors.length} displayed connection(s). The partial record does not establish the complete Cora neighborhood.</p>
      {node.recordedDegree !== undefined && <p className="small">Source-reported degree: {node.recordedDegree}. Selected prompt neighbors: {node.selectedNeighbors?.length}.</p>}
      <div className="node-chips">{neighbors.map(id => <button key={id} onClick={() => onSelect(id)}>#{id} <span aria-hidden="true">↗</span></button>)}</div>
      {node.narrativeEvidence && <details><summary>Original structural statement</summary><p className="small">{node.narrativeEvidence}</p><p className="small">Representative: #{node.representative}. This statement concerns the recorded selection only.</p></details>}
    </section>
    {onDesk && <button className="button primary full" onClick={onDesk}>Open Prediction Desk <span aria-hidden="true">↗</span></button>}
  </aside>;
}
