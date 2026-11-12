import unittest
from llmgnn_sara.annotation.sara_lite import decide,PROTOCOL

class LiteTests(unittest.TestCase):
    def test_existing_router_is_order_independent(self):
        from llmgnn_sara.sara2.policy import Pair,Annotation
        from llmgnn_sara.sara3.r1_candidate import route_r1_candidate
        pairs=[Pair(Annotation(i,i%7,80),Annotation(i,(i+1)%7,90),'synthetic neural network') for i in range(40)]
        self.assertEqual(route_r1_candidate(pairs),route_r1_candidate(reversed(pairs)))
        self.assertEqual(len(route_r1_candidate(pairs)),37)
    def value(self,action='SWITCH',c=2):
        return dict(action=action,proposed_class_index=c,support_quotes=['retrieving prior cases'],counter_quotes=[],primary_topic='Adaptation of previously observed cases',reason_code='TARGET_SUPPORT' if action=='SWITCH' else 'BASELINE_SUPPORTED',uncertainty='NONE')
    def test_keep_and_candidate_or_third_switch(self):
        text='Learning by retrieving prior cases.'
        for c in (1,2,6):
            self.assertEqual(decide(self.value(c=c),text,0)['class_index'],c)
        self.assertEqual(decide(self.value('KEEP',0),text,0)['action'],'KEEP')
    def test_abstain(self):
        v=self.value('ABSTAIN',None);v.update(reason_code='CONFLICT',uncertainty='CONFLICT')
        self.assertIsNone(decide(v,'retrieving prior cases',0)['class_index'])
    def test_quote_and_contradiction_and_domain(self):
        for change in (dict(support_quotes=['fabricated']),dict(proposed_class_index=9),
                       dict(proposed_class_index=0),dict(uncertainty='CONFLICT'),
                       dict(primary_topic='case based'),dict(counter_quotes=['retrieving prior cases'])):
            v=self.value();v.update(change)
            with self.assertRaises(ValueError):decide(v,'retrieving prior cases',0)
    def test_missing_malformed_and_no_confidence_admission(self):
        for v in (None,{},[],{'confidence':99}):
            with self.assertRaises(ValueError):decide(v,'text',0)
        d=decide(self.value(),'retrieving prior cases',0)
        self.assertIsNone(d['confidence']);self.assertEqual(d['training_admission_status'],'NOT_ADMITTED')
        self.assertIsNone(PROTOCOL['execution']['approved_cap_usd'])
        self.assertEqual(PROTOCOL['budget'],37)
    def test_matched_controls_and_capacity(self):
        from llmgnn_sara.annotation.sara_lite_freeze import controls
        v,status=controls({0:0,1:1,2:1},{0},{0:dict(class_index=1)})
        self.assertEqual(v['D'],{0:0,1:1,2:1})
        self.assertEqual(status['status'],'BLOCKED_CLASS_CAPACITY')
        v,status=controls({0:0,1:1,2:1},{0},{0:dict(class_index=None)})
        self.assertEqual(sum(c is not None for c in v['C'].values()),sum(c is not None for c in v['D'].values()))
        self.assertEqual(status['status'],'AVAILABLE')

if __name__=='__main__':unittest.main()
