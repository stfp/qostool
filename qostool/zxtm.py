#!/usr/bin/env python
# -*- coding: iso-8859-15 -*-
"""
zxtm: read zxtm logfiles
"""

import time
import re
import logging

def parse_zxtm_log_line(line):
    try:
        parts = line.split('|')
        duration = parts[1]
        host = parts[2]
        url = parts[5]
        http_code = parts[7]
        node_name = parts[-1]

        try:
            http_code = int(http_code)
        except:
            http_code = 0

        if duration == '-':
            duration = 0
        else:
            duration = float(duration)
        return duration, host, url, node_name, http_code
    except:
        logging.exception("parse_zxtm_log_line: could not parse line [%s]", line)

def logfilename_to_vserver(logfilename):
    return logfilename.split('.')[0]

def logfilename_to_timeperiod(logfilename):
    return '.'.join(logfilename.split('.')[-3:-2])

def get_actual_time_period():
    # ASSUMPTION on avedya zxtm logfile naming
    return time.strftime("%Y%m%d.%H", time.localtime())

def get_logfile_regexp(vservers, time_period):
    # ASSUMPTION on avedya zxtm logfile naming
    return re.compile("^(" + ("|".join(vservers)) + ")\..*\."+time_period+"\.log$")
