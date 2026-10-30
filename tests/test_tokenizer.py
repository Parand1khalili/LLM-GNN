"""Real tokenizer parity using an explicitly provisioned public cache; no network."""
import ast
import hashlib
import importlib.util
import os
from pathlib import Path
import socket
import unittest
from unittest.mock import patch

from llmgnn_sara.annotation.prompts import (
    COMMON_INSTRUCTION, FrozenPromptTemplate, SENTINEL, build_b1_prompt,
    build_consensus, build_narrative_prompt,
)


class HistoricalTokenizer(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec("tiktoken"), "Optional tokenizer not installed")
    def test_cached_cl100k_budget_and_historical_consensus_parity(self):
        root = Path(__file__).resolve().parents[1]
        cache = root / ".local_artifacts/tokenizer_cache"
        vocabulary = cache / "9b5ad71b2ce5302211f9c61530b329a4922fc6a4"
        if not vocabulary.is_file():
            self.skipTest("Public cl100k_base cache not provisioned; tests never download it")
        self.assertEqual(hashlib.sha256(vocabulary.read_bytes()).hexdigest(),
                         "223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7")
        with patch.dict(os.environ, {"TIKTOKEN_CACHE_DIR": str(cache)}), \
                patch.object(socket.socket, "connect", side_effect=AssertionError("Network attempted")):
            import tiktoken
            encoding = tiktoken.get_encoding("cl100k_base")
            original = root / "recovered_sources/src/structure/prompt_builder.py"
            blob = original.read_bytes()
            self.assertEqual(hashlib.sha256(blob).hexdigest(),
                             "fffbc78c364bb9a367c640e7f69196c8640b0f48eb67e0a336152942de6cde7e")
            tree = ast.parse(blob.decode("utf-8-sig"))
            # Only these reviewed pure functions are executed, never the historical
            # imports/tokenizer startup or any annotation/training entry point.
            names = {"count_tokens", "truncate_tokens", "_fit_with_suffix", "build_consensus"}
            functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
            self.assertEqual({n.name for n in functions}, names)
            module = ast.fix_missing_locations(ast.Module(body=functions, type_ignores=[]))
            namespace = {"ENC": encoding, "STRUCTURAL_BUDGET": 256, "COMMON_INSTRUCTION": COMMON_INSTRUCTION}
            exec(compile(module, "<reviewed pure historical prompt functions>", "exec"), namespace)
            for text in ("Verified synthetic neighbor.", "Synthetic neighbor words. " * 2000):
                actual = build_consensus(text, 2, 3, encoding)
                self.assertEqual(actual, namespace["build_consensus"](text, 2, 3))
                self.assertLessEqual(len(encoding.encode(actual)), 256)
            template = FrozenPromptTemplate("Question: " + SENTINEL + "\nPublic class task")
            consensus = build_consensus("Synthetic neural network study.", 2, 3, encoding)
            prompt, diagnostic = build_narrative_prompt(
                "Synthetic target", template, consensus, 0, (1, 2, 3), 1,
                ((1, 2, 3), (0, 2), (0, 1), (0,)), lambda text: len(encoding.encode(text)))
            self.assertLessEqual(diagnostic["new_structural_tokens"], 320)
            self.assertIn("N1 connects directly to N2", prompt)
            self.assertIn("Synthetic target", build_b1_prompt("Synthetic target", template))


if __name__ == "__main__":
    unittest.main()
