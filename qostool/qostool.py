#! /usr/bin/env python
# -*- coding: iso-8859-15 -*-
"""
qos: module for utility classes and methods
"""

import sys
import re
import os
import logging

import config
import util
import workset
import zxtm
import sync
from sheet import Sheet

class DefaultEngine:

    def __init__(self):
        self.config = config.QosEngineConfig()
        self.workset_manager = workset.WorkSetManager()
    
    def configure(self):
        self.config.parse_file("/etc/qos/qos.cfg")

def sync_cmd(args):
    del args
    logging.debug("Running command sync")
    sync_engine = sync.SyncEngine()
    sync_engine.sync()

def summary_cmd(args):
    if len(args) < 1:
        usage()
    
    engine = DefaultEngine()
    for filename in args:
        wkset = engine.workset_manager.load(filename)
        wkset.summary()

def dump_cmd(args):
    if len(args) < 1:
        usage()
    
    engine = DefaultEngine()
    for filename in args:
        wkset = engine.workset_manager.load(filename)
        print wkset

def grep_matcher(pattern, page, options):
    if options.is_regex:
        return re_search_matcher(pattern, page, options)
    if options.case_insensitive:
        res = pattern.lower() in page.url.lower()
    else:
        res = pattern in page.url
    if options.invert_match:
        return not res
    else:
        return res
    
def re_search_matcher(regex, page, options):
    result = regex.search(page.url) is not None
    if options.invert_match:
        return not result
    else:
        return result

def re_match_matcher(regex, page, options):
    result = regex.match(page.url) is not None
    if options.invert_match:
        return not result
    else:
        return result

def display_slow_sorted(wkset, parent_workset, duration=0.5, sort_field_index=2, limit=None):
    result_sheet = Sheet()
    result_sheet.header("URL", "%Hits", "%Slow")
    
    for p in wkset.pages.values():
        hits_pc = float(p.hits) / parent_workset.total_hits * 100
        slow_pc = float(p.shape.get_hits_above(duration)) / parent_workset.shape.get_hits_above(duration) * 100
        result_sheet.line(p.url, hits_pc, slow_pc)

    hits_pc = float(wkset.shape.total_hits) / parent_workset.total_hits * 100
    slow_pc = float(wkset.shape.get_hits_above(duration)) / parent_workset.shape.get_hits_above(duration) * 100
    result_sheet.end_line("Total", hits_pc, slow_pc)

    result_sheet.sort(sort_field_index)
    
    if limit is not None:
        result_sheet.limit(limit)

    result_sheet.show()

class MatcherOptions:
    def __init__(self):
        self.case_insensitive = False
        self.invert_match = False
        self.is_regex = False

def generic_search(matcher, args):

    options = MatcherOptions()
    
    if '-i' in args:
        options.case_insensitive = True
        args.remove('-i')

    if '-v' in args:
        options.invert_match = True
        args.remove('-v')

    if '-e' in args:
        options.is_regex = True
        args.remove('-e')

    pattern = args[0]
    args = args[1:]
    
    if options.is_regex:
        pattern = re.compile(pattern)
        
    engine = DefaultEngine()

    dest_ws = workset.WorkSet()
    source_ws = create_aggregate_workset(engine, args)
    
    dest_ws.filter_aggregate(source_ws, matcher, pattern, options)

    display_slow_sorted(dest_ws, source_ws)

    
def grep_cmd(args):
    if len(args) < 1:
        usage()
    generic_search(grep_matcher, args)

def search_cmd(args):
    if len(args) < 1:
        usage()
    args.append('-e')
    generic_search(re_search_matcher, args)

def match_cmd(args):
    if len(args) < 1:
        usage()
    args.append('-e')
    generic_search(re_match_matcher, args)

def top_cmd(args):
    if len(args) < 1:
        usage()

    engine = DefaultEngine()

    source_ws = create_aggregate_workset(engine, args)
    
    print "\nTop slow pages:\n"
    display_slow_sorted(source_ws, source_ws, limit=20)

def status_top_cmd(args):
    if len(args) < 2:
        usage()
    
    http_code = 0
    try:    
        http_code = int(args[0])
    except:
        usage()

    if http_code == 0:
        usage()
    
    engine = DefaultEngine()            
    wkset = engine.workset_manager.load(args[1])
    
    result_sheet = Sheet()
    result_sheet.header("URL", "Hits", "Ratio")

    total_code_hits = wkset.http_codes.get(http_code, None)
    if total_code_hits is None:
        return

    total_code_hits_check = 0
    total_pc_check = 0.0
    for p in wkset.pages.values():
        
        code_hits = p.http_codes.get(http_code, None)
        if code_hits is None:
            continue
        
        code_pc = float(code_hits)/total_code_hits * 100

        total_code_hits_check += code_hits
        total_pc_check += code_pc

        result_sheet.line(p.url, code_hits, code_pc)

    result_sheet.end_line("Total", total_code_hits_check, total_pc_check)
    result_sheet.end_line("Check", total_code_hits, 100)

    result_sheet.sort(2)
    result_sheet.limit(20)

    print "\nHTTP status code %d breakdown:\n" % (http_code)
    result_sheet.show()


def munin_cmd(args):
    if len(args) > 1:
        usage()
    
    config_mode = False
    if (len(args) > 0) and args[0] == 'config':
        config_mode = True

    engine = DefaultEngine()
    engine.configure()

    for service in engine.config.services.values():
        logging.debug("munin: looking at svc:%s", service)
        for app in service.munin_apps:
            if config_mode:
                print "%s_%s.label %s/%s" % (service.svc_id, app, service.svc_id, app)
                continue

            ws_filename = engine.config.root + '/munin/' + sync.generate_munin_workset_file_name(service.svc_id, app)
            logging.debug("munin: looking at svc:%s app:%s in file %s", service.svc_id, app, ws_filename)
            try:
                wkset = engine.workset_manager.load(ws_filename)
                print "%s_%s.value %.2f" % (service.svc_id, app, 100 - wkset.shape.get_hits_pc_above(service.target_time))
                rf = open(ws_filename + ".read", "w")
                print >> rf, "OK"
                rf.close()
            except:
                pass

def qos_cmd(args):
    if len(args) < 1:
        usage()
    
    time = float(args[0])
    engine = DefaultEngine()
    for filename in args[1:]:
        wkset = engine.workset_manager.load(filename)
        print filename, 100 - wkset.shape.get_hits_pc_above(time)

def parse_cmd(args):
    logging.debug("Running command parse")
    if len(args) < 1:
        usage()

    dest_filename = args[-1]
    if os.path.isfile(dest_filename):
        usage()
        
    sources = list(set(args[:-1]))

    engine = DefaultEngine()

    dest_workset = workset.WorkSet()
    dest_workset.metadata["parse"] = "parse"
    dest_workset.metadata["file_name"] = dest_filename
    dest_workset.metadata["parse_source_files"] = sources
    
    for i in sources:
        mmap_file = util.open_mmap(i)
        while 1:
            line = mmap_file.readline()
            if not line:
                break
            duration, host, url, node_name, http_code = zxtm.parse_zxtm_log_line(line)
            dest_workset.hit(workset.cleanup_url(url), duration, node_name, http_code)

    engine.workset_manager.save(dest_workset, dest_filename)

def aggregate_cmd(args):
    logging.debug("Running command aggregate")
    if len(args) < 3:
        usage()
    
    dest_filename = args[-1]
    sources = args[:-1]
    engine = DefaultEngine()
    dest_workset = create_aggregate_workset(engine, sources)
    dest_workset.metadata["file_name"] = dest_filename
    engine.workset_manager.save(dest_workset, dest_filename)


def create_aggregate_workset(engine, sources):
    dest_workset = workset.WorkSet()
    dest_workset.metadata["creator"] = "aggregate"
    dest_workset.metadata["aggregate_source_files"] = sources
    
    for i in list(set(sources)):
        dest_workset.aggregate(engine.workset_manager.load(i))
    return dest_workset

def export_cmd(args):
    if len(args) < 1:
        usage()
    
    engine = DefaultEngine()
    for filename in args:
        wkset = engine.workset_manager.load(filename)
        for p in wkset.pages.values():
            p.export()

def compare_cmd(args):
    logging.debug("Running command compare")

    if len(args) != 2:
        usage()
    
    engine = DefaultEngine()    
    wkset1 = engine.workset_manager.load(args[0])
    wkset2 = engine.workset_manager.load(args[1])
    
    wkset1.compare(wkset2)

def check_cmd(args):
    logging.debug("Running command check")

    if len(args) < 1:
        usage()
    
    engine = DefaultEngine()
    for i in args:
        if engine.workset_manager.load(i).is_valid():
            print i, "OK"
        else:
            print i, "Invalid"

def report_cmd(args):
    logging.debug("Running command report")

    if len(args) < 1:
        usage()
    
    engine = DefaultEngine()
    for filename in args:
        wkset = engine.workset_manager.load(filename)
        # total actual hits
        total = wkset.total_hits + wkset.total_ignored
        # total errors + http 5xx codes
        errs = wkset.total_errors
        err5xx = 0
        for code in wkset.http_codes.keys():
            if code > 499 and code < 600 and code != 503:
                err5xx += wkset.http_codes[code]
        errs += err5xx
        # nb of requests that took more than 0.5s
        above05 = wkset.shape.get_hits_above(0.5)
        avail = 100 - (float(errs) / float(total) * 100)
        eff = 100 - (float(above05) / float(total) * 100)

        print "<table>"
        print "<tr><td width=\"30%%\">Hits</td><td width=\"70%%\">%d</td></tr>" % wkset.total_hits
        print "<tr><td>Ignored Hits</td><td>%d</td></tr>" % wkset.total_ignored
        print "<tr><td>Errors</td><td>%d</td></tr>" % wkset.total_errors
        print "<tr><td>HTTP 5xx responses</td><td>%d</td></tr>" % err5xx
        print "<tr><td><b>Availability</b></td><td>%.4f</td></tr>" % avail
        print "<tr><td><b>Efficiency</b></td><td>%.4f</td></tr>" % eff
        print "</table><br/><br/>"

        print "<table>"        
        keys = wkset.http_codes.keys()
        keys.sort()
        for code in keys:
            if code < 100:
                continue
            count = wkset.http_codes[code]
            pc = (float(count) / wkset.total_hits) * 100
            print "<tr><td width=\"30%%\">%d</td><td width=\"40%%\">%d</td><td width=\"30%%\">%.2f</td></tr>" % (code, count, pc)
    
        print "</table>"
    


def usage():
    print >> sys.stderr, """usage: qos.py command

Workset creation commands:

\t sync                                          get latest data from zxtm (normally called by a cron job)
\t parse ZXTMFILE1 [...]  DESTINATION            parse zxtm file(s) and save worksets files
\t check WORKSETFILE1 [...]                      runs a self check on workset file(s)
\t aggregate WORKSETFILE1 [...] DESTINATION      creates a new workset containing all the given worksets

Workset analysis commands:

\t summary  WORKSETFILE1 [...]                   print workset file(s) summaries
\t qos TIME WORKSETFILE1 [...]                   print % hits < time
\t grep [-i] [-v] [-e] expression WORKSETFILE1 [...]       shows pages counters matching the given expression or regexp
\t search [-v] expression WORKSETFILE1 [...]          shows pages counters matching the given regexp
\t match [-v] expression WORKSETFILE1 [...]           shows pages counters exactly matching the given regexp
\t top  WORKSETFILE1 [...]                       print slow pages top
\t status-top httpcode WORKSETFILE1 [...]        print http status code page breakdown

Integration commands:
\t munin                                         show current qos for each service/app in a format usable by munin

Unfinished commands:

\t compare WORKSETFILE1 WORKSETFILE2             compares two workset files
\t dump WORKSETFILE1 [...]                       dump workset file(s) contents
\t report WORKSETFILE1 [...]

"""
    sys.exit(1)    


def main():


    if len(sys.argv) < 2:
        usage()

    try:
        import psyco
        psyco.full()
        logging.debug("Psyco optimizations enabled")
    except ImportError:
        logging.debug("Psyco optimizations not available")

    command_map = {
        'parse'      :        parse_cmd,
        'summary'    :      summary_cmd,
        'sync'       :         sync_cmd,
        'qos'        :          qos_cmd,
        'aggregate'  :    aggregate_cmd,
        'compare'    :      compare_cmd,
        'check'      :        check_cmd,
        'grep'       :         grep_cmd,
        'search'     :       search_cmd,
        'match'      :        match_cmd,
        'export'     :       export_cmd,
        'top'        :          top_cmd,
        'dump'       :         dump_cmd,
        'status-top' :   status_top_cmd,
        'munin'      :        munin_cmd,
        'report'     :       report_cmd
    }
    
    command = sys.argv[1]
    try:
        command_map[command](sys.argv[2:])
    except:
        logging.exception("Error running command [%s]", command)
        sys.exit(1)


if __name__ == '__main__':
    main()
