#!/usr/bin/env python
# -*- coding: iso-8859-15 -*-
"""
qos: module for utility classes and methods
"""

import os, os.path
import mmap
import random
import logging
import ConfigParser


def makedirs_for_file(filename):
    folder = os.path.split(filename)[0]
    if len(folder) > 0 and not os.path.isdir(folder):
        os.makedirs(folder)

def importer(name):
    """ dynamic import helper
    """
    module = __import__('.'.join(name.split('.')[:-1]))
    return getattr(module, name.split('.')[-1])

class ValueList:
    """ basic random value list: every call to get_my_value will return a random value
    """
    def __init__(self):
        self.values = []
    
    def set_values(self, the_values):
        self.values = the_values

    def get_values(self):
        return self.values

    def get_my_value(self, dummy):
        return random.choice(self.values)

    def split_values(self, separator):
        self.values = [ v.split(separator) for v in self.values ]
    
    def __repr__(self):
        return "<ValueList [%s]>" % (unicode(self.values))

class LockValueList(ValueList):
    """ a value list where the owning/calling object will always get the same value when
        calling 'get_my_value'; it also ensures every caller get a different value
        usage example: values that should only be used once, ie. login/password couple
    """
    def __init__(self):
        ValueList.__init__(self)
        self.owner_map = {}

    def get_my_value(self, for_object):
        """ gets a value suitable for the given calling/owning object
        """
        if not self.owner_map.has_key(for_object):
            if len(self.values) == 0:
                logging.warning("LockValueList: no value left for owner object [%s]", for_object)
                return None
            choice = random.choice(self.values)
            self.values.remove(choice)
            self.owner_map[for_object] = choice
            return choice
        else:
            return self.owner_map[for_object]

    def __repr__(self):
        return "<LockValueList [%s]>" % (unicode(self.values))

class KeepValueList(ValueList):
    """ a value list where the owning/calling object will always get the same value when
        calling 'get_my_value'. unlike LockValueList one value can be affected to multiple owner/callers.
        usage example: values that can be used by multiple browsers but kept stable per browser, ie. user-agent header
    """
    def __init__(self):
        ValueList.__init__(self)
        self.owner_map = {}

    def get_my_value(self, for_object):
        """ gets a value
        """
        if not self.owner_map.has_key(for_object):
            choice = random.choice(self.values)
            self.owner_map[for_object] = choice
            return choice
        else:
            return self.owner_map[for_object]
        
    def __repr__(self):
        return "<KeepValueList [%s]>" % (unicode(self.values))


class ConfigParserDef(ConfigParser.SafeConfigParser):
    """ a ConfigParser variant with support for default values
    """

    def get_def(self, section, option, default):
        """ get, returning a default value for missing options
        """
        try:
            return unicode(self.get(section, option))
        except ConfigParser.NoOptionError:
            return default

    def getint_def(self, section, option, default):
        """ getint, returning a default value for missing options
        """
        try:
            return self.getint(section, option)
        except ConfigParser.NoOptionError:
            return default

    def getboolean_def(self, section, option, default):
        """ getboolean, returning a default value for missing options
        """
        try:
            return self.getboolean(section, option)
        except ConfigParser.NoOptionError:
            return default

    def getfloat_def(self, section, option, default):
        """ getfloat, returning a default value for missing options
        """
        try:
            return self.getfloat(section, option)
        except ConfigParser.NoOptionError:
            return default

    def get_list(self, section, option, allow_special=True):
        """ gets a list of values:
            if the option value starts with 'keep:' or 'lock:', TODO: document
            if the option value starts with 'file:', values are read from the separate file
            else, the value is split by ','
        """
        value_str = self.get(section, option)
        
        if value_str.startswith('keep:'):
            assert allow_special, "This option doesn't allow the special 'keep' behaviour"
            vlist = KeepValueList()
            value_str = value_str[5:]
        elif  value_str.startswith('lock:'):
            assert allow_special, "This option doesn't allow the special 'lock' behaviour"
            vlist = LockValueList()
            value_str = value_str[5:]
        else:
            vlist = ValueList()
        
        if value_str.startswith('file:'):
            filep = open(value_str[5:], 'r')
            values = filep.readlines()
            filep.close()
        else:
            values = self.get(section, option).split(',')
            
        vlist.set_values([ unicode(v.strip()) for v in values ])
        return vlist
        
def open_mmap(filename):
    logging.debug("Openning mmap for file [%s]", filename)
    fp = open(filename, "rb")
    size = os.path.getsize(filename)
    return mmap.mmap(fp.fileno(), size, mmap.MAP_PRIVATE, mmap.PROT_READ)
