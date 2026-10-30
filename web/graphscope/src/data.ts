export type Arm = 'b1' | 'narrative';
export type Annotation = {
  label: string; confidence: number; promptHash: string; fallbackCount: number;
  samples: { index: number; label: string; confidence: number; valid: boolean; responseHash: string }[];
};
export type ResearchNode = {
  id: number; target: boolean; title?: null; text?: string; textTruncated?: boolean;
  recordedDegree?: number; selectedNeighbors?: number[]; representative?: number;
  narrativeEvidence?: string; annotations?: Record<Arm, Annotation>;
  routing?: { r0Review: boolean; semanticReview: boolean; pilotSelected: boolean };
  gcn?: Record<string, Record<Arm, number[]>>;
};
export type Seed = { seed: number; source: string; b1: number; narrative: number };
export type Stats = { mean: number; sd: number };
export type Experiment = {
  id: string; cohort: 'primary' | 'sensitivity'; postFilter: boolean; weighted: boolean;
  b1TrainCount: number; narrativeTrainCount: number; seeds: Seed[];
  b1ClassCount: number; narrativeClassCount: number;
  summary: Record<Arm, Stats>; delta: Stats;
};
export type Atlas = {
  schema: 'graphscope.atlas.v2'; snapshotDate: string; graphHash: string; classes: string[];
  nodes: ResearchNode[]; edges: { source: number; target: number; evidenceTargets: number[] }[];
  experiments: Experiment[]; sources: { id: string; sha256: string; status: string }[];
  boundaries: { topology: string; rawParsing: string; saraVerifier: string; pageRank2: string; newTrainingRuns: number };
};

function requireValue(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(`Research export rejected: ${message}`);
}
function fields(value: unknown, allowed: string[], required = allowed): asserts value is Record<string, unknown> {
  requireValue(value !== null && typeof value === 'object' && !Array.isArray(value), 'object expected');
  requireValue(Object.keys(value).every(k => allowed.includes(k)) && required.every(k => k in value), 'unexpected or missing field');
}
const finite = (v: unknown, min = 0, max = Infinity): v is number => typeof v === 'number' && Number.isFinite(v) && v >= min && v <= max;
const integer = (v: unknown, max = 2707): v is number => finite(v, 0, max) && Number.isInteger(v);
const hash = (v: unknown) => typeof v === 'string' && /^[a-f0-9]{64}$/.test(v);
const text = (v: unknown, max = 2000) => typeof v === 'string' && v.length <= max;
const stats = (values: number[]) => {
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  return { mean, sd: Math.sqrt(values.reduce((a, b) => a + (b - mean) ** 2, 0) / values.length) };
};

export function validateAtlas(input: unknown): Atlas {
  fields(input, ['schema', 'snapshotDate', 'graphHash', 'classes', 'nodes', 'edges', 'experiments', 'sources', 'boundaries']);
  requireValue(input.schema === 'graphscope.atlas.v2' && hash(input.graphHash) && input.snapshotDate === '2026-10-30', 'version/identity');
  const classes = input.classes;
  requireValue(Array.isArray(classes) && classes.length === 7 && new Set(classes).size === 7 && classes.every(c => text(c, 60)), 'classes');
  requireValue(Array.isArray(input.nodes) && input.nodes.length < 2708, 'partial node set');
  const nodes = new Map<number, ResearchNode>();
  for (const node of input.nodes) {
    fields(node, ['id', 'target', 'title', 'text', 'textTruncated', 'recordedDegree', 'selectedNeighbors', 'representative', 'narrativeEvidence', 'annotations', 'routing', 'gcn'], ['id', 'target']);
    requireValue(integer(node.id) && !nodes.has(node.id) && typeof node.target === 'boolean', 'node identity');
    if (node.target) {
      requireValue(node.title === null && text(node.text, 1200) && typeof node.textTruncated === 'boolean' && text(node.narrativeEvidence), 'recorded paper evidence');
      requireValue(integer(node.recordedDegree) && Array.isArray(node.selectedNeighbors) && node.selectedNeighbors.length <= 3 && node.selectedNeighbors.every(n => integer(n) && n !== node.id), 'selected neighborhood');
      requireValue(new Set(node.selectedNeighbors).size === node.selectedNeighbors.length && node.selectedNeighbors.includes(node.representative), 'representative');
      fields(node.annotations, ['b1', 'narrative']);
      fields(node.routing, ['r0Review', 'semanticReview', 'pilotSelected']);
      requireValue(Object.values(node.routing).every(v => typeof v === 'boolean'), 'offline routing selection');
      for (const value of Object.values(node.annotations)) {
        fields(value, ['label', 'confidence', 'promptHash', 'fallbackCount', 'samples']);
        requireValue(classes.includes(value.label) && finite(value.confidence, 0, 100) && hash(value.promptHash) && integer(value.fallbackCount, 1), 'annotation');
        requireValue(Array.isArray(value.samples) && value.samples.length === 3, 'three parsed samples');
        value.samples.forEach((s, i) => {
          fields(s, ['index', 'label', 'confidence', 'valid', 'responseHash']);
          requireValue(s.index === i && text(s.label, 100) && finite(s.confidence, 0, 100) && typeof s.valid === 'boolean' && hash(s.responseHash), 'sample identity');
        });
      }
    } else requireValue(!('annotations' in node) && !('text' in node) && !('routing' in node), 'context node content must be unavailable');
    nodes.set(node.id, node as ResearchNode);
  }
  requireValue([...nodes.values()].filter(n => n.target).length === 140, 'target cohort');
  requireValue(Array.isArray(input.edges), 'edges');
  const edges = new Set<string>();
  for (const edge of input.edges) {
    fields(edge, ['source', 'target', 'evidenceTargets']);
    requireValue(integer(edge.source) && integer(edge.target) && edge.source < edge.target && nodes.has(edge.source) && nodes.has(edge.target), 'edge endpoints');
    const id = `${edge.source}:${edge.target}`;
    requireValue(!edges.has(id) && Array.isArray(edge.evidenceTargets) && edge.evidenceTargets.length > 0 && edge.evidenceTargets.every(n => integer(n) && nodes.get(n)?.target), 'edge provenance');
    for (const id of edge.evidenceTargets) {
      const owner = nodes.get(id)!;
      const local = [id, ...owner.selectedNeighbors!];
      requireValue(local.includes(edge.source) && local.includes(edge.target), 'edge outside recorded ego evidence');
    }
    edges.add(id);
  }
  for (const node of nodes.values()) for (const other of node.selectedNeighbors ?? []) {
    requireValue(edges.has(`${Math.min(node.id, other)}:${Math.max(node.id, other)}`), 'missing recorded neighbor edge');
  }
  requireValue(Array.isArray(input.sources) && input.sources.length > 0, 'source records');
  const sources = new Set<string>();
  for (const source of input.sources) {
    fields(source, ['id', 'sha256', 'status']);
    requireValue(text(source.id, 180) && !sources.has(source.id as string) && hash(source.sha256) && source.status === ((source.id as string).startsWith('reports/') ? 'REPRODUCED' : 'RECOVERED_EXACT'), 'source pin');
    sources.add(source.id as string);
  }
  requireValue(Array.isArray(input.experiments) && input.experiments.length === 8, 'experiment coverage');
  const experiments = new Set<string>();
  for (const experiment of input.experiments) {
    fields(experiment, ['id', 'cohort', 'weighted', 'postFilter', 'b1TrainCount', 'narrativeTrainCount', 'b1ClassCount', 'narrativeClassCount', 'seeds', 'summary', 'delta']);
    const e = experiment as Experiment;
    requireValue(['primary', 'sensitivity'].includes(e.cohort) && typeof e.weighted === 'boolean' && typeof e.postFilter === 'boolean' && e.id === `${e.cohort}-${e.weighted ? 'wce' : 'ce'}-${e.postFilter ? 'ps' : 'nops'}` && !experiments.has(e.id), 'separate condition identity');
    experiments.add(e.id);
    const trainCount = e.cohort === 'primary' ? (e.postFilter ? 95 : 135) : (e.postFilter ? 98 : 140);
    requireValue(e.b1TrainCount === trainCount && e.narrativeTrainCount === trainCount && Array.isArray(e.seeds) && e.seeds.length === 10, 'training/seed count');
    requireValue(integer(e.b1ClassCount, 7) && e.b1ClassCount > 0 && integer(e.narrativeClassCount, 7) && e.narrativeClassCount > 0, 'retained class coverage');
    e.seeds.forEach((s, i) => {
      fields(s, ['seed', 'source', 'b1', 'narrative']);
      requireValue(s.seed === i && finite(s.b1, 0, 100) && finite(s.narrative, 0, 100) && sources.has(s.source as string), 'matched seed/source');
    });
    fields(e.summary, ['b1', 'narrative']);
    for (const arm of ['b1', 'narrative'] as const) {
      fields(e.summary[arm], ['mean', 'sd']);
      const actual = stats(e.seeds.map(s => s[arm]));
      requireValue(Math.abs(actual.mean - e.summary[arm].mean) < 1e-9 && Math.abs(actual.sd - e.summary[arm].sd) < 1e-9, 'mean/population SD mismatch');
    }
    fields(e.delta, ['mean', 'sd']);
    const delta = stats(e.seeds.map(s => s.narrative - s.b1));
    requireValue(Math.abs(delta.mean - e.delta.mean) < 1e-9 && Math.abs(delta.sd - e.delta.sd) < 1e-9, 'paired delta mismatch');
  }
  for (const node of nodes.values()) if (node.gcn) {
    fields(node.gcn, [...experiments]);
    requireValue(!node.target, 'training targets cannot have held-out predictions');
    for (const result of Object.values(node.gcn)) {
      fields(result, ['b1', 'narrative']);
      for (const values of Object.values(result)) requireValue(Array.isArray(values) && values.length === 10 && values.every(v => integer(v, 6)), 'saved GCN predictions');
    }
  }
  fields(input.boundaries, ['topology', 'rawParsing', 'saraVerifier', 'pageRank2', 'newTrainingRuns']);
  requireValue(input.boundaries.topology === 'PARTIAL_RECORDED' && input.boundaries.rawParsing === 'NOT_RUN' && input.boundaries.saraVerifier === 'NO_REAL_VERIFIER_RESULT_IN_THIS_EXPORT' && input.boundaries.pageRank2 === 'SOURCE_ARTIFACTS_UNAVAILABLE' && input.boundaries.newTrainingRuns === 0, 'evidence boundary');
  return input as Atlas;
}

export function neighborsOf(data: Atlas, id: number): number[] {
  return data.edges.flatMap(e => e.source === id ? [e.target] : e.target === id ? [e.source] : []);
}
export function searchNodes(data: Atlas, query: string, filter: string): ResearchNode[] {
  const term = query.toLocaleLowerCase().trim();
  return data.nodes.filter(n => (`${n.id} ${n.text ?? ''}`).toLocaleLowerCase().includes(term) &&
    (filter === 'all' || (filter === 'targets' && n.target) ||
      (filter === 'disagreement' && n.annotations && n.annotations.b1.label !== n.annotations.narrative.label)));
}
export const label = (s: string) => s.replaceAll('_', ' ');
export const format = (n: number, digits = 2) => n.toFixed(digits);
