#!/usr/bin/env python
# -*- coding: iso-8859-15 -*-
"""
qos: module for utility classes and methods
"""

import os, os.path
import dircache
import cPickle
import stat
import logging

import config
import util
import workset
import zxtm

class SyncLogFile:
    def __init__(self, filename, time_period):
        self.zxtm_vserver = zxtm.logfilename_to_vserver(filename)
        self.time_period = time_period
        self.filename = filename
        self.size = 0
        self.closable = False

class SyncEngineState:
    def __init__(self):
        self.current_logfiles = {}

    def __repr__(self):
        return "<SyncEngineState current_logfiles:%s>" % (repr(self.current_logfiles))


def generate_workset_file_name(time_period, service, app):
    # 20070222.17 -> 2007/02/22/17
    return service + '/' + time_period[0:4] + '/' + time_period[4:6] + '/' + time_period[6:8] + '/' + time_period[9:] + '/' + app + '.' + time_period + ".ws"

def generate_munin_workset_file_name(service, app):
    # 20070222.17 -> 2007/02/22/17
    return service + '/' + app + '.ws'


class SyncEngine:

    def __init__(self):
        self.workset_manager = workset.WorkSetManager()
        self.config = config.QosEngineConfig()
        self.config.parse_file("/etc/qos/qos.cfg")
        self.state = None
        self.opened_worksets = {}
        self.opened_munin_worksets = {}
        self.current_time_period = zxtm.get_actual_time_period()
        

    def handle_new_logfiles(self):
        regex = zxtm.get_logfile_regexp(self.config.zxtm_vservers, self.current_time_period)
        
        for f in dircache.listdir(self.config.zxtm_root):
            if regex.match(f) and not self.state.current_logfiles.has_key(f):
                self.state.current_logfiles[f] = SyncLogFile(f, self.current_time_period)
    
    def create_initial_state(self):
        self.state = SyncEngineState()
        self.handle_new_logfiles()
        logging.debug("SyncEngine: initial state created: %s", repr(self.state))
        
    def load_state(self):
        state_file_name = self.config.root + "/state/sync.state"
        if not os.path.isfile(state_file_name):
            self.create_initial_state()
        else:
            infile = open(state_file_name, "rb")
            self.state = cPickle.load(infile)
            infile.close()


    def get_workset(self, time_period, svc_id, app):
        wset_key = time_period + '-' + svc_id + '-' + app
        wset = self.opened_worksets.get(wset_key, None)
        if wset is not None:
            return wset
            
        ws_filename = generate_workset_file_name(time_period, svc_id, app)            

        try:
            wset = self.workset_manager.load(self.config.root + "/data/" + ws_filename)
            logging.debug("Loaded existing workset %s", ws_filename)
        except:
            logging.debug("Creating new workset")
            wset = workset.WorkSet()
            wset.metadata["creator"] = "qostool"
            wset.metadata["file_name"] = ws_filename

        self.opened_worksets[wset_key] = wset
        return wset

    def get_munin_workset(self, svc_id, app):
        wset_key = svc_id + '-' + app
        wset = self.opened_munin_worksets.get(wset_key, None)
        if wset is not None:
            return wset
            
        ws_filename = generate_munin_workset_file_name(svc_id, app)            

        if not os.path.isfile(self.config.root + "/munin/" + ws_filename + ".read"):
            try:
                wset = self.workset_manager.load(self.config.root + "/munin/" + ws_filename)
                logging.debug("Loaded existing munin workset %s", ws_filename)
                self.opened_munin_worksets[wset_key] = wset
                return wset
            except:
                pass

        logging.debug("Creating new munin workset")
        wset = workset.WorkSet()
        wset.metadata["creator"] = "qostool"
        wset.metadata["file_name"] = ws_filename

        self.opened_munin_worksets[wset_key] = wset
        return wset

    def get_possible_services(self, vserver):
        # look for possible services for this vserver
        possible_services = []

        for service in self.config.services.values():
            if vserver in service.zxtm_vservers:
                logging.debug("logfile for vserver %s can add hits to service %s", vserver, service.svc_id)
                possible_services.append(service)
        return possible_services
    

    def update_current_logfiles(self):
        for logfilename in self.state.current_logfiles.keys():
            try:
                logfile = self.state.current_logfiles[logfilename]            
                self.update_current_logfile(logfile, logfilename)
            except:
                logging.exception("update_current_logfiles: error processing current logfile [%s], dropping it", logfilename)
                logfile.closable = True


                        
    def update_current_logfile(self, logfile, logfilename):
        new_size = os.stat(self.config.zxtm_root + '/' + logfilename)[stat.ST_SIZE]
        prev_size = logfile.size
        if (new_size == 0) or (new_size == prev_size):
            logging.debug("SyncEngine: no new data in current logfile [%s]", logfilename)
            
            if logfile.time_period < self.current_time_period:
                logging.debug("SyncEngine: logfile [%s] is done, marking as closable", logfilename)
                logfile.closable = True
            return

        logging.debug("SyncEngine: current logfile [%s] has new data, skipping %d", logfilename, prev_size)

        
        mmap_file = util.open_mmap(self.config.zxtm_root + '/' + logfilename)
        mmap_file.seek(prev_size)

        # look for possible services for this vserver
        possible_services = self.get_possible_services(logfile.zxtm_vserver)

        while 1:
            line = mmap_file.readline()
            if not line:
                break

            duration, host, url, node_name, http_code = zxtm.parse_zxtm_log_line(line)
            svc = self.find_svc_for_host(possible_services, host)
            if svc is None:
                continue

            app = self.find_app_for_url(svc, url)
            ws = self.get_workset(logfile.time_period, svc.svc_id, app)

            # should we ignore this hit ?
            if svc.ignore_re.search(url) is not None:
                ws.ignore_hit(url, duration, node_name, http_code)
            else:
                clean_url = workset.cleanup_url(url, svc.keep_params_re)
                ws.hit(clean_url, duration, node_name, http_code)
                if (app in svc.munin_apps):
                    self.get_munin_workset(svc.svc_id, app).hit(clean_url, duration, node_name, http_code)

        logfile.size = new_size

    def find_svc_for_host(self, possible_services, host):
        for svc in possible_services:
            if svc.zxtm_host_re.search(host):
                return svc

    def find_app_for_url(self, svc, url):
        m = svc.apps_re.search(url)
        if m is not None:
            return m.group(1)    
        return "other"
                
    def save_opened_worksets(self):
        for ws in self.opened_worksets.values():
            fname = self.config.root + "/data/" + ws.metadata["file_name"]
            self.workset_manager.save(ws, fname)
        self.opened_worksets = {}

    def save_or_reset_munin_worksets(self):
        for ws in self.opened_munin_worksets.values():
            fname = self.config.root + "/munin/" + ws.metadata["file_name"]
            self.workset_manager.save(ws, fname)
            try:
                os.unlink(fname + ".read")
            except:
                pass
        self.opened_munin_worksets = {}
        # now we look for old workspaces to reset
        for service in self.config.services.values():
            for app in service.munin_apps:
                fname = self.config.root + "/munin/" + generate_munin_workset_file_name(service.svc_id, app)
                if os.path.isfile(fname) and os.path.isfile(fname + ".read"):
                    try:
                        os.unlink(fname)
                        os.unlink(fname + ".read")
                    except:
                        pass




    def save_state(self):
        state_file_name = self.config.root + "/state/sync.state"
        logging.debug("Saving state in %s", state_file_name)
        util.makedirs_for_file(state_file_name)
        outfile = open(state_file_name, "wb")
        cPickle.dump(self.state, outfile)
        outfile.close()        

    def close_logfiles(self):
        new_current_logfiles = {}
        for logfilename in self.state.current_logfiles.keys():
            logfile = self.state.current_logfiles[logfilename]
            if not logfile.closable:
                new_current_logfiles[logfilename] = logfile
            else:
                logging.debug("Closing logfile [%s]", logfilename)
        self.state.current_logfiles = new_current_logfiles
            

    def sync(self):
        self.load_state()
        self.handle_new_logfiles()
        self.update_current_logfiles()
        self.close_logfiles()
        self.save_opened_worksets()
        self.save_or_reset_munin_worksets()
        self.save_state()

