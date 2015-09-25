#!/usr/bin/env python
#
# Copyright (c) 2015 Intel Innovation and Research Ireland Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from wsgiref.simple_server import make_server
from pymongo import MongoClient
import logging
import json
import threading
import sys
from api import api
import api.create_providers_credentials as provider_details
from api import templates
from api import rulesengine
import api.create_monitoring_records as monitoring_details

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename='logs/slaaas.log',
                    filemode='w')

LOG = logging.getLogger(__name__)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
# add the handlers to the logger
LOG.addHandler(ch)
#logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

DB = MongoClient().sla.entities

def clean_violation_from_db():
    """
        Removes the violations and violation links from the Monfo DB so that the new OCCI SLA service is clean from old violation resources.
    """
    DB.remove({'kind':"/violation/"})
    DB.remove({'kind':"/violation_link/"})
    agreements = DB.find({'kind':"/agreement/"})
    for agreement in agreements:
        id = agreement['identifier']
        links = agreement['links']
        for link in links:
            violation_found = False
            if "violation" in link:
                agreement['links'].remove(link)
                violation_found = True
        if violation_found:
            DB.update({'_id': id}, agreement,
                      upsert=True)

def init_environment():
    """
        Initialise MCN Provider details
    """
    # Load Templates
    
    temps_dss = json.load(file("configs/template_definition_DSS.json"))
    templates.load_templates(temps_dss)

    #Add Providers login credentials
    provider_details.load_providers()

    #Add monitoring capabilities and Collectos's API
    monitoring_details.load_monitoring_capabilities()
    
    clean_violation_from_db()

if __name__ == "__main__":
    try:
            LOG.info("Starting OCCI server")
            init_environment()
            northbound_api = api.build()

            #start RulesEngine
            myRulesEngine = rulesengine.RulesEngine(northbound_api.registry) # Prepare intellect rules engine
            RE_thread = threading.Thread(target=myRulesEngine.start_engine, args=(15,))
            RE_thread.daemon = True
            RE_thread.start()

            httpd = make_server('0.0.0.0', 8888, northbound_api)
            httpd.serve_forever()
            #tmps = json.load(file("tests/sample_data/template_definition.json"))
            #templates.load_templates(tmps)
            
    except KeyboardInterrupt:
            print "Ctrl-c received! Killing OCCI Server..."
            

    
    



