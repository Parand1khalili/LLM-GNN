"""SARA-3: Read-only validation of six human L2 responses against private closeout.

No network, no modification, no GT, no model calls or acceptance decisions.
Do not put original human submissions or the private admin manifest in Git.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

SCHEMA = 'sara3.l2.human.response.v1'
CHOICES = {'supports', 'does_not_support', 'uncertain'}
TOPICS = {'yes', 'no', 'uncertain'}
EXPECTED_NODES = {1243, 130, 682}
EXPECTED_REVIEWERS = {'A', 'B'}
FIELDS = {'schema', 'reviewer_case_id', 'reviewer_independence_confirmed',
          'each_quote_supports_proposed_primary_class', 'overall_semantic_support',
          'primary_topic_match', 'uncertainty_or_limitation', 'short_justification'}

class ValidationError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def checked_json(data: bytes):
    def pairs(items):
        out = {}
        for k, v in items:
            if k in out:
                raise ValidationError('DUPLICATE_JSON_KEY')
            out[k] = v
        return out
    return json.loads(data, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValidationError('NONFINITE_JSON')))


def read_receipt(directory: Path, stem: str):
    if not isinstance(stem, str) or len(stem) != 64 or any(c not in '0123456789abcdef' for c in stem):
        raise ValidationError('RECEIPT_ID_INVALID')
    path = directory / (stem + '.json')
    if directory.is_symlink() or path.is_symlink() or not path.is_file():
        raise ValidationError('RECEIPT_MISSING_OR_UNSAFE')
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != stem:
        raise ValidationError('RECEIPT_HASH_MISMATCH')
    return checked_json(content)


def find_admin_manifest(closeout: Path):
    directory = closeout / 'admin'
    if not directory.is_dir() or directory.is_symlink():
        raise ValidationError('ADMIN_DIRECTORY_MISSING_OR_UNSAFE')
    manifests = []
    for path in directory.glob('*.json'):
        doc = read_receipt(directory, path.stem)
        if doc.get('kind') == 'administrator_manifest':
            manifests.append(doc)
    if len(manifests) != 1:
        raise ValidationError('ADMIN_MANIFEST_NOT_UNIQUE')
    return manifests[0]


def load_submissions(folder: Path):
    if not folder.is_dir() or folder.is_symlink():
        raise ValidationError('RESPONSE_FOLDER_MISSING_OR_UNSAFE')
    files = list(folder.glob('*.json'))
    if len(files) != 6:
        raise ValidationError('RESPONSE_FILE_COUNT_NOT_SIX')
    submissions = {}
    for file in files:
        if file.is_symlink() or not file.is_file():
            raise ValidationError('RESPONSE_FILE_UNSAFE')
        response = checked_json(file.read_bytes())
        if type(response) is not dict:
            raise ValidationError('RESPONSE_NOT_OBJECT')
        keys = set(response)
        if not FIELDS <= keys or keys - FIELDS - {'allowed_values'}:
            raise ValidationError('RESPONSE_SCHEMA_FIELDS_INVALID')
        if response['schema'] != SCHEMA:
            raise ValidationError('RESPONSE_SCHEMA_VERSION_INVALID')
        cid = response['reviewer_case_id']
        if type(cid) is not str or len(cid) != 24 or any(c not in '0123456789abcdef' for c in cid):
            raise ValidationError('CASE_ID_MALFORMED')
        if cid in submissions:
            raise ValidationError('DUPLICATE_CASE_RESPONSE')
        if response['reviewer_independence_confirmed'] is not True:
            raise ValidationError('INDEPENDENCE_NOT_SELF_CONFIRMED')
        quotes = response['each_quote_supports_proposed_primary_class']
        if type(quotes) is not list or not quotes or any(type(v) is not str or v not in CHOICES for v in quotes):
            raise ValidationError('QUOTE_VOTES_INVALID')
        if response['overall_semantic_support'] not in CHOICES or response['primary_topic_match'] not in TOPICS:
            raise ValidationError('OVERALL_VOTES_INVALID')
        if any(type(response[k]) is not str or not response[k].strip() for k in
               ('short_justification', 'uncertainty_or_limitation')):
            raise ValidationError('JUSTIFICATION_INCOMPLETE')
        submissions[cid] = response
    return submissions


def verify(closeout: Path, responses: Path):
    manifest = find_admin_manifest(closeout)
    mapping = manifest.get('cases')
    if type(mapping) is not list or len(mapping) != 6:
        raise ValidationError('ADMIN_CASE_COUNT_INVALID')
    submissions = load_submissions(responses)
    expected_pairs = {(n, r) for n in EXPECTED_NODES for r in EXPECTED_REVIEWERS}
    matched = {}
    ids = set()
    for record in mapping:
        if type(record) is not dict:
            raise ValidationError('ADMIN_CASE_RECORD_INVALID')
        node, reviewer, cid = record.get('node'), record.get('reviewer'), record.get('reviewer_case_id')
        if (type(node) is not int or type(reviewer) is not str or type(cid) is not str
                or (node, reviewer) not in expected_pairs or (node, reviewer) in matched or cid in ids):
            raise ValidationError('ADMIN_MAPPING_INCONSISTENT')
        ids.add(cid)
        case_doc = read_receipt(closeout / ('reviewer_' + reviewer), record.get('case_receipt_sha256'))
        case = case_doc.get('case')
        if case_doc.get('kind') != 'blinded_l2_case' or type(case) is not dict:
            raise ValidationError('BLINDED_CASE_KIND_INVALID')
        if case.get('schema') != 'sara3.l2.blinded_case.v1' or case.get('reviewer_case_id') != cid:
            raise ValidationError('BLINDED_CASE_BINDING_INVALID')
        excerpts = case.get('evidence_exact_target_excerpts')
        target = case.get('target_text')
        if type(excerpts) is not list or not excerpts or type(target) is not str or any(
                type(x) is not str or x not in target for x in excerpts):
            raise ValidationError('BLINDED_CASE_QUOTATION_INVALID')
        if cid not in submissions:
            raise ValidationError('MISSING_MAPPED_RESPONSE')
        response = submissions[cid]
        if len(excerpts) != len(response['each_quote_supports_proposed_primary_class']):
            raise ValidationError('QUOTE_COUNT_MISMATCH')
        matched[(node, reviewer)] = response
    if ids != set(submissions) or set(matched) != expected_pairs:
        raise ValidationError('EXTRA_OR_UNMATCHED_RESPONSE')
    rows = []
    agree_overall = agree_topic = quote_agree = quote_comparisons = 0
    for node in sorted(EXPECTED_NODES):
        a, b = matched[node, 'A'], matched[node, 'B']
        av, bv = a['each_quote_supports_proposed_primary_class'], b['each_quote_supports_proposed_primary_class']
        if len(av) != len(bv):
            raise ValidationError('REVIEWER_QUOTE_COUNTS_DIFFER')
        quote_matches = sum(x == y for x, y in zip(av, bv))
        quote_agree += quote_matches
        quote_comparisons += len(av)
        agree_overall += (a['overall_semantic_support'] == b['overall_semantic_support'])
        agree_topic += (a['primary_topic_match'] == b['primary_topic_match'])
        rows.append({'node': node,
                     'a_overall': a['overall_semantic_support'], 'b_overall': b['overall_semantic_support'],
                     'a_primary_topic': a['primary_topic_match'], 'b_primary_topic': b['primary_topic_match'],
                     'quote_agreements': quote_matches, 'quote_comparisons': len(av),
                     'overall_agreement': a['overall_semantic_support'] == b['overall_semantic_support']})
    return {'state': 'RESPONSES_VERIFIED_READ_ONLY', 'responses': len(submissions),
            'independence': 'SELF_DECLARED_NOT_EXTERNALLY_VERIFIED',
            'overall_agreement': {'agreed': agree_overall, 'cases': 3},
            'topic_agreement': {'agreed': agree_topic, 'cases': 3},
            'quote_agreement': {'agreed': quote_agree, 'paired_quotes': quote_comparisons},
            'rows': rows,
            'label_acceptance': 'NONE', 'arbitration': 'NOT_PERFORMED',
            'no_ledger_modified': True, 'no_network_requests': True}


def main():
    p = argparse.ArgumentParser(description='Read-only SARA-3 human L2 verifier; emits no raw content')
    p.add_argument('--closeout-dir', required=True, type=Path)
    p.add_argument('--responses-dir', required=True, type=Path)
    args = p.parse_args()
    try:
        result = verify(args.closeout_dir, args.responses_dir)
    except (ValidationError, OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as e:
        code = e.code if isinstance(e, ValidationError) else 'INPUT_OR_ACCESS_ERROR'
        print(json.dumps({'state': 'BLOCKED_READ_ONLY', 'safe_error_code': code}, indent=2))
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    sys.exit(main())
