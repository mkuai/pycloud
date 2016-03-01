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

import dynamic_dns
import os
import sys

SVMS_ZONE_NAME = 'svm.cloudlet.local.'
CLOUDLET_HOST_NAME = 'cloudlet'

# Internal file path, relative to data folder.
KEY_FILE_PATH = 'dns/Ksvm.cloudlet.local.private'

#################################################################################################################
# Loads the key value from a TSIG privat key file.
#################################################################################################################
def load_tsig_key(key_path):
    key_value = None
    with open(key_path, "r") as key_file:
        # Find the key in the formatted key file, it is the text after a line starting with "Key: "
        data = key_file.read()
        lines = data.splitlines()
        for line in lines:
            parts = line.split(': ')
            if len(parts) > 1 and parts[0] == 'Key':
                key_value = parts[1]
                break

    return key_value

#################################################################################################################
# Object used to manage the cloudlet DNS server.
#################################################################################################################
class CloudletDNS(object):

    #################################################################################################################
    # Constructor.
    #################################################################################################################
    def __init__(self, root_data_folder):
        full_path = os.path.join(os.path.abspath(root_data_folder), KEY_FILE_PATH)
        self.key = load_tsig_key(full_path)

    #################################################################################################################
    # Registers an SVM.
    #################################################################################################################
    def register_svm(self, svm_fqdn, ip_address=None):
        # Depending on networking mode, we will need to register an explicit A record with an IP, or a cname to cloudlet.
        if ip_address:
            record_value = ip_address
            record_type = 'A'
        else:
            record_value = CLOUDLET_HOST_NAME
            record_type = 'CNAME'

        if not self.key:
            print "Can't register SVM: TSIG key not loaded."
            return

        dynamic_dns.add_dns_record(SVMS_ZONE_NAME, self.key, svm_fqdn, record_value, record_type=record_type)

    #################################################################################################################
    # Unregisters an SVM.
    #################################################################################################################
    def unregister_svm(self, svm_fqdn):
        if not self.key:
            print "Can't unregister SVM: TSIG key not loaded."
            return

        dynamic_dns.remove_dns_record(SVMS_ZONE_NAME, self.key, svm_fqdn)

#################################################################################################################
# Main behavior is to load a TSIG file and print its contents.
#################################################################################################################
if __name__ == '__main__':
    key = load_tsig_key(sys.argv[1])
    print key
