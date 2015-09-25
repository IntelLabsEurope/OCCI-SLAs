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
    Aggregator class for term subscription and un-subscription
"""

import logging
import collectors
import rulesengine
from pymongo import MongoClient
import json

LOG = logging.getLogger(__name__)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
# create formatter and add it to the handlers
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - ' +
    '%(levelname)s - %(message)s'
)
ch.setFormatter(formatter)
# add the handlers to the logger
LOG.addHandler(ch)
METRICS = json.load(file("configs/metrics.json"))
DB = MongoClient().sla


class Aggregator(object):
    """
    The Aggregator class is an assistive class which collects the metrics of
    an agreement term and returns the values to the agreement helper, for
    validation..
    """

    def __init__(self, logger=None):
        """
        Aggregator initializer
        """
        self.logger = logger or logging.getLogger(__name__)

    def subscribe_term(self, term, agreement_id, metrics_info, device_ids):
        """
            Subscription method of an agreement term
        """
        
        if len(device_ids) == 0:
            LOG.error('No device ids given!')
            raise AttributeError('No device ids given!')
        else:
            for device in device_ids:
                LOG.info("Agreement: {} - SubscribeTerm called for term "
                         "{} on device {}.".
                          format(agreement_id, term, device))
                for metric_key, metric in metrics_info['metrics'].iteritems():
                    c_api = None
                    if metric_key not in METRICS:
                        LOG.error(
                            'Metric {} not found in METRICS.json'
                                .format(metric_key)
                        )
                        raise AttributeError()
                    try:
                        c_api = self.get_collector_class(device, metric_key)
                    except AttributeError as e:
                        LOG.error(
                            'Failed to get collector class for device {}.'
                                .format(device))
                        LOG.warn('Loading default collector')
                        c_api = 'DummyCollector'
                        # LOG.debug(e)
                        # raise AttributeError

                    if c_api:
                        LOG.debug(c_api)
                        try:
                            c_class = getattr(collectors, c_api)
                            LOG.debug('Collector is {} for metric {}'.format(
                                     c_class, metric_key))
                            collector = c_class()

                            margin_value = None
                            if 'limiter_value' in metric:
                                margin_value = metric['limiter_value']
                            collector.subscribe_metric(device,
                                                       metric_key,
                                                       metric['value'],
                                                       metric['limiter_type'],
                                                       margin_value)
                        except AttributeError:
                            LOG.error('Collector class {} missing'
                                      .format(c_api))
                            raise RuntimeWarning('Collector class {} missing'
                                                 .format(c_api))


    def notification_event(self, device_id, metric_name, metric_value):
        """
               A notification event carrying the metric from the monitoring infra.
        """

        # from device and metric get agreement_id
        db_records = DB.policies.find({'devices': device_id}, {'policy': 0})
        if db_records.count() > 0:
            for policy in db_records:
                metrics = []
                for term_key, term in policy['terms'].iteritems():
                    for metric in term['metrics']:
                        metrics.append(metric)

                if metric_name in metrics:
                    metrics.remove(metric_name)
                else:
                    LOG.error('Metric {} could not be found in policy record '
                              '{}.'.format(metric_name, policy['_id']))
                    raise AttributeError('Metric {} could not be found in the '
                                         'policy record {}.'
                                         .format(metric_name, policy['_id']))

                metric_values = {metric_name: metric_value}
                for metric in metrics:
                    try:
                        c_api = self.get_collector_class(device_id, metric)
                    except AttributeError as e:
                        LOG.error(
                            'Failed to get collector class for device {}.'
                                .format(device_id))
                        LOG.warn('Loading default collector')
                        c_api = 'DummyCollector'

                    if c_api:
                        try:
                            c_class = getattr(collectors, c_api)
                            collector = c_class()
                            metric_values[metric] = collector. \
                                pull_metric(device_id, metric)
                        except AttributeError:
                            LOG.error('Collector class {} missing'
                                      .format(c_api))
                            raise RuntimeWarning('Collector class {} missing'
                                                 .format(c_api))

                LOG.debug("agreement ID is {}.".format(policy['agreement_id']))
                LOG.debug(
                    "Metric(s) {} with value(s) {}.".format(
                        metric_values.keys(), metric_values.values()
                    )
                )

                
                myrulesengine = rulesengine.RulesEngine()
                myrulesengine.reason_agreement(policy['agreement_id'],
                                               metric_values, device_id)
        else:
            LOG.error(
                'Policy record for device {} and metric {} could not be '
                'found.'.format(device_id, metric_name)
            )
            raise AttributeError(
                'Policy record for device {} and metric {} '
                'could not be found.'.format(device_id, metric_name)
            )


    def get_collector_class(self, device_id, metric):
        """
                Method for returning the collector class for a metric and device
        """

        db_records = DB.devices.find(
            {'_id': device_id},
            {'_id': 0, 'monitoring': 1}
        )
        coll_class = None
        if db_records.count() == 0:
            LOG.error('No devices found in the DB for id: {}'
                      .format(device_id))
            raise AttributeError('No devices found in the DB for id: {}'
                                 .format(device_id))
        elif db_records.count() > 1:
            LOG.error('More than one records found in the DB for id: {}'
                      .format(device_id))
            raise AttributeError('More than one records found in the DB'
                                 ' for id: {}'.format(device_id))
        else:
            for mon_system in db_records[0]['monitoring']:
                monitoring = DB.monitoring.find({'name': mon_system})
                if monitoring.count() > 0:
                    mon_system = monitoring[0]
                    if metric in mon_system['metrics']:
                        coll_class = mon_system['api']
                else:
                    LOG.error('Monitoring api {} cannot be found in the '
                              'DB for the device {}.'.format(mon_system.
                                                             device_id))
                    raise AttributeError('Monitoring api {} cannot be found '
                                         'in the DB.'.format(mon_system))

        if not coll_class:
            LOG.error('Metric {} could not be found into the available '
                      'monitoring apis.'.format(metric))
            raise AttributeError('Metric {} could not be found into the '
                                 'available monitoring apis.'.format(metric))
        else:
            return coll_class


    def unsubscribe_term(self, term, agreement_id, metrics_info, device_ids):
        """
                Un-subscription method of an agreement term
         """

        if len(device_ids) == 0:
            LOG.error('No device ids given!')
            raise AttributeError('No device ids given!')
        else:
            for device in device_ids:
                LOG.info("Agreement: {} - Un-subscribeTerm called for "
                         "term {} on device {}.".
                          format(agreement_id, term, device))
                for metric_key, metric in metrics_info['metrics'].iteritems():
                    try:
                        c_api = self.get_collector_class(device, metric_key)
                    except AttributeError as e:
                        LOG.error(
                            'Failed to get collector class for device {}.'
                                .format(device))
                        LOG.warn('Loading default collector')
                        c_api = 'DummyCollector'

                    if c_api:
                        try:
                            c_class = getattr(collectors, c_api)
                            collector = c_class()

                            collector.unsubscribe_metric(device, metric_key)
                        except AttributeError:
                            LOG.error(
                                'Collector class {} missing'.format(c_api)
                            )
                            raise RuntimeWarning('Collector class {} missing'
                                                 .format(c_api))


    def pull_term(self, term, agreement_id, metrics_info, device_id):
        """
                Pulling the term's metrics from the appropriate collector.
        """

        metrics_values = {}

        for metric_key, metric in metrics_info.iteritems():
            c_api = None
            try:
                c_api = self.get_collector_class(device_id, metric_key)
            except AttributeError:
                LOG.error('Failed to get collector class for {}.'
                          .format(device_id))
                LOG.warn('Loading default collector')
                c_api = 'DummyCollector'

            if c_api:
                try:
                    c_class = getattr(collectors, c_api)
                    LOG.debug('Collector is {} for metric {}'.format(
                        c_class, metric_key))
                    collector = c_class()

                    metric_value = collector.pull_metric(device_id, metric_key)
                    metrics_values[metric_key] = metric_value

                except AttributeError:
                    LOG.error('Collector class {} missing'.format(c_api))
                    raise RuntimeWarning('Collector class {} missing'
                                         .format(c_api))
        return metrics_values
