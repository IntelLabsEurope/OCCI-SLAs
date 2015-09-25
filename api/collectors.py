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
    Collectors class for metric subscription and un-subscription
"""

import logging
import abc
import threading
import time
import json
import ConfigParser
import aggregator

LOG = logging.getLogger(__name__)
fh = logging.FileHandler('logs/collectors.log')
fh.setLevel(logging.INFO)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s -' +
                              ' %(levelname)s - %(message)s')
fh.setFormatter(formatter)
# add the handlers to the logger
LOG.addHandler(fh)

METRICS = json.load(file("configs/metrics.json"))


class Collector(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def subscribe_metric(self, device_id, metric, metric_value,
                         limiter_type, limiter_value):
        """
            This is an abstract method for subscribing a metric
            to the collector.
            metric: the name of the metric to monitor
            metric_value: the threshold value of the metric to monitor
            device_id: the identifier of the resource on which the metric
            will be monitored
            limiter_type: the type of violation monitoring. Can be max,
             min, marginal or enum
            limiter value: if the type of monitoring is marginal, this value
            gives the percentage of the accepted marginal variation.
            It returns True is the subscription is successful or False if there
             is some failure.
        """
        return

    @abc.abstractmethod
    def unsubscribe_metric(self, device_id, metric):
        """
            This is an abstract method for un-subscribing a metric from a
            resource (device_id).
        """

    @abc.abstractmethod
    def pull_metric(self, device_id, metric):
        """
            This is an abstract method for pulling a metric value from a
            resource (device_id).
            It returns the value of the metric.
        """
        return

    def metric_violated(self, metric_name, slo_metric_value,
                        metric_value, limiter_type, margin_value):
        """
           Check if metric is violated based on the template format
        """

        slo_metric_value = self.format_metric_value(metric_name,
                                                    slo_metric_value)
        metric_value = self.format_metric_value(metric_name, metric_value)

        if limiter_type == 'margin':
            margin_percentage = float(margin_value) / 100.0
            low_margin = slo_metric_value - \
                         slo_metric_value * margin_percentage
            high_margin = slo_metric_value + \
                          slo_metric_value * margin_percentage

            if metric_value < low_margin or metric_value > high_margin:
                LOG.debug("Violation on metric: " + metric_name)
                return True
        elif limiter_type == 'max':
            if metric_value > slo_metric_value:
                LOG.debug("Violation on metric: " + metric_name)
                LOG.debug("{} > than {}"
                          .format(metric_value, slo_metric_value))
                return True
        elif limiter_type == 'min':
            if metric_value < slo_metric_value:
                LOG.debug("Violation on metric: " + metric_name)
                LOG.debug("{} < than {}"
                          .format(metric_value, slo_metric_value))
                return True
        elif limiter_type == 'enum':
            if metric_value not in slo_metric_value:
                LOG.debug("Violation on metric: " + metric_name)
                return True
        else:
            LOG.error("Metric %s could not be evaluated" % metric_name)
            return False

    def format_metric_value(self, metric_name, metric_value):
        """
            Formats the metric value based on the type
            defined in the metrics.json
        """

        if metric_name in METRICS:
            if METRICS[metric_name]['value'] == 'integer':
                metric_value = int(metric_value)
            elif METRICS[metric_name]['value'] == 'real':
                metric_value = float(metric_value)
            elif METRICS[metric_name]['value'] == 'string':
                metric_value = str(metric_value)

            return metric_value

        else:
            LOG.error('Metric {} not found in METRICS.json'
                      .format(metric_name))
            raise AttributeError


class DummyCollector(Collector):
    """
    Replace this class with the implementation of a collector.
    """

    _subscriptions = {}

    def __init__(self):

    def subscribe_metric(self, device_id, metric, slo_value,
                         limiter_type, margin_value):
        """
            Public Subscription method for a metric
        """

        try:
            subscription_thread = threading. \
                Thread(target=self.__metric_subscription,
                       args=(device_id, metric, slo_value, limiter_type,
                             margin_value,))

            DummyCollector._subscriptions[device_id + "#" + metric] = \
                subscription_thread

            subscription_thread.daemon = True
            subscription_thread.start()

            return True
        except Exception:
            LOG.error('Subscription of {} on {} failed.'
                      .format(metric, device_id))
            return False

    def unsubscribe_metric(self, device_id, metric):
        """
            Public metric un-subscribe method.
        """

        LOG.debug('Un-subscribing metric {} on device {}.'
                  .format(metric, device_id))

        try:
            subs_thread = DummyCollector._subscriptions[device_id +
                                                       "#" + metric]
            del DummyCollector._subscriptions[device_id + "#" + metric]
            subs_thread.join()
            return True

        except Exception:
            LOG.error('Un-subscription of {} on {} failed.'
                      .format(metric, device_id))
            return False

    def __metric_subscription(self, device_id, metric, slo_value,
                              limiter_type, margin_value):
        """
            Private method for implementing the thread loop
        """

        while device_id + "#" + metric in DummyCollector._subscriptions:
            LOG.debug('Checking {}#{}'.format(device_id, metric))
            value = self.pull_metric(device_id, metric)
            if self.metric_violated(metric, slo_value, value,
                                    limiter_type, margin_value):
                gator = aggregator.Aggregator()
                gator.notification_event(device_id, metric, value)
            time.sleep(15)

    def pull_metric(self, device_id, metric_name):
        """
            Pull metric upon request.
        """

        # Initialise monitoring server access
        
	# Retrieve metric
	pass
