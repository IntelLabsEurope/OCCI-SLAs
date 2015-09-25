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
"""
  Assistive class for Intellect policy enforcement and violation detection and reporting
"""

import logging
import json
from pymongo import MongoClient
import time
import uuid
import rulesengine
import aggregator
from api import occi_violation
from api import occi_sla
import arrow
from occi import core_model
import ConfigParser
import pika

LOG = logging.getLogger(__name__)
fh = logging.FileHandler('logs/evaluation.log')
fh.setLevel(logging.INFO)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s -' +
                              ' %(levelname)s - %(message)s')
fh.setFormatter(formatter)
# add the handlers to the logger
LOG.addHandler(fh)

METRICS = json.load(file("configs/metrics.json"))
DB = MongoClient().sla

config = ConfigParser.ConfigParser()
config.read('configs/rabbit.cfg')
RABBIT_MQ_HOST = config.get('rabbit', 'host')
RABBIT_QUEUE = config.get('rabbit', 'queue')
RABBIT_EXCHANGE = config.get('rabbit', 'exchange')
RABBIT_USERNAME = config.get('rabbit', 'username')
RABBIT_PASSWORD = config.get('rabbit', 'password')
RABBIT_VIRTUAL_HOST = config.get('rabbit', 'virtual_host')


class RulesEngineHelper(object):
    """
    The RulesEngine_Helper class is an assistive class which evaluates
    the terms and metrics of an agreement.
    """

    def __init__(self, agreement_id=None, slo_terms_metrics=None,
                 metrics=None, device_id=None):
        """
        RulesEngine_Helper initializer
        """

        LOG.info("SLA evaluation process initiated.")
        LOG.info("Agreement ID %s." % agreement_id)

        self._metrics = metrics
        self._slo_terms_metrics = slo_terms_metrics
        self._agreement_id = agreement_id
        self._violated_metrics = {}
        self._device_id = device_id

    @property
    def device_id(self):
        """
            Device id that triggered the notification violation
        """
        return self._device_id

    @device_id.setter
    def device_id(self, value):
        """
            Setter for list of device id
        """
        self._device_id = value

    @property
    def violated_metrics(self):
        """
            List of violated metrics
        """
        return self._violated_metrics

    @violated_metrics.setter
    def violated_metrics(self, value):
        """
            Setter for list of violated metrics
        """
        self._violated_metrics = value

    @property
    def slo_terms_metrics(self):
        """
            SLO terms metrics list
         """
        return self._slo_terms_metrics

    @slo_terms_metrics.setter
    def slo_terms_metrics(self, value):
        """
            SLO terms metrics list setter
        """
        self._slo_terms_metrics = value

    @property
    def metrics(self):
        """
            Monitored metrics list
        """
        return self._metrics

    @metrics.setter
    def metrics(self, value):
        """
            Monitored metrics list setter
        """
        self._metrics = value

    @property
    def agreement_id(self):
        """
            Agreement ID parameter
        """
        return self._agreement_id

    @agreement_id.setter
    def agreement_id(self, value):
        """
            Agreement ID parameter setter
        """
        self.agreement_id = value

    def agreement_term_violated(self, agreement_id, term):
        """
            Method for the evaluation of a term violation.
        """
        # LOG.debug("Inspect violation of agreement {} for term {}." \
        #          .format(agreement_id, term))

        self._violated_metrics = {}
        violation_flags = []
        limiter_value = None

        for slo_metric in self._slo_terms_metrics[term]['metrics']:
            term_mtrc = self._slo_terms_metrics[term]['metrics'][slo_metric]
            limiter = term_mtrc['limiter_type']
            if limiter == 'margin':
                limiter_value = term_mtrc['limiter_value']

            slo_metric_value = term_mtrc['value']
            metric_value = self._metrics[slo_metric]
            
            mtr_violated = self.__metric_violated(slo_metric,
                                   slo_metric_value, metric_value, limiter,
                                   limiter_value)
            violation_flags.append(mtr_violated)
            if mtr_violated:
                self._violated_metrics[slo_metric] = metric_value

        # if all metrics of the term are violated, the term is violated too
        if violation_flags.count(True) == len(violation_flags):
            LOG.warn("Violation of agreement {} detected for term {}."
                     .format(agreement_id, term))
            return True
        else:
            LOG.info("No violation detected for term {}.".format(term))
            return False

    def agreement_term_apply_remedy(self, agreement_id, term):
        """
            Method for the application of the remedy clause.
        """
        LOG.info("Enforcing remedy for agreement {} called for term {}."
                 .format(agreement_id, term))

        myrulesengine = rulesengine.RulesEngine()

        myrulesengine.update_term(
            agreement_id, term + ".term.state", "violated")

        remedy = self._slo_terms_metrics[term]['remedy']

        # ToDo: interact with RCBaaS for charging the remedy
        self.__publish_to_rcb_queue(agreement_id, term, '', '', self.device_id, 
                                    self._violated_metrics, self._slo_terms_metrics[term]['remedy'])

        extras = self.__get_extras(agreement_id)
        violation = self.__create_violation_resource(term, '', '', self.device_id, 
                                                     self._violated_metrics, remedy, extras)
        link = self.__create_violation_link(agreement_id, violation, extras)

        LOG.info('Wait for term to become valid.')
        aggrator = aggregator.Aggregator()
        term_slo_metrics = aggrator.pull_term(term, agreement_id,
                                              self._slo_terms_metrics[term]
                                              ['metrics'],
                                              self._device_id)

        for key, value in term_slo_metrics.iteritems():
            self._metrics[key] = value

        while self.agreement_term_violated(agreement_id, term):
            term_slo_metrics = aggrator.pull_term(term,
                                                  agreement_id,
                                                  self._slo_terms_metrics[term]
                                                  ['metrics'],
                                                  self._device_id)

            for key, value in term_slo_metrics.iteritems():
                self._metrics[key] = value
            time.sleep(15)
        LOG.info('SLO term {} became valid again.'.format(term))
        myrulesengine.update_term(
            agreement_id, term + ".term.state", "fulfilled")

        #self.__update_violation_end_time(violation, extras)
        # Deleting the violation resource while is no longer active
        self.__delete_violation(violation, extras)
        self.__delete_violation_link(agreement_id, violation, link, extras)

    def __publish_to_rcb_queue(self, agreement_id, term, metric_name, metric_value, device_id, 
                               violation_metrics, remedy):
        """
           Create an entry into the queue of the RCBaaS
        """

        now_iso = arrow.utcnow().isoformat()
        epoch_time = int(time.time())

        violation = {'agreement_id':agreement_id, 'timestamp':epoch_time, 'resource':device_id, 'term':term, 
                     'violation_metrics': json.dumps(violation_metrics), 'penalty':remedy}        

        credentials = pika.PlainCredentials(RABBIT_USERNAME, RABBIT_PASSWORD)
        parameters = pika.ConnectionParameters(host=RABBIT_MQ_HOST, port=5672, virtual_host=RABBIT_VIRTUAL_HOST, credentials=credentials)
        try:
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            #channel.queue_declare(queue=RABBIT_QUEUE)
            channel.basic_publish(exchange=RABBIT_EXCHANGE,
                              routing_key=RABBIT_QUEUE,
                              body=violation)
            connection.close()
        except:
            # LOG.error("Connection to RabbitMQ failed")
            pass

    def __create_violation_resource(self, term, metric_name, metric_value, device_id, 
                                    violation_metrics, remedy, extras):
        """
           Create an OCCI violation instance with the proper attribute values
        """
        LOG.debug('Violation instance created for metric {} on device {}'.format(metric_name, device_id))
        
        now_iso = arrow.utcnow().isoformat()
        id = '/violation/' + str(uuid.uuid4())
        res = core_model.Resource(id, occi_violation.VIOLATION, [])
        res.attributes = {'occi.violation.timestamp.start': now_iso,
                          'occi.violation.term': term,
                          'occi.violation.metrics': json.dumps(violation_metrics),
                          'occi.violation.device': device_id,
                          'occi.violation.remedy': remedy
                          }
        res.provider = extras["security"].items()[0][0]
        res.customer = extras["customer"]
        LOG.debug('Inserting resource with ID: {}'.format(id))
        myrulesengine = rulesengine.RulesEngine()
        myrulesengine._registry.resources.__setitem__(id, res)

	return res

    def __create_violation_link(self, agreement_id, violation, extras):
        """
           Create an OCCI violation link with the proper attribute values
        """
        LOG.debug('Violation instance created for agreement {}'.format(agreement_id))

        now_iso = arrow.utcnow().isoformat()
        id = '/violation_link/' + str(uuid.uuid4())
        myrulesengine = rulesengine.RulesEngine()
        agreement = myrulesengine._registry.get_resource(agreement_id, None)
        agreement.identifier = agreement_id

        res = core_model.Link(id, occi_violation.VIOLATION_LINK, [], agreement, violation)
        res.attributes = {'occi.core.source': agreement_id,
                          'occi.core.target': violation.identifier}

        res.provider = extras["security"].items()[0][0]
        res.customer = extras["customer"]
        res.source = agreement
        res.target = violation.identifier

        # Updating agreement resource with new link
        agreement.links.append(res)
        myrulesengine._registry.resources.__setitem__(agreement_id, agreement)

        LOG.debug('Inserting violation link with ID: {}'.format(id))
        myrulesengine._registry.resources.__setitem__(id, res)
        return res

    def __delete_violation_link(self, agreement_id, violation, violation_link, extras):
        """
            Remove the violation link resource from the registry and from the agreement resource.
        """
        myrulesengine = rulesengine.RulesEngine()
        myrulesengine._registry.delete_resource(violation_link.identifier, extras)

        agreement = myrulesengine._registry.get_resource(agreement_id, None)
        agreement.identifier = agreement_id
        if violation_link in agreement.links:
            agreement.links.remove(violation_link)

    def __update_violation_end_time(self, violation, extras):
        """
           Update an OCCI violation with the proper attribute values.
        """
        LOG.debug('Violation endtime updated for violation {}'.format(violation.identifier))

        now_iso = arrow.utcnow().isoformat()
        myrulesengine = rulesengine.RulesEngine()
        # Updating agreement resource with new link
        violation.attributes['occi.violation.timestamp.end'] = now_iso 
        myrulesengine._registry.resources.__setitem__(violation.identifier, violation)

    def __delete_violation(self, violation, extras):
        """
           Delete an OCCI violation when the violation is no longer active. 
        """
        LOG.debug('Deleting violation: {}.'.format(violation.identifier))

        myrulesengine = rulesengine.RulesEngine()
        myrulesengine._registry.delete_resource(violation.identifier, extras)

        
    def __get_extras(self, agreement_id):
        """
           Get extras infos for a certain agreement instance.
        """
        agreement_record = DB.entities.find({'_id': agreement_id})
        if agreement_record.count() == 0:
            LOG.error('Agreement {} not found in DB'.format(agreement_id))
        else:
            provider = agreement_record[0]['provider']
            customer = agreement_record[0]['customer']
            provider_rec = DB.providers.find({'username': provider})
            if provider_rec.count() == 0:
                LOG.error('Provider record for {} not found in DB'.format(provider))
            else:
                provider_pass = provider_rec[0]['password']
                extras = {"security": {provider: provider_pass}, "customer": customer}
                return extras

    def __metric_violated(self, metric_name, slo_metric_value,
                          metric_value, limiter_type, limiter_value):
        """
           Check if metric is violated based on the template format
        """

        if (metric_name in METRICS) and metric_value:
            if METRICS[metric_name]['value'] == 'integer':
                slo_metric_value = int(slo_metric_value)
                metric_value = int(metric_value)
            elif METRICS[metric_name]['value'] == 'real':
                slo_metric_value = float(slo_metric_value)
                metric_value = float(metric_value)
            elif METRICS[metric_name]['value'] == 'string':
                pass
            else:
                raise AttributeError
        else:
            return False

        if limiter_type == 'margin':
            margin_percent = float(limiter_value) / 100.0
            low_margin = slo_metric_value - slo_metric_value * margin_percent
            high_margin = slo_metric_value + slo_metric_value * margin_percent

            if metric_value < low_margin or metric_value > high_margin:
                LOG.debug("Violation on metric: " + metric_name)
                return True
        elif limiter_type == 'max':
            if metric_value > slo_metric_value:
                LOG.debug("Violation on metric: " + metric_name)
                LOG.debug("{} > than {}".format(metric_value,
                                                slo_metric_value))
                return True
        elif limiter_type == 'min':
            if metric_value < slo_metric_value:
                LOG.debug("Violation on metric: " + metric_name)
                LOG.debug("{} < than {}".format(metric_value,
                                                slo_metric_value))
                return True
        elif limiter_type == 'enum':
            if metric_value not in slo_metric_value:
                LOG.debug("Violation on metric: " + metric_name)
                return True
        else:
            LOG.warn("Metric %s could not be evaluated" % metric_name)
            return False
