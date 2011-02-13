#!/usr/bin/env python
# -*- coding: iso-8859-15 -*-
"""
qos: module for configuration related stuff
"""

import os, os.path
import re
import logging

import util



DEFAULT_ROOT = "/tmp"
DEFAULT_ZXTM_ROOT = "/var/log/zxtm"

DEFAULT_TARGET_TIME = 0.5
DEFAULT_TARGET_PC = 90

class ConfigurationException(Exception):
    """ Configuration error
    """
    pass


class QosServiceConfig:
    def __init__(self, svc_id):
        self.svc_id = svc_id
        self.name = None
        self.apps = []
        self.target_time = DEFAULT_TARGET_TIME
        self.target_pc = DEFAULT_TARGET_PC
        self.zxtm_vservers = []
        self.zxtm_host_re = None # TODO support case where re isn't given
        self.apps_re = None
        self.ignore_re = None
        self.keep_params_re = None
        self.munin_apps = []
    
    def parse_file(self, file_name, parser=None):
        logging.debug("QosServiceConfig: Reading configuration file [%s]", file_name)
        if parser is None:
            parser = util.ConfigParserDef()
            parser.read(file_name)
        
        section = self.svc_id + ".service"
        self.name = parser.get(section, "name")
        self.apps = parser.get_list(section, "apps").get_values()

        regex = parser.get_def(section, "ignore_re", "^$")
        try:
            self.ignore_re = re.compile(regex)
        except:
            raise ConfigurationException("QosServiceConfig: %s.ignore_re [%s] is invalid" % (section, regex))

        regex = parser.get_def(section, "keep_params_re", None)
        try:
            if regex is not None:
                self.keep_params_re = re.compile(regex)
        except:
            raise ConfigurationException("QosServiceConfig: %s.keep_params_re [%s] is invalid" % (section, regex))
        
        self.target_time = parser.getfloat_def(section, "target_time", DEFAULT_TARGET_TIME)
        self.target_pc   = parser.getfloat_def(section, "target_pc", DEFAULT_TARGET_PC)
        self.zxtm_vservers = parser.get_list(section, "zxtm_vservers").get_values()
        try:
            self.munin_apps = parser.get_list(section, "munin_apps").get_values()
        except:
            self.munin_apps = []

        regex = parser.get_def(section, "zxtm_host_re", "^.*$")
        try:
            self.zxtm_host_re = re.compile(regex)
        except:
            raise ConfigurationException("QosServiceConfig: %s.zxtm_host_re [%s] is invalid" % (section, regex))
        
        self.apps_re = re.compile("^/("+'|'.join(self.apps)+")")
        
    def __repr__(self):
        result = ["QosServiceConfig"]
        attributes = [ 'svc_id', 'name', 'apps', 'ignore_re', 'keep_params_re', 'target_time', 'target_pc', 'zxtm_vservers', 'zxtm_host_re' ]
        for attr in attributes:
            result.append('\n  ')
            result.append(attr)
            result.append(':')
            result.append(unicode(getattr(self, attr)))
            result.append(' ')
        result.append('\n')
        return ''.join(result)


class QosEngineConfig:
    def __init__(self):
        self.root = DEFAULT_ROOT
        self.services = {}
        self.zxtm_root = DEFAULT_ZXTM_ROOT
        self.zxtm_vservers = []
    
    def parse_file(self, file_name, parser=None):
        logging.debug("QosEngineConfig: Reading configuration file [%s]", file_name)
        if parser is None:
            parser = util.ConfigParserDef()
            parser.read(file_name)
        
        section = "global"
        self.root = parser.get_def(section, "root", DEFAULT_ROOT)
        
        if not os.path.isdir(self.root):
            os.makedirs(self.root)

        for svcid in parser.get_list(section, "services").get_values():
            svc = QosServiceConfig(svcid)
            svc.parse_file(file_name, parser)
            self.services[svcid] = svc

        section = "zxtm"
        self.zxtm_root = parser.get_def(section, "root", DEFAULT_ZXTM_ROOT)
        self.zxtm_vservers = parser.get_list(section, "vservers").get_values()

    def __repr__(self):
        result = ["QosEngineConfig"]
        attributes = [ 'root', 'zxtm_root', 'zxtm_vservers' ]
        for attr in attributes:
            result.append('\n  ')
            result.append(attr)
            result.append(':')
            result.append(unicode(getattr(self, attr)))
            result.append(' ')
        result.append('\n')
        for s in self.services.values():
            result.append(unicode(s))
        return ''.join(result)
