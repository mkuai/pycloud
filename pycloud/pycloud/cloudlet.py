# KVM-based Discoverable Cloudlet (KD-Cloudlet) 
# Copyright (c) 2015 Carnegie Mellon University.
# All Rights Reserved.
# 
# THIS SOFTWARE IS PROVIDED "AS IS," WITH NO WARRANTIES WHATSOEVER. CARNEGIE MELLON UNIVERSITY EXPRESSLY DISCLAIMS TO THE FULLEST EXTENT PERMITTEDBY LAW ALL EXPRESS, IMPLIED, AND STATUTORY WARRANTIES, INCLUDING, WITHOUT LIMITATION, THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT OF PROPRIETARY RIGHTS.
# 
# Released under a modified BSD license, please see license.txt for full terms.
# DM-0002138
# 
# KD-Cloudlet includes and/or makes use of the following Third-Party Software subject to their own licenses:
# MiniMongo
# Copyright (c) 2010-2014, Steve Lacy 
# All rights reserved. Released under BSD license.
# https://github.com/MiniMongo/minimongo/blob/master/LICENSE
# 
# Bootstrap
# Copyright (c) 2011-2015 Twitter, Inc.
# Released under the MIT License
# https://github.com/twbs/bootstrap/blob/master/LICENSE
# 
# jQuery JavaScript Library v1.11.0
# http://jquery.com/
# Includes Sizzle.js
# http://sizzlejs.com/
# Copyright 2005, 2014 jQuery Foundation, Inc. and other contributors
# Released under the MIT license
# http://jquery.org/license

__author__ = 'jdroot'

from pymongo import Connection
from pymongo.errors import ConnectionFailure
import psutil
import os
import shutil
from pycloud.pycloud.utils import portmanager
from pycloud.pycloud.vm.vmutils import destroy_all_vms
import pycloud.pycloud.mongo.model as model
import sys

# Singleton object to maintain intra- and inter-app variables.
_g_singletonCloudlet = None

################################################################################################################
# Creates the Cloudlet singleton, or gets an instance of it if it had been already created.
################################################################################################################
def get_cloudlet_instance(config=None):
    # Only create it if we don't have a reference already.
    global _g_singletonCloudlet
    if not _g_singletonCloudlet:
        print 'Creating Cloudlet singleton.'
        _g_singletonCloudlet = Cloudlet(config)

    return _g_singletonCloudlet

################################################################################################################
# Singleton that will contain common resources: config values, db connections, common managers.
################################################################################################################
class Cloudlet(object):

    ################################################################################################################
    # Constructor, should be called only once, independent on how many apps there are.
    ################################################################################################################    
    def __init__(self, config, *args, **kwargs):

        # Data folder
        self.data_folder = config['pycloud.data_folder']

        # Detect the app we are running in depending on the config params in the file.
        app = 'api' if 'pycloud.api.encrypted' in config else 'manager'

        # Write output to log file.
        sys.stdout = Tee(os.path.join(self.data_folder, 'pycloud-' + app + '.log'), 'w')

        print 'Loading cloudlet configuration...'

        # DB information.
        host = config['pycloud.mongo.host']
        port = int(config['pycloud.mongo.port'])
        dbName = config['pycloud.mongo.db']

        try:
            self.conn = Connection(host, port)
        except ConnectionFailure as error:
            print error
            raise Exception('Unable to connect to MongoDB')

        self.db = self.conn[dbName]

        # Get information about folders to be used.
        self.svmCache = os.path.join(self.data_folder, 'svmcache/')
        self.service_cache = os.path.join(self.data_folder, 'svmcache/')
        self.svmInstancesFolder = os.path.join(self.data_folder, 'temp/instances/')
        self.appFolder = os.path.join(self.data_folder, 'apks/')
        
        # Load the templates to be used when creating VMs.
        self.newVmFolder = os.path.join(self.data_folder, 'temp/servicevm/')
        self.newVmXml = os.path.join(config['pycloud.servicevm.xml_template'], 'vm_template.xml')

        # Export
        self.export_path = os.path.join(self.data_folder, 'temp/export')

        # Network params.
        self.network_bridge_enabled = config['pycloud.network.bridge_enabled'].upper() in ['T', 'TRUE', 'Y', 'YES']
        self.network_adapter = config['pycloud.network.adapter']

        # API port of remote APIs, needed for migration.
        self.api_port = config['pycloud.remote_api.port'] if 'pycloud.remote_api.port' in config else 0

        # Auth and pairing.
        self.auth_enabled = config['pycloud.auth.enabled'] if 'pycloud.auth.enabled' in config else 'false'
        self.auth_controller = config['pycloud.auth_controller'] if 'pycloud.auth_controller' in config else None
        self.credentials_type = config['pycloud.credentials_type'] if 'pycloud.credentials_type' in config else ''
        self.ssid = config['pycloud.pairing.ssid'] if 'pycloud.pairing.ssid' in config else ''

        # RADIUS.
        self.radius_users_file = config['pycloud.radius.users_file'] if 'pycloud.radius.users_file' in config else None
        self.radius_certs_folder = config['pycloud.radius.certs_folder'] if 'pycloud.radius.certs_folder' in config else None
        self.radius_eap_conf_file = config['pycloud.radius.eap_conf_file'] if 'pycloud.radius.eap_conf_file' in config else None

        # Load version information.
        basse_folder = os.path.dirname(os.path.realpath(__file__))
        self.version = ''
        with open(os.path.join(basse_folder, '../../', 'VERSION')) as version_file:
            self.version = version_file.readline()
            print 'App version: {}'.format(self.version)

        print 'cloudlet created.'

    @staticmethod
    def system_information():
        return Cloudlet_Metadata()

    def cleanup_system(self):
        destroy_all_vms()
        self._clean_temp_folder(self.svmInstancesFolder)
        self._clean_temp_folder(self.newVmFolder)
        self._remove_service_vms()
        portmanager.PortManager.clearPorts()
        if not os.path.exists(self.export_path):
            os.makedirs(self.export_path)
        if not os.path.exists(self.appFolder):
            os.makedirs(self.appFolder)

    def _clean_temp_folder(self, folder):
        print 'Cleaning up \'%s\'' % folder
        if os.path.exists(folder):
            print '\tDeleting all files in \'%s\'' % folder
            shutil.rmtree(folder)
        if not os.path.exists(folder):
            print '\tMaking folder \'%s\'' % folder
            os.makedirs(folder)
        print 'Done cleaning up \'%s\'' % folder

    def _remove_service_vms(self):
        from pycloud.pycloud.model import ServiceVM
        ServiceVM._collection.drop()


class Cpu_Info(model.AttrDict):

    def __init__(self):
        self.max_cores = psutil.cpu_count()
        self.usage = psutil.cpu_percent(interval=0.1)

        cpu_info = cpuinfo()
        self.speed = cpu_info['cpu MHz']
        self.cache = int(cpu_info['cache size'].split()[0])    # In KBs, per core.

class Memory_Info(model.AttrDict):

    def __init__(self):
        mem = psutil.virtual_memory()
        self.max_memory = mem.total
        self.free_memory = mem.free


class Cloudlet_Metadata(model.AttrDict):

    def __init__(self):
        self.memory_info = Memory_Info()
        self.cpu_info = Cpu_Info()


class Tee(object):

    def __init__(self, name, mode):
        self.file = open(name, mode)
        self.stdout = sys.stdout

    def __del__(self):
        self.file.close()

    def write(self, data):
        self.file.write(data)
        self.stdout.write(data)


from collections import OrderedDict

##########################################################################################
# Returns info about the first processor. Assumes if multiprocessor, all cores are equal.
##########################################################################################
def cpuinfo():
    procinfo = OrderedDict()

    with open('/proc/cpuinfo') as f:
        for line in f:
            if not line.strip():
                # End of one processor
                break
            else:
                if len(line.split(':')) == 2:
                    procinfo[line.split(':')[0].strip()] = line.split(':')[1].strip()
                else:
                    procinfo[line.split(':')[0].strip()] = ''

    return procinfo
