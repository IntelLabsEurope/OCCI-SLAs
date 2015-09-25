#!/usr/bin/env python
#
# Copyright (c) 2015 Intel Innovation and Research Ireland Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
    Rules Engine class for the SLAaaS framework
"""
import logging
from pymongo import MongoClient
import time
from intellect.Intellect import Intellect
from rulesenginehelper import RulesEngineHelper
import aggregator
import occi_sla
from occi import core_model
from utils import build_attr

LOG = logging.getLogger(__name__)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - ' +
                              '%(levelname)s - %(message)s')
ch.setFormatter(formatter)
# add the handlers to the logger
LOG.addHandler(ch)

DB = MongoClient().sla.policies


class RulesEngine(Intellect):
    """
         Rules Engine class for the OCCI SLAaaS.
         It inherits Intellect framework.
    """

    _registry = None
    _agreements_under_reasoning = []

    def __init__(self, registry=None, logger=None):
        self.active_agreements = {}
        self.active_policies = {}
        self.subscribed_devices = {}
        self.logger = logger or logging.getLogger(__name__)
        Intellect.__init__(self)
        if registry:
            RulesEngine._registry = registry
            DB.remove({})

    def start_engine(self, refresh_period):
        """
            Method for stating the Rules Engine.
            It gets the valid agreements from the registry and triggers the
            parsing. It takes as input the time interval of the loop.
        """
        LOG.info(">>>>>>>>>>>>>> OCCI SLAaaS Rules Engine started! "
                 "<<<<<<<<<<<<<<<<<")

        loop_status = True
        while loop_status:

            valid_agreements = self.__get_valid_agreements()

            agreement_keys = self.__parse_valid_agreements(valid_agreements)

            # REMOVE OLD POLICIES THAT HAVE EXPIRED FROM CACHE AND FROM DB
            expired_policies = []
            if len(self.active_policies.keys()) > len(agreement_keys):
                expired_policies = list(set(self.active_policies.keys()) -
                                        set(agreement_keys))

            for key in expired_policies:
                # Check if agreement is under reasoning
                # Do not remove agreement until the reasoning is complete.
                if key not in RulesEngine._agreements_under_reasoning:

                    LOG.info("Removing Agreement and policy for "
                             "Agreement ID: " + key)

                    if key in RulesEngine._registry.resources.keys():
                        # Get Agreement Entity
                        agreement = RulesEngine._registry.resources[key]
                        # agreement = self.registry.get_resource(key, None)

                        # Change Terms state to "undefined"
                        terms = self.__get_slo_terms(agreement.attributes)
                        for term in terms:
                            self.update_term(key, term + ".term.state",
                                             "undefined")

                            # Unsubscribe every term
                            metricsinfos = DB.find({'agreement_id': key},
                                                   {'_id': 0, 'terms': 1})
                            mtrcs = metricsinfos[0]['terms'][term]
                            aggrator = aggregator.Aggregator()
                            if len(self.subscribed_devices[key]) > 0:
                                device_ids = self.subscribed_devices[key]
                                aggrator.unsubscribe_term(term, key,
                                                          mtrcs,
                                                          device_ids)

                    DB.remove({'agreement_id': key})

                    del self.active_policies[key]

            if self.active_policies.keys():
                LOG.debug('Active agreements and policies are:')
                for key in self.active_policies.keys():
                    LOG.debug(key)

            if refresh_period != 0:
                time.sleep(refresh_period)
            else:
                loop_status = False

    def reason_agreement(self, agreement_id, metrics, device_id):
        """
            Public method for reasoning an agreement over a set of
            monitored metrics.
        """
        if agreement_id not in RulesEngine._agreements_under_reasoning:
            LOG.info("Reasoning agreement: {}".format(agreement_id))
            RulesEngine._agreements_under_reasoning.append(agreement_id)

            agreement_collection = self.__get_policy_collection(agreement_id)

            if agreement_collection:
                slo_terms = agreement_collection[0]['terms']
                policy = agreement_collection[0]['policy']

                ruhelper = RulesEngineHelper(agreement_id, slo_terms,
                                             metrics, device_id)
                try:
                    self.learn(ruhelper)
                    self.learn(policy)
                    self.reason()
                    LOG.info('Agreement reasoning completed.')
                    RulesEngine._agreements_under_reasoning\
                        .remove(agreement_id)
                    self.forget_all()
                except TypeError:
                    raise TypeError('Intellect framework failed.')

            else:
                raise AttributeError('Policy record for {} not found in DB.'
                                     .format(agreement_id))
        else:
            LOG.warn('Agreement {} already under reasoning.'
                     .format(agreement_id))

    def __parse_valid_agreements(self, valid_agreements):
        """
            Method for parsing the active agreements and triggering
            the policy generation and Aggregator subscription.
        """

        agreement_keys = []

        for agreement in valid_agreements:
            links = agreement.links
            agreement_id = agreement.identifier

            if len(links) > 0:

                # parse links
                rtrn_values = self.__get_devices(links, valid_agreements)
                device_ids = rtrn_values['devices']
                linked_agreements = rtrn_values['linked_agreements']
                skip_agreement = rtrn_values['skip_agreement_flag']

                # break loop if agreement link towards an agreement is invalid.
                if skip_agreement:
                    continue

                agreement_keys.append(agreement_id)

                if agreement_id not in self.active_policies.keys():
                    LOG.info("New valid Agreement found: " + agreement_id)

                    self.__subscribe_agreement_terms(agreement,
                                                     device_ids,
                                                     linked_agreements)
                else:
                    LOG.debug("Agreement %s already exists in active list."
                              % agreement_id)
                    # check if resources/devices have changed
                    current_links = self.active_agreements[agreement_id].links
                    current_devices = self.__get_devices(current_links,
                                                         valid_agreements)
                    removed_devices = []
                    for device in self.subscribed_devices[agreement_id]:
                        if device not in current_devices['devices']:
                            LOG.info('Device {} removed from agreement {}'
                                     .format(device, agreement_id))
                            # unsubscribe device
                            removed_devices.append(device)
                            self.subscribed_devices[agreement_id]\
                                .remove(device)

                    if len(removed_devices) > 0:
                        terms = self.__get_slo_terms(agreement.attributes)
                        policy_record = DB.find({'agreement_id': agreement_id})
                        for term in terms:
                            # Unsubscribe every term
                            mtrcs = policy_record[0]['terms'][term]
                            aggrator = aggregator.Aggregator()
                            aggrator.unsubscribe_term(term, agreement_id,
                                                      mtrcs,
                                                      removed_devices)
                        temp = policy_record[0]
                        for device in removed_devices:
                            temp['devices'].remove(device)
                        DB.update({'agreement_id': agreement_id}, temp,
                                  upsert=True)
                    new_devices = []
                    for device in current_devices['devices']:
                        if device not in \
                                self.subscribed_devices[agreement_id]:
                            LOG.info('New device {} for agreement {}'
                                     .format(device, agreement_id))
                            # create the new devices list used later
                            new_devices.append(device)
                            self.subscribed_devices[agreement_id]\
                                .append(device)
                    if len(new_devices) > 0:
                        self.__subscribe_agreement_terms(agreement,
                                                         new_devices,
                                                         linked_agreements)
            else:
                LOG.info('Valid agreement {} does not have linked resources.'
                         .format(agreement_id))
        return agreement_keys

    def __get_devices(self, links, valid_agreements):
        '''
        Returns the list of valid devices based on the links of an agreement,
        list of linked SLA agreements and if there is a fault in the linkage
        of SLAs it returns a flag to break the loop.
        '''
        skip_agreement = False
        device_ids = []
        linked_agreements = []

        for link in links:
            if not isinstance(link, core_model.Link):
                if link in RulesEngine._registry.resources.keys():
                    link = RulesEngine._registry.resources[link]
                else:
                    LOG.error("Link {} not in registry.".format(link))
            if link.kind == occi_sla.AGREEMENT_LINK:
                temp_target = link.target
                if isinstance(link.target, core_model.Resource) and \
                   link.target.kind == occi_sla.AGREEMENT:
                    LOG.debug('SLA federation scenario triggered')
                    temp_res = RulesEngine._registry.resources
                    if temp_res[temp_target.identifier] \
                            not in valid_agreements:
                        # check if is valid
                        LOG.warn('Linked agreement {} not valid!'
                                 .format(temp_target.identifier))
                        # if its not valid break for loop
                        skip_agreement = True
                        break
                    else:
                        linked_agreements. \
                            append(temp_target.identifier)
                else:
                    if isinstance(link.target, core_model.Resource):
                        device_ids.append(link.target.identifier)
                    else:
                        device_ids.append(link.target)

        return {'devices': device_ids, 'linked_agreements': linked_agreements,
                'skip_agreement_flag': skip_agreement}

    def __subscribe_term(self, agreement_id, attributes,
                         device_ids, template, term):
        '''
            Parse term's attributes and subscribe the term of an agreement
            to the Aggregator.
        '''

        metrics = {}

        term_remedy = attributes[build_attr(term, 'term.remedy')]
        attributes_keys = attributes.keys()
        attributes_keys.remove(build_attr(term, 'term.remedy'))
        for key in attributes_keys:
            if build_attr(template, term) in key:
                mixed_metrics = key.replace(build_attr(template,
                                                       term) +
                                            '.', '')
                if len(mixed_metrics.split('.')) == 1:
                    metrics[mixed_metrics] = {
                        'value': attributes.get(key),
                        'limiter_type': attributes[
                            build_attr(template, term,
                                       mixed_metrics,
                                       'limiter_type')
                        ]
                    }

                    if attributes[build_attr(
                            template, term, mixed_metrics, 'limiter_type')
                    ] == 'margin':
                        temp1 = attributes[
                            build_attr(template, term,
                                       mixed_metrics, 'limiter_type')
                        ]
                        temp2 = attributes[build_attr(
                            template, term, mixed_metrics, 'limiter_value')
                        ]

                        metrics[mixed_metrics] = {
                            'value': attributes.get(key),
                            'limiter_type': temp1,
                            'limiter_value': temp2
                        }

        if metrics:
            # Subscribe term to Aggregator
            aggrator = aggregator.Aggregator()
            aggrator.subscribe_term(term, agreement_id,
                                    {'remedy': term_remedy,
                                     'metrics': metrics},
                                    device_ids)

            return {'remedy': term_remedy, 'metrics': metrics}
        else:
            return {}

    def __subscribe_agreement_terms(self, agreement,
                                    device_ids, linked_agreements):
        '''
            Subscribe all the SLO terms of an agreement to the devices.
        '''
        attributes = agreement.attributes
        agreement_id = agreement.identifier

        # FIND WHICH ATTRIBUTES/METRICS ARE SLOs
        terms = self.__get_slo_terms(attributes)
        # Change Terms state to "fulfilled"
        for term in terms:
            self.update_term(agreement_id, term + ".term.state",
                             "fulfilled")

        mixins = agreement.mixins
        templates = []

        for mixin in mixins:
            if occi_sla.AGREEMENT_TEMPLATE in mixin.related:
                templates.append(mixin.term)

        terms_metrics = {}

        for template in templates:
            for term in terms:
                term_mtrc = self.__subscribe_term(agreement_id,
                                                  attributes,
                                                  device_ids,
                                                  template,
                                                  term)
                if term_mtrc:
                    terms_metrics[term] = term_mtrc

        if agreement_id not in self.active_policies.keys():
            self.active_policies[agreement_id] = \
                self.__construct_policy(
                    agreement_id, terms,
                    terms_metrics)
            self.subscribed_devices[agreement_id] = device_ids
            self.active_agreements[agreement_id] = agreement

            # Insert to Policies DB
            policy = {'agreement_id': agreement_id, 'policy':
                      str(self.active_policies[agreement_id]),
                      'terms': terms_metrics,
                      'devices': device_ids,
                      'linked_agreements': linked_agreements}
            DB.update({'agreement_id': agreement_id}, policy,
                      upsert=True)

        # update policy record with new devices
        else:
            policy_record = DB.find({'agreement_id': agreement_id})
            temp = policy_record[0]['devices']
            for device in device_ids:
                temp.append(device)
            policy = {'agreement_id': agreement_id, 'policy':
                      str(self.active_policies[agreement_id]),
                      'terms': terms_metrics,
                      'devices': temp,
                      'linked_agreements': linked_agreements}
            DB.update({'agreement_id': agreement_id}, policy,
                      upsert=True)

    def __get_slo_terms(self, attributes):
        """
            Method for getting the SLO terms from an agreements.
        """

        terms = []
        for key in attributes.keys():
            if ".term.type" in key and attributes[key] == "SLO-TERM":
                terms.append(key.replace(".term.type", ""))

        return terms

    def __get_valid_agreements(self):
        """
            Method for getting the valid agreements from the Mongo DB. They are
             valid when they are accepted and the current date is within
             the valid period.
        """

        resources = RulesEngine._registry.get_active_agreement_resources()
        # if len(resources) > 0:
        #    LOG.debug("Total number of valid agreements: %d "
        #              % (len(resources)))
        return resources

    def __get_policy_collection(self, agreement_id):
        """
            Method for getting the active policies stored in the Mongo DB.
        """
        agreement_collection = DB.find({'agreement_id': agreement_id},
                                       {'_id': 0})
        if agreement_collection.count() > 0:
            LOG.debug(">>>>>>>>>>>> called __getPolicyCollection method. %d "
                      "policies found" % (agreement_collection.count()))
            return agreement_collection
        else:
            raise AttributeError('Policy record for {} not found in DB.'
                                 .format(agreement_id))

    def __construct_policy(self, agreement_id, terms, metrics):
        """
            Method for constructing a String with the definition of the policy
             rules following the syntax defined by Intellect.
        """

        imports = 'import logging\n' \
                  'from api.rulesenginehelper import RulesEngineHelper\n'
        new_line = '\n'
        rules = ''

        for term in terms:
            rule_title = 'rule "' + term + ' for ' + agreement_id + '":\n'

            when = ''
            then = ''
            action = ''

            when = '        when:\n'
            condition = '                $RulesEngineHelper := RulesEngine' \
                        'Helper(agreement_term_violated("' + agreement_id + \
                        '","' + term + '"))\n'
            then = '        then:\n'
            action = '                log("A violation is fired for :' + \
                     agreement_id + ' - ' + term + '")\n'
            action += '                $RulesEngineHelper.' \
                      'agreement_term_apply_remedy("' + agreement_id + '","' \
                      + term + '")\n'

            rules += rule_title + when + condition + then + action

        policy = imports + new_line + rules + new_line

        return policy

    def update_term(self, agreement_id, term, state):
        """
            It updates the terms of an agreement.
        """

        LOG.debug('Change term for {} to state {}'.format(term, state))

        res = RulesEngine._registry.get_resource(agreement_id, None)
        res.attributes[term] = state
        RulesEngine._registry.resources.__setitem__(agreement_id, res)
