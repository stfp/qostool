#!/usr/bin/env python
# -*- coding: iso-8859-15 -*-
"""
qos: module for utility classes and methods
"""

import sys, cPickle, gzip
import logging

import util

QOS_SHAPE_RESOLUTION = 0.1 # in seconds
QOS_SHAPE_MAX_TIME = 5 # in seconds
QOS_SHAPE_HIST_WIDTH = 20
QOS_SHAPE_MAX_INDEX = int(QOS_SHAPE_MAX_TIME/QOS_SHAPE_RESOLUTION)

MODE_URI, MODE_SEMICOL, MODE_QUERY, MODE_QVALUE, MODE_KEPTQVALUE = range(5)

def cleanup_url(url, keep_params_re=None):
    mode = MODE_URI
    result = ""
    start = 0
    index = 0
    for c in url:
        if mode == MODE_URI:
            if c == ';':
                result += url[start:index]
                mode = MODE_SEMICOL
            elif c == '?':
                result += url[start:index]
                mode = MODE_QUERY
                start = index
        elif mode == MODE_SEMICOL:
            if c == '?':
                mode = MODE_QUERY
                start = index
        elif mode == MODE_QUERY:
            if c == '=':
                param_name = url[start:index]
                if keep_params_re is not None and keep_params_re.match(param_name[1:]) is not None:
                    mode = MODE_KEPTQVALUE
                else:
                    mode = MODE_QVALUE
                    result += param_name
        elif mode == MODE_KEPTQVALUE:
            if c == '&':
                result += url[start:index]
                mode = MODE_QUERY
                start = index
        elif mode == MODE_QVALUE:
            if c == '&':
                mode = MODE_QUERY
                start = index
        index += 1
    if mode == MODE_URI or mode == MODE_QUERY or mode == MODE_KEPTQVALUE:
        result += url[start:index]
    return result

def aggregate_http_codes(obj, other_obj):
    try:        
        for code in other_obj.http_codes.keys():
            if not obj.http_codes.has_key(code):
                obj.http_codes[code] = other_obj.http_codes[code]
            else:
                obj.http_codes[code] += other_obj.http_codes[code]
    except AttributeError:
        pass

def aggregate_nodes(obj, other_obj):
    try:        
        for n in other_obj.nodes.keys():
            if not obj.nodes.has_key(n):
                obj.nodes[n] = other_obj.nodes[n]
            else:
                obj.nodes[n].aggregate(other_obj.nodes[n])
    except AttributeError:
        pass

class QosShape:
    def __init__(self):
        self.shape = [0]*QOS_SHAPE_MAX_INDEX
        self.total_hits = 0
        self.resolution = QOS_SHAPE_RESOLUTION
        self.max_time = QOS_SHAPE_MAX_TIME
    
    def compare(self, other_qos_shape, out=sys.stdout):
        if self.resolution != other_qos_shape.resolution:
            logging.error("Cannot compare QosShape with different resolution !")

        if len(self.shape) != len(other_qos_shape.shape):
            logging.warning("When comparing two QosShape with different max_times, we will pick the smallest one")

        logging.debug("QosShape.compare: not implemented !")
        print >> out, "QosShape.compare: Not implemented !"

    def aggregate(self, other_qos_shape):
        if self.resolution != other_qos_shape.resolution:
            logging.error("Cannot aggregate QosShape with different resolution !")

        if len(self.shape) != len(other_qos_shape.shape):
            logging.warning("When aggregating two QosShape with different max_times, we will pick the smallest one")

        self.total_hits += other_qos_shape.total_hits
        
        i = 0
        minlen = min(len(self.shape), len(other_qos_shape.shape))
        while i < minlen:
            self.shape[i] += other_qos_shape.shape[i]
            i += 1
    
    def hit(self, time):
        self.total_hits += 1
        
        i = int(time/QOS_SHAPE_RESOLUTION)
        if i >= QOS_SHAPE_MAX_INDEX:
            i = QOS_SHAPE_MAX_INDEX-1

        while i >= 0:
            self.shape[i] += 1
            i -= 1

    def get_hits_above(self, time):
        return self.shape[int(time/QOS_SHAPE_RESOLUTION)]
        
    def get_hits_pc_above(self, time):
        return (float(self.get_hits_above(time)) / self.total_hits * 100)

    def get_dist(self):
        dist = [0]*len(self.shape)
        prev = 0
        for i in range(len(self.shape) - 1, -1, -1):
            dist[i] = self.shape[i] - prev
            prev = self.shape[i]
        return dist
    
    def invert(self, values):
        res = [0] * len(values)
        refv = values[0]
        for i in range(len(values)):
            res[i] = refv - values[i]
        return res
    
    def show_histogram(self, aggregated=False, inverted=False, out=sys.stdout):
        if aggregated:
            dist = self.shape
        else:
            dist = self.get_dist()
        if inverted:
            dist = self.invert(dist)
            
        m = max(dist)
        zero_count = 0
        print >> out," time   |    hits  |   % hits | visual"
        print >> out,"--------+----------+----------+---------------------"
        for i in range(len(dist)):
            if dist[i] == 0:
                zero_count += 1
                if zero_count > 1:
                    if zero_count == 2:
                        print >> out,"  ...   |          |          |"
                    continue
                else:
                    print >> out,"% 5.2f   |          |          |     " % (i*QOS_SHAPE_RESOLUTION)
            else:
                zero_count = 0
                f = (float(dist[i]) / m) * QOS_SHAPE_HIST_WIDTH
                r = f - int(f)
                if f - int(f) > 0.5:
                    r = '-'
                else:
                    r = ''
                print >> out, "% 5.2f   |% 8d  | % 8.2f | %s" % (i * QOS_SHAPE_RESOLUTION, dist[i], float(dist[i]) / self.total_hits * 100, '#' * int(f) + r)

class WorkSet:
    
    def __init__(self):
        self.pages = {}
        self.nodes = {}
        self.total_hits = 0
        self.total_errors = 0
        self.total_ignored = 0
        self.shape = QosShape()
        self.metadata = {}
        self.http_codes = {}

    def hit(self, url, time, node_name=None, http_code=None):
        self.total_hits += 1
        if time == 0 and http_code == 0:
            self.total_errors += 1
            return

        page = self.pages.get(url, None)
        if page is None:
            page = Page(url)
            self.pages[url] = page

        page.hit(time, node_name, http_code)

        self.shape.hit(time)
        
        try:
            if node_name is not None:
                node = self.nodes.get(node_name, None)
                if node is None:
                    node = Node(node_name)
                    self.nodes[node_name] = node
                node.hit(time, http_code)

            if http_code is not None:
                self.http_codes[http_code] = self.http_codes.get(http_code, 0) + 1
        except AttributeError:
            pass
                    
    def ignore_hit(self, url, time, node_name=None, http_code=None):
        self.total_ignored += 1
    
    def compare(self, other_workset, out=sys.stdout):
        if self.total_hits != other_workset.total_hits:
            print >> out, "total_hits_diff: ", other_workset.total_hits - self.total_hits
        if self.total_errors != other_workset.total_errors:
            print >> out, "total_errors_diff: ", other_workset.total_errors - self.total_errors

        self.shape.compare(other_workset.shape, out)
        
        for p in self.pages.keys():
            if not other_workset.pages.has_key(p):
                print >> out, "-" , p
            else:
                self.pages[p].compare(other_workset.pages[p], out)

        for p in other_workset.pages.keys():
            if not self.pages.has_key(p):
                print >> out, "+", p, "hits:", other_workset.pages[p].hits
    
    def aggregate(self, other_workset):
        self.total_hits += other_workset.total_hits
        self.total_errors += other_workset.total_errors
        self.shape.aggregate(other_workset.shape)

        try:
            self.total_ignored += other_workset.total_ignored
        except:
            pass

        aggregate_nodes(self, other_workset)
        aggregate_http_codes(self, other_workset)

        for p in other_workset.pages.keys():
            if not self.pages.has_key(p):
                self.pages[p] = other_workset.pages[p]
            else:
                self.pages[p].aggregate(other_workset.pages[p])

    # FIXME ? missing total_errors, http_codes aggregation ?
    def filter_aggregate(self, other_workset, filter_function, filter_arg, filter_options):
        for page in other_workset.pages.values():
            if not filter_function(filter_arg, page, filter_options):
                continue

            self.total_hits += page.hits
            self.shape.aggregate(page.shape)

            if not self.pages.has_key(page.url):
                self.pages[page.url] = other_workset.pages[page.url]
            else:
                self.pages[page.url].aggregate(other_workset.pages[page.url])

    def summary(self, out=sys.stdout):
        print >> out, "WorkSet Summary"
        print >> out, "\tTotal hits:", self.total_hits
        print >> out, "\tTotal errs:", self.total_errors
        try:
            print >> out, "\tTotal ignored hits: %d" % (self.total_ignored)
        except:
            pass
        print >> out, "\tDistinct pages:", len(self.pages.keys())
        print >> out, "\tAbove 0.5:", self.shape.get_hits_above(0.5)
        print >> out, "\tAbove 1.5:", self.shape.get_hits_above(1.5)
        print >> out, "\n\tPer-Node\t\thits\t0.5\t1.5"
        for i in self.nodes.values():
            print >> out, "\t%s\t%d\t%d\t%d" % (i.name, i.hits, i.shape.get_hits_above(0.5),  i.shape.get_hits_above(1.5))
        print >> out, "\n\tPer-HTTP Code\tcode\thits\tratio"
        
        try:
            for i in self.http_codes.keys():
                print >> out, "\t\t\t%s\t%d\t%2.2f" % (i, self.http_codes[i], float(self.http_codes[i]) * 100 / self.total_hits)
        except AttributeError:
            pass        

    def is_valid(self):
        if self.total_errors > self.total_hits:
            logging.warn("is_valid: total_errors is greater than total_hits")
            return False
        pages_total_hits = 0
        for p in self.pages.values():
            pages_total_hits += p.hits
        if pages_total_hits != self.total_hits:
            logging.warn("is_valid: total_hits and pages total hits differ")
        return True

    def page_summary(self, out=sys.stdout):
        for p in self.pages.values():
            p.summary(out)

    
class WorkSetManager:
    def __init__(self):
        pass
    
    def load(self, worksetfilename):
        try:
            try:
                infile = gzip.open(worksetfilename, "rb")
                data = infile.read()
                infile.close()
            except IOError:
                infile = open(worksetfilename, "rb")
                data = infile.read()
                infile.close()

            return cPickle.loads(data)
            
        except cPickle.UnpicklingError, unpe:
            logging.warn("Could not load file [%s] (cPickle error)" % (worksetfilename))
            raise unpe
    
    def save(self, workset, filename):
        logging.debug("WorkSetManager: saving %s" % (filename))
        
        util.makedirs_for_file(filename)

        outfile = gzip.GzipFile(filename, "wb+", 5)
        cPickle.dump(workset, outfile)
        outfile.close()        


class Page:
    def __init__(self, url):
        self.url = url
        self.max_time = 0
        self.min_time = 100000
        self.hits = 0
        self.total_time = 0
        self.errors = 0
        self.shape = QosShape()
        self.nodes = {}
        self.http_codes = {}

    def export(self, out=sys.stdout):
        print >> out, "%s|%.2f|%.2f|%.2f|%d|%d" % (self.url, self.max_time, self.min_time, self.total_time, self.hits, self.errors )

    def aggregate(self, other_page):
        self.max_time = max(self.max_time, other_page.max_time)
        self.min_time = min(self.min_time, other_page.min_time)
        self.hits += other_page.hits
        self.total_time += other_page.total_time
        self.shape.aggregate(other_page.shape)
        self.errors += other_page.errors
        aggregate_nodes(self, other_page)
        aggregate_http_codes(self, other_page)        


    def compare(self, other_page, out=sys.stdout):
        if self.hits != other_page.hits:
            print >> out, "Page", self.url, "hits_diff", other_page.hits-self.hits

    def hit(self, time, node_name=None, http_code=None):
        self.hits += 1
        if time == 0:
            self.errors += 1
            return
        self.total_time += time


        if time > self.max_time:
            self.max_time = time
        elif time < self.min_time:
            self.min_time = time

        self.shape.hit(time)

        try:
            if node_name is not None:
                node = self.nodes.get(node_name, None)
                if node is None:
                    node = Node(node_name)
                    self.nodes[node_name] = node
                node.hit(time, http_code)
        except AttributeError:
            pass
        
        try:
            if http_code is not None:
                self.http_codes[http_code] = self.http_codes.get(http_code, 0) + 1
        except AttributeError:
            pass

    def summary(self, out=sys.stdout):
        http_code_summary = ""
        try:
            for i in self.http_codes.keys():
                http_code_summary += " %s:%d:%2.2f" % (i, self.http_codes[i], float(self.http_codes[i]) * 100 / self.hits)
        except AttributeError:
            pass
        
        print >> out, "%s hits: %d errors: %d max: %d min: %d above.5: %d %s" % (self.url, self.hits, self.errors, self.max_time, self.min_time, self.shape.get_hits_above(0.5), http_code_summary)

class Node:
    def __init__(self, node_name):
        self.name = node_name.strip()
        self.max_time = 0
        self.min_time = 100000
        self.hits = 0
        self.total_time = 0
        self.errors = 0
        self.shape = QosShape()
        self.http_codes = {}

    def export(self, out=sys.stdout):
        print >> out, "%s|%.2f|%.2f|%.2f|%d|%d" % (self.name, self.max_time, self.min_time, self.total_time, self.hits, self.errors )
        
    def aggregate(self, other_node):
        self.max_time = max(self.max_time, other_node.max_time)
        self.min_time = min(self.min_time, other_node.min_time)
        self.hits += other_node.hits
        self.total_time += other_node.total_time
        self.shape.aggregate(other_node.shape)
        self.errors += other_node.errors
        aggregate_http_codes(self, other_node)
        
    def compare(self, other_node, out=sys.stdout):
        if self.hits != other_node.hits:
            print >> out, "Node", self.name, "hits_diff", other_node.hits-self.hits
        
    def hit(self, time, http_code=None):
        self.hits += 1
        
        if time == 0:
            self.errors += 1
            return
        
        self.total_time += time
        if time > self.max_time:
            self.max_time = time
        elif time < self.min_time:
            self.min_time = time
        
        self.shape.hit(time)
        
        try:
            if http_code is not None:
                self.http_codes[http_code] = self.http_codes.get(http_code, 0) + 1
        except AttributeError:
            pass
