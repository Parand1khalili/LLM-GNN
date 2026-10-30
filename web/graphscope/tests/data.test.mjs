import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import cytoscape from 'cytoscape';
import { validateAtlas, neighborsOf, searchNodes } from '../src/data.ts';
import { ATLAS_SHA256 } from '../src/data-pin.ts';

const bytes = readFileSync(new URL('../public/data/atlas.v2.json', import.meta.url));
const raw = JSON.parse(bytes);
const data = validateAtlas(raw);
const changed = () => structuredClone(raw);

test('reviewed export checksum and authentic coverage', () => {
  assert.equal(createHash('sha256').update(bytes).digest('hex'), ATLAS_SHA256);
  assert.equal(data.nodes.length, 478);
  assert.equal(data.edges.length, 525);
  assert.equal(data.nodes.filter(n => n.target).length, 140);
  assert.equal(data.experiments.reduce((n, e) => n + e.seeds.length * 2, 0), 160);
});
test('recorded node identity joins article, annotation and topology', () => {
  const node = data.nodes.find(n => n.id === 1013);
  assert.ok(node.text.includes('Specialization of Recursive Predicates'));
  assert.deepEqual(node.selectedNeighbors, [1014, 2407, 1879]);
  assert.equal(node.annotations.narrative.label, 'rule_learning');
  assert.ok(Math.abs(node.annotations.narrative.confidence - 94.66666666666667) < 1e-12);
  for (const n of node.selectedNeighbors) assert.ok(neighborsOf(data, 1013).includes(n));
  assert.equal(node.title, null);
});
test('actual FeatProp sensitivity WCE/noPS means agree with historical report', () => {
  const e = data.experiments.find(e => e.id === 'sensitivity-wce-nops');
  assert.ok(Math.abs(e.summary.b1.mean - 70.595794) < 0.000001);
  assert.ok(Math.abs(e.summary.narrative.mean - 73.165888) < 0.000001);
  assert.ok(Math.abs(e.delta.mean - 2.570093) < 0.000001);
});
test('search and disagreement filter preserve global node identity', () => {
  assert.deepEqual(searchNodes(data, 'recursive predicates', 'targets').map(n => n.id), [1013]);
  assert.ok(searchNodes(data, '1528', 'all').some(n => n.id === 1528));
  assert.ok(searchNodes(data, '', 'disagreement').length > 0);
  assert.ok(searchNodes(data, '', 'disagreement').every(n => n.annotations.b1.label !== n.annotations.narrative.label));
  assert.equal(searchNodes(data, 'not a recorded paper zxq', 'all').length, 0);
});
test('Cytoscape adjacency contains exactly the admitted edges', () => {
  const cy = cytoscape({ headless: true, elements: [
    ...data.nodes.map(n => ({ data: { id: String(n.id) } })),
    ...data.edges.map(e => ({ data: { source: String(e.source), target: String(e.target) } })),
  ] });
  assert.equal(cy.edges().length, 525);
  for (const node of data.nodes) assert.deepEqual(
    cy.getElementById(String(node.id)).neighborhood('node').map(n => Number(n.id())).sort((a, b) => a - b),
    neighborsOf(data, node.id).sort((a, b) => a - b));
  cy.destroy();
});
test('reject leakage fields, invented titles and ambiguous node mappings', () => {
  for (const mutate of [
    d => { d.nodes[0].ground_truth = 'theory'; },
    d => { d.nodes.find(n => n.target).title = 'Invented canonical title'; },
    d => { d.nodes[1].id = d.nodes[0].id; },
    d => { d.nodes.find(n => n.target).annotations.b1.label = 'unknown_class'; },
    d => { d.nodes.find(n => n.target).annotations.b1.confidence = NaN; },
  ]) { const d = changed(); mutate(d); assert.throws(() => validateAtlas(d), /Research export rejected/); }
});
test('reject invented topology, absent endpoints and duplicate edges', () => {
  for (const mutate of [
    d => { d.edges[0].target = 999999; },
    d => { d.edges.push(structuredClone(d.edges[0])); },
    d => { d.edges[0].evidenceTargets = []; },
    d => { d.edges[0].evidenceTargets = [data.nodes.find(n => n.target && n.id !== d.edges[0].source && !n.selectedNeighbors.includes(d.edges[0].source)).id]; },
  ]) { const d = changed(); mutate(d); assert.throws(() => validateAtlas(d)); }
});
test('reject changed means, repeated seeds, cohort conflation and source mismatch', () => {
  for (const mutate of [
    d => { d.experiments[0].summary.b1.mean += 0.1; },
    d => { d.experiments[0].seeds[1].seed = 0; },
    d => { d.experiments[0].cohort = 'pagerank2'; },
    d => { d.experiments[0].seeds[0].source = 'screenshot'; },
    d => { d.boundaries.saraVerifier = 'LIVE_MEASURED'; },
    d => { d.boundaries.newTrainingRuns = 1; },
  ]) { const d = changed(); mutate(d); assert.throws(() => validateAtlas(d)); }
});
test('saved GCN predictions remain separate from annotation targets', () => {
  assert.ok(data.nodes.some(n => n.gcn));
  for (const node of data.nodes.filter(n => n.target)) assert.equal(node.gcn, undefined);
  const d = changed(); d.nodes.find(n => n.target).gcn = d.nodes.find(n => n.gcn).gcn;
  assert.throws(() => validateAtlas(d), /training targets/);
});
test('offline routing is review selection only; no fixture judgments are exported', () => {
  const targets = data.nodes.filter(n => n.target);
  assert.equal(targets.filter(n => n.routing.r0Review).length, 37);
  assert.equal(targets.filter(n => n.routing.semanticReview).length, 37);
  assert.deepEqual(targets.filter(n => n.routing.pilotSelected).map(n => n.id), [130, 637, 653, 682, 1243, 2396]);
  const d = changed(); d.nodes.find(n => n.target).routing.verifierJudgment = 'accept';
  assert.throws(() => validateAtlas(d), /unexpected/);
});
