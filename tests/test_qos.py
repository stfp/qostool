import re
import logging
import unittest

import qostool
import qostool.util
import qostool.zxtm
import qostool.workset



class Test_Util_ValueList(unittest.TestCase):
    
    def test_valuelist_set_get(self):
        vl = qostool.util.ValueList()
        vl.set_values([1, 2, 3, 4])
        self.assertEqual(vl.get_values(), [1, 2, 3, 4])

    def test_valuelist_get_my_value(self):
        __docstring__ = """ make sure calls to get_my_value will return random values
        """
        vl = qostool.util.ValueList()
        vl.set_values([1, 2, 3, 4])
        my_values = set()
        # this tries to test randomness, so it could fail even if the code
        # does the correct thing - if that happens the only thing (?) we can
        # do is increase this loop counter
        for i in range(1000):
            v = vl.get_my_value(self)
            self.assertTrue(v in [1, 2, 3, 4])
            my_values.add(v)
        self.assertEquals(len(my_values), 4)

    def test_valuelist_split_values(self):
        vl = qostool.util.ValueList()
        vl.set_values(['A-1', 'B-2', 'C-3', 'D-4'])
        vl.split_values('-')
        self.assertEqual(vl.get_values(), [['A','1'], ['B','2'], ['C','3'], ['D','4']])

class Test_Util_KeepValueList(Test_Util_ValueList):
    
    def test_valuelist_get_my_value(self):
        __docstring__ = """ make sure calls to get_my_value will always return the same value
        """
        vl = qostool.util.KeepValueList()
        vl.set_values([1, 2, 3, 4])
        my_values = set()
        for i in range(1000):
            v = vl.get_my_value(self)
            self.assertTrue(v in [1, 2, 3, 4])
            my_values.add(v)
        self.assertEquals(len(my_values), 1)

class Test_Util_LockValueList(Test_Util_ValueList):
    
    def test_valuelist_get_my_value(self):
        """ make sure calls to get_my_value will always return the same value
        """
        vl = qostool.util.LockValueList()
        vl.set_values([1, 2, 3, 4])
        my_values = set()
        for i in range(1000):
            v = vl.get_my_value(self)
            self.assertTrue(v in [1, 2, 3, 4])
            my_values.add(v)
        self.assertEquals(len(my_values), 1)
        value_one = vl.get_my_value(self)
        value_two = vl.get_my_value("two")
        value_three = vl.get_my_value("three")
        value_four = vl.get_my_value("four")
        self.assertNotEqual(value_one, value_two)
        self.assertNotEqual(value_one, value_three)
        self.assertNotEqual(value_one, value_four)
        self.assertNotEqual(value_two, value_three)
        self.assertNotEqual(value_two, value_four)
        self.assertNotEqual(value_three, value_four)
        logging.info("++++ <Expected warning>")
        self.assertEquals(vl.get_my_value("five"), None)
        logging.info("++++ </Expected warning>")


class Test_Zxtm(unittest.TestCase):

    def setUp(self):
        self.lines = [ 
            "[21/Nov/2007:15:00:22 +0100]|0.000732|blogsperso.orange.fr|77.200.218.23|GET|/web/img/arrowrt.gif|image/gif|200|-|305|-|http://blogsperso.orange.fr/web/jsp/blog.jsp?blogID=381853|Mozilla/5.0 (Windows; U; Windows NT 6.0; fr; rv:1.8.0.12) Gecko/20070508 Firefox/1.5.0.12|0|10.1.42.66:8080|10.1.42.66:8080",
            "[21/Nov/2007:17:50:28 +0100]|0.016799|aolchat.fr|78.113.106.7|POST|/web/ChatServlet;jsessionid=agW4JcALfK19?U=1195663828382615|text/html|200|-|484|ebNewBandWidth_.aolchat.fr=1138%3A1193484501734; s_cc=true; s_sq=aolfrglobal%2Caolfrportalnew%3D%2526pid%253DChat%252520%25253A%252520s.prop1%252520%25253A%252520sprop2%252520%25253A%252520sprop16%2526pidt%253D1%2526oid%253Dfunctionanonymous%252528%252529%25257BsendMessage%252528%252529%25253B%25257D%2526oidt%253D2%2526ot%253DDIV%2526oi%253D317|http://aolchat.fr/web/chat.jsp;jsessionid=agW4JcALfK19?userID=2219794|Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 2.0.50727)|0|212.73.213.173:80|212.73.213.173:80",
            "[21/Nov/2007:17:53:15 +0100]|-|www.mynrj.com|86.196.47.55|GET|/media/image?p=hDupF8MNFGtnZDCVtItPr0vpl86SveFbZ8vN@tqWQDPjtk30G9SSYGN18BtKcOFr.|-|200|-|3258|JSESSIONID=aM5iaHjUDSe-; X-Mapping-oihfabgp=DF6250420263888DDC5C6905A4082F8A|http://www.mynrj.com/web/membre/jenifer-lunatique|Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322)|0|-|-",
            "[21/Nov/2007:17:54:08 +0100]|0.019221|www.zapzone.fr|90.1.154.63|GET|/web/jsp/inc/search_users_result.jsp?totalCount=508&onlyOnline=true&userFilterType=0|text/html; charset=iso-8859-1|200|-|1621|__utma=174439721.964439698.1168035844.1195653305.1195660951.812; __utmz=174439721.1188239596.627.1.utmccn=(direct)|utmcsr=(direct)|utmcmd=(none); __utmb=174439721; __utmc=174439721; JSESSIONID=aZ4zuH5PLxU7|http://www.zapzone.fr/web/jsp/searchUsersResult.jsp?onlyOnline=true|Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; FREE; .NET CLR 2.0.50727; .NET CLR 1.1.4322)|0|10.1.42.52:8080|10.1.42.52:8080",
        ]
        self.values = [
            (0.00073200000000000001, 'blogsperso.orange.fr', '/web/img/arrowrt.gif', '10.1.42.66:8080', 200),
            (0.016799000000000001, 'aolchat.fr', '/web/ChatServlet;jsessionid=agW4JcALfK19?U=1195663828382615', '212.73.213.173:80', 200),
            (0, 'www.mynrj.com', '/media/image?p=hDupF8MNFGtnZDCVtItPr0vpl86SveFbZ8vN@tqWQDPjtk30G9SSYGN18BtKcOFr.', '-', 200),
            (0.019220999999999999, 'www.zapzone.fr', '/web/jsp/inc/search_users_result.jsp?totalCount=508&onlyOnline=true&userFilterType=0', '10.1.42.52:8080', 200)
        ]
    

    def test_parse_zxtm_log_line(self):
        for l, v in zip(self.lines, self.values):
            values = qostool.zxtm.parse_zxtm_log_line(l)
            self.assertEquals(values, v)

class Test_Workset(unittest.TestCase):

    def setUp(self):
        self.urls = [
            '/web/img/arrowrt.gif',
            '/web/ChatServlet;jsessionid=agW4JcALfK19?U=1195663828382615',
            '/media/image?p=hDupF8MNFGtnZDCVtItPr0vpl86SveFbZ8vN@tqWQDPjtk30G9SSYGN18BtKcOFr.',
            '/web/jsp/inc/search_users_result.jsp?totalCount=508&onlyOnline=true&userFilterType=0',
            '/super/cool?method=display&incredible=maybe&fantastic=false',
            '/super/cool?method=display&incredible=maybe&fantastic=false&blah=1928&zut',
        ]
        self.clean_urls = [
            '/web/img/arrowrt.gif',
            '/web/ChatServlet?U',
            '/media/image?p',
            '/web/jsp/inc/search_users_result.jsp?totalCount&onlyOnline&userFilterType',
            '/super/cool?method&incredible&fantastic',
            '/super/cool?method&incredible&fantastic&blah&zut',
        ]
        self.clean_urls_keep_params = [
            '/web/img/arrowrt.gif',
            '/web/ChatServlet?U',
            '/media/image?p',
            '/web/jsp/inc/search_users_result.jsp?totalCount&onlyOnline=true&userFilterType',
            '/super/cool?method=display&incredible&fantastic=false',
            '/super/cool?method=display&incredible&fantastic=false&blah&zut',
        ]        

    def test_cleanup_url(self):
        for u, c in zip(self.urls, self.clean_urls):
            self.assertEquals(qostool.workset.cleanup_url(u), c)

    def test_cleanup_url_keep_params(self):
        keep_params_re = re.compile("^(onlyOnline|method|fantastic)$")
        for u, c in zip(self.urls, self.clean_urls_keep_params):
            self.assertEquals(qostool.workset.cleanup_url(u, keep_params_re), c)
        


if __name__ == '__main__':
    logging.baseConfig()
    unittest.main()
