"""Unit test for oracleDB.py"""
import unittest
from oracleDB import OracleDB

class AddSource(unittest.TestCase):
    def setUp(self):
        self.oracle = OracleDB()
    
    def testAddSource(self):
        """addSource should return true when it's a new source for a content, and false
        when the tuple content-IP is already in the map """
        result = self.oracle.addSource('c1','10.0.0.1')
        self.assertTrue(result)
        result = self.oracle.addSource('c1','10.0.0.1')
        self.assertFalse(result)
        #result = oracle.addSource('c1','10.0.0.2')
        #self.assertEqual(result, True)
     
class RemoveContent(unittest.TestCase):
    def setUp(self):
        self.oracle = OracleDB()
        self.oracle.addSource('c1','10.0.0.1')    

    def testRemoveMissingContent(self):
        """removeSource should fail if the content is unknown """
        self.assertRaises(self.oracle.UnknownContentError,self.oracle.removeSource,'c3','10.0.0.1')
    
    def testRemoveMissingSource(self):
        """removeSource should fail if the source is unknown """
        self.assertRaises(self.oracle.UnknownSourceError,self.oracle.removeSource,'c1','10.0.0.2')
        
    def testRemoveExistingSource(self):
        """Test successful removal of a source"""
        self.oracle.removeSource('c1','10.0.0.1')
        result = self.oracle.addSource('c1','10.0.0.1')
        self.assertTrue(result)

class GetSource(unittest.TestCase):
    def setUp(self):
        self.oracle = OracleDB()
        self.oracle.addSource('c1','10.0.0.1')
        self.oracle.addSource('c1','10.0.0.2')
        
    def testGetSource(self):
        """getSource should return a valid source if one is known"""
        source = self.oracle.getSource('c1')
        self.assertTrue(source in ['10.0.0.1','10.0.0.2'])
        
    def testGetMissingContent(self):
        """getSource should return None if the content is unknown """
        source = self.oracle.getSource('c2')
        self.assertEqual(source, None)   
        
class ListSources(unittest.TestCase):
    def setUp(self):
        self.oracle = OracleDB()
    
    def testEmptyListSource(self):
        """listSource should return an empty list if no source is known"""
        sources = self.oracle.listSources('c1')
        self.assertEqual(len(sources),0)
        
    def testNonEmptyListSources(self):
        """listSources should return a list of all known sources for a given content"""
        self.oracle.addSource('c1','10.0.0.1')
        sources = self.oracle.listSources('c1')
        self.assertEqual(len(sources),1)
        self.assertTrue('10.0.0.1' in sources)
        
class Clear(unittest.TestCase):
    def setUp(self):
        self.oracle = OracleDB()
    
    def testClearContent(self):
        """clear(content) should eliminate all sources for the given content"""
        self.oracle.addSource('c1','10.0.0.1')
        self.oracle.addSource('c1','10.0.0.2')
        self.oracle.addSource('c2','10.0.0.1')
        self.oracle.clear('c1')
        source = self.oracle.getSource('c1')
        self.assertEqual(source, None)
        sources = self.oracle.listSources('c2')
        self.assertEqual(len(sources),1)
        
    def testClearAll(self):
        """clear() with no parameters hould clean the entire map"""
        self.oracle.addSource('c1','10.0.0.1')
        self.oracle.addSource('c1','10.0.0.2')
        self.oracle.addSource('c2','10.0.0.1')
        self.oracle.clear()
        source = self.oracle.getSource('c1')
        self.assertEqual(source, None)
        sources = self.oracle.listSources('c2')
        self.assertEqual(len(sources),0)

if __name__ == '__main__':
    unittest.main()
