import unittest
from llmgnn_sara.evaluation.homophily import measure
class HomophilyTests(unittest.TestCase):
 def test_homophilic_heterophilic_mixed_isolated(self):
  r,_,_=measure([(0,1),(0,2),(1,3)],[0,0,1,1,2],5)
  self.assertEqual(r[0]['homophily'],.5);self.assertEqual(r[2]['homophily'],0)
  self.assertIsNone(r[4]['homophily'])
  self.assertEqual(measure([(0,1)],[0,0],2)[0][0]['homophily'],1)
 def test_direction_duplicates_loops(self):
  a=measure([(0,1)],[0,1],2)[0]
  b,_,info=measure([(0,1),(1,0),(0,1),(0,0)],[0,1],2)
  self.assertEqual(a,b);self.assertEqual(info['duplicate_directed_edges'],1)
  self.assertEqual(info['self_loops_removed'],1)
 def test_alignment_and_domain(self):
  for edges,y,n in [([], [0],2),([(0,2)],[0,1],2),([], [8],1)]:
   with self.assertRaises(ValueError):measure(edges,y,n)
if __name__=='__main__':unittest.main()
