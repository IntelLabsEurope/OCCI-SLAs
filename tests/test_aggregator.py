from api.aggregator import Aggregator
import logging
import unittest
from pymongo import MongoClient


LOG = logging.getLogger(__name__)
DB = MongoClient().sla
logging.basicConfig(level='DEBUG')


class AggregatorOperation(unittest.TestCase):
    def setUp(self):
        device1 = {"_id": "/compute/aaaaaa-aaaaaa",
                   "host": "testbed - X",
                   "monitoring": ["dummy_api"]}

        device2 = {"_id": "/compute/bbbbbb-bbbbbb",
                   "host": "testbed - X",
                   "monitoring": ["dummy-merlin"]}

        device3 = {"_id": "/compute/testing-device",
                   "host": "testbed - X",
                   "monitoring": ["dummy-merlin"]}

        policy1 = {"_id": "cccccc-bbbbbb-cccccc",
                  "agreement_id": "/agreement/dddddd-eeeeee",
                  "policy": " ",
                  "terms": {
                      "availability": {
                          "metrics": {
                              "uptime": {
                                  "limiter_value": "2",
                                  "limiter_type": "margin",
                                  "value": "98"
                              }
                          },
                          "remedy": "0.10"
                      }
                  },
                  "devices": ["/compute/bbbbbb-bbbbbb"]
                  }

        policy2 = {"_id": "cccccc-cccc-cccccc",
                  "agreement_id": "/agreement/test-agreement-id",
                  "policy": " ",
                  "terms": {
                      "availability": {
                          "metrics": {
                              "uptime": {
                                  "limiter_value": "2",
                                  "limiter_type": "margin",
                                  "value": "98"
                              }
                          },
                          "remedy": "0.10"
                      }
                  },
                  "devices": ["/compute/testing-device"]
                  }

        monitoring = {"_id": "dummy-merlin",
                      "name": "dummy-merlin",
                      "metrics": ["vcpu", "scu", "power"],
                      "api": "DummyMerlinCollector"
                      }

        DB.devices.insert(device1)
        DB.devices.insert(device2)
        DB.devices.insert(device3)
        DB.policies.insert(policy1)
        DB.policies.insert(policy2)
        DB.monitoring.insert(monitoring)

    def tearDown(self):
        DB.devices.remove({'_id': "/compute/aaaaaa-aaaaaa"})
        DB.devices.remove({'_id': "/compute/bbbbbb-bbbbbb"})
        DB.devices.remove({'_id': "/compute/testing-device"})
        DB.policies.remove({'_id': "cccccc-bbbbbb-cccccc"})
        DB.policies.remove({'_id': "cccccc-cccc-cccccc"})
        DB.monitoring.remove({'_id': "dummy-merlin"})


    def test_get_collector_class_for_wrong_device(self):
        """

        """

        gator = Aggregator()
        device_id = "dummy_device"
        metric = "dummy_metric"
        self.assertRaises(AttributeError, gator.get_collector_class, device_id, metric)


    def test_subscribe_term_metric_not_found(self):
        """

        """
        gator = Aggregator()
        term = "availability"
        agreement_id = "dummy"
        metrics_info = {
            "metrics": {
                "dummy_metric": {
                    "limiter_type": "max",
                    "value": "120.0"
                }
            }
        }
        device_ids = ["/compute/bbbbbb-bbbbbb"]

        self.assertRaises(AttributeError, gator.subscribe_term, term, agreement_id, metrics_info, device_ids)


    def test_subscribe_term_monitoring_api_error(self):
        """

        """
        gator = Aggregator()
        term = "availability"
        agreement_id = "dummy"
        metrics_info = {
            "metrics": {
                "scu": {
                    "limiter_type": "max",
                    "value": "120.0"
                }
            }
        }
        device_ids = ["/compute/bbbbbb-bbbbbb"]

        self.assertRaises(RuntimeWarning, gator.subscribe_term, term, agreement_id, metrics_info, device_ids)

    def test_notification_event(self):
        """
            Tests if the RE.reason_agreement raises a type error for an empty policy.
        """
        gator = Aggregator()
        self.assertRaises(TypeError, gator.notification_event, "/compute/testing-device", "uptime", 80)
