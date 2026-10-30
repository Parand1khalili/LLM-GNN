import type { Atlas } from './data';

export type Topology = { schema: string; graphHash: string; sourceHash: string; manifestHash: string; rawEdgeCount: number; duplicatesRemoved: number; nodes: number[]; edges: [number, number][] };
function check(ok: unknown, message: string): asserts ok { if (!ok) throw new Error(`Topology rejected: ${message}`); }
export function validateTopology(value: unknown, atlas: Atlas): Topology {
  check(value && typeof value === 'object', 'object required');
  const t = value as Topology;
  const keys = ['schema','graphHash','sourceHash','manifestHash','rawEdgeCount','duplicatesRemoved','nodes','edges'];
  check(Object.keys(t).length === keys.length && Object.keys(t).every(k => keys.includes(k)), 'unexpected fields');
  check(t.schema === 'graphscope.topology.v1' && t.graphHash === atlas.graphHash, 'graph identity');
  check([t.sourceHash,t.manifestHash].every(h => /^[a-f0-9]{64}$/.test(h)), 'provenance hashes');
  check(Array.isArray(t.nodes) && t.nodes.length === 2708 && t.nodes.every((n,i) => n === i), 'canonical global ID space 0..2707');
  check(Array.isArray(t.edges) && t.edges.length > atlas.edges.length && t.edges.length < 100000, 'full edge coverage');
  const edges = new Set<string>();
  for (const pair of t.edges) {
    check(Array.isArray(pair) && pair.length === 2 && pair.every(n => Number.isInteger(n) && n >= 0 && n < 2708) && pair[0] < pair[1], 'endpoint/self-loop');
    const key = pair.join(':'); check(!edges.has(key), 'duplicate canonical edge'); edges.add(key);
  }
  check(Number.isInteger(t.rawEdgeCount) && Number.isInteger(t.duplicatesRemoved) && t.duplicatesRemoved >= 0 && t.rawEdgeCount === t.edges.length + t.duplicatesRemoved, 'duplicate accounting');
  check(atlas.edges.every(e => edges.has(`${e.source}:${e.target}`)), 'recorded evidence is not a subset; mapping conflict');
  return t;
}
export function topologyAtlas(t: Topology, atlas: Atlas): Atlas {
  const research = new Map(atlas.nodes.map(n => [n.id,n]));
  return { ...atlas, nodes: t.nodes.map(id => research.get(id) ?? {id,target:false}), edges: t.edges.map(([source,target]) => ({source,target,evidenceTargets:[]})) };
}
