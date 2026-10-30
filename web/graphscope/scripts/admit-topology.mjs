// Offline, JSON-only admission. The manifest hash must be reviewed independently.
import { readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';
import { validateTopology } from '../src/topology.ts';
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const [manifestPath, reviewedManifestHash] = process.argv.slice(2);
assert.ok(manifestPath && /^[a-f0-9]{64}$/.test(reviewedManifestHash ?? ''), 'Usage: node scripts/admit-topology.mjs <reviewed-manifest.json> <independently-reviewed-manifest-sha256>');
const hash = b => createHash('sha256').update(b).digest('hex');
const bytes = readFileSync(manifestPath);
assert.equal(hash(bytes), reviewedManifestHash, 'Manifest hash conflict');
const manifest = JSON.parse(bytes);
assert.deepEqual(Object.keys(manifest).sort(), ['source','sha256','graphHash','idSpace','mappingEvidence','rawEdgeCount','uniqueUndirectedEdgeCount'].sort());
assert.equal(manifest.idSpace,'canonical-zero-based-global-Cora-2708');
const mapping = manifest.mappingEvidence;
assert.deepEqual(Object.keys(mapping).sort(),['file','sha256']);
assert.equal(hash(readFileSync(resolve(dirname(resolve(manifestPath)),mapping.file))),mapping.sha256,'Mapping evidence bytes differ');
const source = readFileSync(resolve(dirname(resolve(manifestPath)),manifest.source));
assert.ok(source.length < 10000000, 'Oversized topology source');
assert.equal(hash(source),manifest.sha256,'Topology source hash conflict');
const raw = JSON.parse(source);
assert.deepEqual(Object.keys(raw).sort(), ['nodes','edges']);
assert.equal(raw.edges.length,manifest.rawEdgeCount);
const canonical = new Map();
for (const pair of raw.edges) {
  assert.ok(Array.isArray(pair) && pair.length===2 && pair.every(n=>Number.isInteger(n)&&n>=0&&n<2708) && pair[0]!==pair[1], 'Invalid edge');
  const edge=[...pair].sort((a,b)=>a-b); canonical.set(edge.join(':'),edge);
}
assert.equal(canonical.size,manifest.uniqueUndirectedEdgeCount,'Unique edge count differs');
const value={schema:'graphscope.topology.v1',graphHash:manifest.graphHash,sourceHash:manifest.sha256,manifestHash:reviewedManifestHash,rawEdgeCount:raw.edges.length,duplicatesRemoved:raw.edges.length-canonical.size,nodes:raw.nodes,edges:[...canonical.values()].sort((a,b)=>a[0]-b[0]||a[1]-b[1])};
validateTopology(value,JSON.parse(readFileSync(resolve(root,'public/data/atlas.v2.json'))));
const output=JSON.stringify(value)+'\n';
writeFileSync(resolve(root,'public/data/full-topology.json'),output);
writeFileSync(resolve(root,'src/topology-pin.ts'),`export const TOPOLOGY_SHA256: string | null = "${hash(output)}";\n`);
console.log({nodes:value.nodes.length,edges:value.edges.length,duplicatesRemoved:value.duplicatesRemoved,sha256:hash(output)});
