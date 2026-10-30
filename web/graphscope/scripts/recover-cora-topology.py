"""Extract fixed edge storage from the exact pinned archive, without unpickling.

pickletools is a static opcode disassembler. No pickle VM, REDUCE, GLOBAL,
PyTorch import, object constructor or persistent-loader callback is executed.
Only ZIP metadata and storage/1 (edge_index) are read. Label storage/0 is not read.
This deliberately supports one reviewed archive, not arbitrary torch files.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import pickletools
import struct
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE_HASH = "9285c2afae1bdd9e01ee1b805ace7bd1308a49895b1f11fa22bd0e5bd0adf466"
PROMPT_HASH = "d7416cb83070b4a5d1ceaee061fe3fb81b6646abcee5cdabe58db33c5b8fdf29"
CONTEXT_HASH = "1bd0be9dba2760159f30d72f77dc6036729b2ff10182d220f7673823af95f56e"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def read_pinned(path, expected):
    blob = Path(path).read_bytes()
    require(digest(blob) == expected, "Historical hash conflict: " + Path(path).name)
    return blob


def extract(archive):
    read_pinned(archive, SOURCE_HASH)  # Admission precedes ZIP/metadata inspection.
    prefix = "cora_random_sbert/"
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        require(len(names) == len(set(names)), "Duplicate archive member")
        require(z.getinfo(prefix + "data.pkl").file_size == 2456344, "Metadata size differs")
        require(z.getinfo(prefix + "data/1").file_size == 173728, "Edge storage size differs")
        metadata = z.read(prefix + "data.pkl")
        ops = list(pickletools.genops(metadata))
        # Verify literal memo bindings without resolving or invoking any callable.
        for memo, literal in {2724: ("GLOBAL", "torch._utils _rebuild_tensor_v2"),
                              2725: ("BINUNICODE", "storage"),
                              2726: ("GLOBAL", "torch LongStorage"),
                              2728: ("BINUNICODE", "cpu"),
                              2732: ("GLOBAL", "collections OrderedDict")}.items():
            bindings = [i for i, (o, a, _) in enumerate(ops)
                        if o.name in ("BINPUT", "LONG_BINPUT") and a == memo]
            require(len(bindings) == 1, "Ambiguous metadata binding")
            o, a, _ = ops[bindings[0] - 1]
            require((o.name, a) == literal, "Reviewed metadata binding differs")
        locations = [i for i, (_, a, _) in enumerate(ops) if a == "edge_index"]
        require(len(locations) == 1, "Ambiguous edge attribute")
        i = locations[0]
        actual = [(o.name, a) for o, a, _ in ops[i:i + 34]]
        expected = [('BINUNICODE', 'edge_index'), ('LONG_BINPUT', 2745),
                    ('LONG_BINGET', 2724), ('MARK', None), ('MARK', None),
                    ('LONG_BINGET', 2725), ('LONG_BINGET', 2726),
                    ('BINUNICODE', '1'), ('LONG_BINPUT', 2746), ('LONG_BINGET', 2728),
                    ('BININT2', 21716), ('TUPLE', None), ('LONG_BINPUT', 2747),
                    ('BINPERSID', None), ('BININT1', 0), ('BININT1', 2),
                    ('BININT2', 10858), ('TUPLE2', None), ('LONG_BINPUT', 2748),
                    ('BININT2', 10858), ('BININT1', 1), ('TUPLE2', None),
                    ('LONG_BINPUT', 2749), ('NEWFALSE', None), ('LONG_BINGET', 2732),
                    ('EMPTY_TUPLE', None), ('REDUCE', None), ('LONG_BINPUT', 2750),
                    ('TUPLE', None), ('LONG_BINPUT', 2751), ('REDUCE', None),
                    ('LONG_BINPUT', 2752), ('BINUNICODE', 'train_masks'), ('LONG_BINPUT', 2753)]
        require(actual == expected, "Reviewed edge descriptor differs")
        text_start = next(i for i, (_, a, _) in enumerate(ops) if a == "raw_text")
        texts = []
        for o, a, _ in ops[text_start + 5:]:
            if o.name == "BINUNICODE":
                texts.append(a)
            else:
                require(o.name in ("BINPUT", "LONG_BINPUT", "MARK", "APPENDS"),
                        "Unsupported paper-list metadata")
            if len(texts) == 2708:
                break
        require(len(texts) == 2708, "Node text/index count differs")
        storage = z.read(prefix + "data/1")  # Only tensor storage read.
    values = struct.unpack('<21716q', storage)
    require(all(0 <= n < 2708 for n in values), "Endpoint/byte-order conflict")
    edges = list(zip(values[:10858], values[10858:]))
    require(all(a != b for a, b in edges), "Unexpected self-loop")
    return texts, edges, {"metadataSha256": digest(metadata), "edgeStorageSha256": digest(storage)}


def recover(archive, authentic, output):
    texts, edges, hashes = extract(archive)
    prompts = json.loads(read_pinned(authentic / "b1_prompts.json", PROMPT_HASH))["prompts_by_target_id"]
    contexts = json.loads(read_pinned(authentic / "neighborhoods.json", CONTEXT_HASH))["by_target_id"]
    pairs = set(tuple(sorted(pair)) for pair in edges)
    directed = set(edges)
    require(all((b, a) in directed for a, b in directed), "Reciprocity differs")
    adjacent = {n: set() for n in range(2708)}
    for a, b in edges:
        adjacent[a].add(b)
    require(len(prompts) == len(contexts) == 140, "Target count differs")
    for key, prompt in prompts.items():
        require(prompt.startswith("Question: Paper: \n") and prompt.count("\nTask: \n") == 1,
                "Paper boundary differs")
        paper = prompt[len("Question: Paper: \n"):prompt.index("\nTask: \n")]
        require(texts[int(key)] == paper, "Paper/global-ID mapping conflict: " + key)
        context = contexts[key]
        require(len(adjacent[int(key)]) == context["degree"], "Source degree conflict: " + key)
        require(all(n in adjacent[int(key)] for n in context["neighbor_ids"]), "Neighbor conflict")
        detail = context["v0_details"]
        require(all(b in adjacent[a] for a, b in detail["connected_node_pairs"]), "Positive edge conflict")
        require(all(b not in adjacent[a] for a, b in detail["disconnected_node_pairs"]), "Negative edge conflict")
    atlas = json.loads((ROOT / "public/data/atlas.v2.json").read_bytes())
    require(all((e["source"], e["target"]) in pairs for e in atlas["edges"]), "Atlas edge conflict")
    counts = Counter(edges)
    output.mkdir(parents=True, exist_ok=True)
    mapping = {"schema": "graphscope.cora.mapping.v1", "status": "RECOVERED_EXACT_SOURCE_REPRODUCED_EXTRACTION",
               "sourceGraphSha256": SOURCE_HASH, "driveFileId": "1BLOmx8MRvsWqPQLIrw78aYl5C3Uu8LyH",
               "originalPath": "Prnd-project/LLMGNN_data/cora_random_sbert.pt",
               "method": "Static opcode inspection plus fixed int64 ZIP storage extraction; no pickle execution",
               "nodeIdSpace": "Unmodified source tensor row indices 0..2707",
               "nodeCount": 2708, "rawEdgeCount": len(edges), "uniqueDirectedEdges": len(directed),
               "uniqueUndirectedEdges": len(pairs), "repeatedDirectedEntries": sum(c - 1 for c in counts.values()),
               "reverseAndRepeatedEntriesRemovedForDisplay": len(edges) - len(pairs),
               "selfLoops": 0, "reciprocal": True, "isolatedNodes": sum(not n for n in adjacent.values()),
               "targetTextMatches": 140, "targetDegreeMatches": 140, "atlasEdgesMatched": len(atlas["edges"]),
               "recordedPositiveAndNegativePairsMatched": True,
               "promptSourceSha256": PROMPT_HASH, "contextSourceSha256": CONTEXT_HASH,
               "edgeShape": [2, 10858], "edgeStride": [10858, 1], "storageOffset": 0,
               "storageDtype": "little-endian signed int64", "readTensorStorageMembers": ["cora_random_sbert/data/1"],
               "GTStorageRead": False, "pickleDeserialization": False, "providerCalls": 0, "trainingRuns": 0, **hashes}
    def write(name, value):
        blob = (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()
        (output / name).write_bytes(blob)
        return digest(blob)
    topology_hash = write('cora_topology.json', {"nodes": list(range(2708)), "edges": edges})
    mapping_hash = write('cora_topology.mapping.json', mapping)
    manifest_hash = write('cora_topology.manifest.json', {
        "source": "cora_topology.json", "sha256": topology_hash, "graphHash": SOURCE_HASH,
        "idSpace": "canonical-zero-based-global-Cora-2708",
        "mappingEvidence": {"file": "cora_topology.mapping.json", "sha256": mapping_hash},
        "rawEdgeCount": len(edges), "uniqueUndirectedEdgeCount": len(pairs)})
    print(json.dumps({"manifestSha256": manifest_hash, "mapping": mapping}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--authentic', type=Path, default=ROOT.parents[1] / '.local_artifacts/authentic')
    parser.add_argument('--output', type=Path, default=ROOT / '.qa/topology-recovery')
    args = parser.parse_args()
    recover(args.archive, args.authentic, args.output)
