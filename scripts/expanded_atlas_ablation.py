"""One-factor lexical ablation, run in an isolated offline process."""
from dataclasses import replace
from unittest.mock import patch
from llmgnn_sara.sara3 import atlas, r1_candidate as r1
from llmgnn_sara.sara3.audit import PrivateAudit
from llmgnn_sara.sara3.experiment import digest
from llmgnn_sara.io.project import load_project_inputs

EXTRA = (
    "horn clause clauses predicate predicates antecedent consequent foil",
    "perceptron multilayer sigmoid activation neuron neurons recurrent convolutional",
    "analogical exemplar exemplars instance instances adaptation similarity nearest",
    "chromosome chromosomes fitness population populations recombination genotype offspring",
    "pac learnability vc hypothesis hypotheses generalization convergence shattering",
    "rewards policies temporal bellman action actions exploration exploitation",
    "bayes posterior prior conditional marginal inference marginalization priors",
)

def main():
    pairs=load_project_inputs('.local_artifacts/frozen','.local_artifacts/authentic').pairs
    package=PrivateAudit('.local_artifacts/expanded_gcn_inventory_v1').read('789a6aea4715c1e7537ede75d82f5e552859c392a0e27acd8cbbbc03b568da83')
    old=r1.route_r1_candidate(pairs)
    assert list(old)==next(r['selected_ids'] for r in package['routers'] if r['router']=='r1_v1')
    result={}
    for name,entries in [('old',atlas.ATLAS),('expanded',tuple(replace(e,keywords=e.keywords+tuple(s.split())) for e,s in zip(atlas.ATLAS,EXTRA)))]:
        with patch.object(atlas,'ATLAS',entries):
            ids=list(r1.route_r1_candidate(pairs))
            vocab=[list(e.keywords) for e in entries]
            assert all(w.isalpha() for group in vocab for w in group)
            rows=[[p.node_id,p.b1.class_index,p.narrative_v0.class_index,str(r1.risk_terms(p)['score']),max(atlas.semantic_support(p.text))==0] for p in pairs]
            result[name]=dict(ids=ids,vocab=vocab,rows=rows,atlas_sha=digest(vocab),selection_sha=digest(ids))
    print(PrivateAudit('.local_artifacts/expanded_atlas_ablation').write(result))

if __name__=='__main__':main()
