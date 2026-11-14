import { readdirSync, readFileSync, statSync } from 'node:fs';
import { resolve, relative } from 'node:path';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';

const root = resolve('dist');
const files = [];
function visit(directory) {
  for (const name of readdirSync(directory)) {
    const path = resolve(directory, name);
    if (statSync(path).isDirectory()) visit(path); else files.push(path);
  }
}
visit(root);
for (const file of files) {
  const name = relative(root, file).replaceAll('\\', '/');
  assert.ok(name === 'index.html' || name === 'data/atlas.v2.json' || name === 'data/full-topology.json' || name === 'data/benchmark.v3.json' || name === 'data/layout.v1.json' || /^assets\/[\w-]+\.(js|css)$/.test(name), `Unexpected public file: ${name}`);
  const text = readFileSync(file, 'utf8');
  assert.ok(!/(?:sk-[A-Za-z0-9_-]{24,}|-----BEGIN [A-Z ]*PRIVATE KEY|Bearer\s+[A-Za-z0-9._-]{20,}|C:\\\\Users\\\\Admin|\.local_artifacts)/.test(text), `Sensitive content: ${name}`);
  assert.ok(statSync(file).size < 1_500_000, `Unexpected large public file: ${name}`);
}
const source = readFileSync('public/data/atlas.v2.json');
assert.equal(createHash('sha256').update(source).digest('hex'), createHash('sha256').update(readFileSync('dist/data/atlas.v2.json')).digest('hex'));
const html = readFileSync('dist/index.html', 'utf8');
assert.ok(html.includes('/LLM-GNN/assets/'), 'Wrong GitHub Pages base path');
assert.ok(!html.includes('http://') && !html.includes('https://'), 'Unexpected remote asset');
console.log(`PASS: ${files.length} public files; exact sanitized export; no source maps, source artifacts or credential patterns; /LLM-GNN/ base.`);

assert.equal(createHash('sha256').update(readFileSync('public/data/benchmark.v3.json')).digest('hex'),createHash('sha256').update(readFileSync('dist/data/benchmark.v3.json')).digest('hex'));

for(const name of ['full-topology.json','layout.v1.json'])assert.equal(createHash('sha256').update(readFileSync('public/data/'+name)).digest('hex'),createHash('sha256').update(readFileSync('dist/data/'+name)).digest('hex'));
const benchmark=JSON.parse(readFileSync('dist/data/benchmark.v3.json','utf8'));
assert.ok(!Object.keys(benchmark).some(k=>['targetIds','labels','confidence','GT'].includes(k)));
for(const arm of benchmark.arms)assert.ok(!Object.keys(arm).some(k=>['targetIds','labels','confidence','GT'].includes(k)));
