from api import rulesengine
import logging
import json
import unittest
from pymongo import MongoClient
from api import create_providers_credentials as provider_details
from occi import core_model
from api import occi_sla
from api import api
from api import templates
from api.entity_dictionary import EntityDictionary
from occi.extensions import infrastructure

# LOG = logging.getLogger(__name__)
DB = MongoClient().sla
# logging.basicConfig(level='INFO')


class AgreementPolicyDetection(unittest.TestCase):
    def setUp(self):

        self.temps = json.load(file("tests/sample_data/template_definition_v2.json"))
        self.extras = {"security": {"DSS": "dss_pass"}, "customer": "larry"}

        templates.load_templates(self.temps)
        provider_details.load_providers()

        self.id = "/agreement/4545-4545454-sdasdas"
        self.compute_id = "/compute/ccccccc-ddddddd"
        self.link_id = "/agreement_link/lllllll-ddddddd"


    def tearDown(self):

        DB.templates.remove({})
        DB.providers.remove({})
        DB.policies.remove({})
        DB.entities.remove({'_id': self.id})
        DB.entities.remove({'_id': self.link_id})
        DB.entities.remove({'_id': self.compute_id})
        rulesengine.RulesEngine._agreements_under_reasoning = []

    def test_pending_agreement_non_detection(self):
        """
		   Check that the temp agreement with pending state is not detected as active agreement.
		"""

        gold = core_model.Mixin('', 'gold', [occi_sla.AGREEMENT_TEMPLATE])
        compute = core_model.Mixin('', 'compute', [])
        availability = core_model.Mixin('', 'availability', [])
        mixins = [gold, compute, availability]
        res = core_model.Resource(self.id, occi_sla.AGREEMENT, mixins)
        res.attributes = {'occi.agreement.state': 'pending',
                          'occi.agreement.effectiveFrom': '2014-11-02T02:20:26+00:00',
                          'occi.agreement.effectiveUntil': '2015-11-02T02:20:27+00:00'
                          }

        northbound_api = api.build()
        resources = EntityDictionary(northbound_api.registry)
        resources[self.id] = res
        resources.registry.populate_resources()

        active_agreements = resources.registry.get_active_agreement_resources()

        self.assertEqual(active_agreements.__len__(), 0)

    def test_past_agreement_non_detection(self):
        """
		   Check that the temp agreement with pending state is not detected as active agreement.
		"""

        gold = core_model.Mixin('', 'gold', [occi_sla.AGREEMENT_TEMPLATE])
        compute = core_model.Mixin('', 'compute', [occi_sla.AGREEMENT_TEMPLATE])
        availability = core_model.Mixin('', 'availability', [occi_sla.AGREEMENT_TEMPLATE])
        mixins = [gold, compute, availability]
        res = core_model.Resource(self.id, occi_sla.AGREEMENT, mixins)
        res.attributes = {'occi.agreement.state': 'accepted',
                          'occi.agreement.effectiveFrom': '2014-10-02T02:20:26+00:00',
                          'occi.agreement.effectiveUntil': '2014-11-02T02:20:27+00:00'
                          }

        northbound_api = api.build()
        resources = EntityDictionary(northbound_api.registry)
        resources[self.id] = res
        resources.registry.populate_resources()

        active_agreements = resources.registry.get_active_agreement_resources()

        self.assertEqual(active_agreements.__len__(), 0)


    def test_active_agreement_detection(self):
        """
		   Check that the temp agreement is detected as active agreement.
		"""

        gold = core_model.Mixin('', 'gold', [occi_sla.AGREEMENT_TEMPLATE])
        compute = core_model.Mixin('', 'compute', [occi_sla.AGREEMENT_TEMPLATE])
        availability = core_model.Mixin('', 'availability', [occi_sla.AGREEMENT_TEMPLATE])
        mixins = [gold, compute, availability]
        res = core_model.Resource(self.id, occi_sla.AGREEMENT, mixins)
        res.attributes = {'occi.agreement.state': 'accepted',
                          'occi.agreement.effectiveFrom': '2014-11-02T02:20:26+00:00',
                          'occi.agreement.effectiveUntil': '2015-11-02T02:20:27+00:00'
                          }

        northbound_api = api.build()
        resources = EntityDictionary(northbound_api.registry)
        resources[self.id] = res

        resources.registry.populate_resources()

        active_agreements = resources.registry.get_active_agreement_resources()

        if active_agreements.__len__() == 1:
            self.assertEqual(active_agreements[0].identifier, self.id)
        else:
            for agr in active_agreements:
                self.assertTrue(agr.identifier == self.id)


    def test_no_policy_creation(self):
        """
			Check that if no link (aka device id) exist, no policy is created
		"""
        gold = core_model.Mixin('', 'gold', [occi_sla.AGREEMENT_TEMPLATE])
        compute = core_model.Mixin('', 'compute', [occi_sla.AGREEMENT_TEMPLATE])
        availability = core_model.Mixin('', 'availability', [occi_sla.AGREEMENT_TEMPLATE])
        mixins = [gold, compute, availability]
        res = core_model.Resource(self.id, occi_sla.AGREEMENT, mixins)
        res.attributes = {'occi.agreement.state': 'accepted',
                          'occi.agreement.effectiveFrom': '2014-11-02T02:20:26+00:00',
                          'occi.agreement.effectiveUntil': '2015-11-02T02:20:27+00:00'
                          }

        northbound_api = api.build()
        resources = EntityDictionary(northbound_api.registry)
        resources[self.id] = res

        resources.registry.populate_resources()

        myrulesengine = rulesengine.RulesEngine(resources.registry)
        myrulesengine.active_policies = {}
        myrulesengine.active_agreements = {}
        # myrulesengine.registry=registry

        myrulesengine.start_engine(0)

        temp_policy_record = DB.policies.find({'agreement_id': self.id}, {'_id': 0})

        self.assertEqual(temp_policy_record.count(), 0)

    def test_policy_creation(self):
        """
			Check that an active agreement has been detected and a record inserted into the database
		"""
        availability = core_model.Mixin('', 'availability', [occi_sla.AGREEMENT_TEMPLATE])
        mixins = [availability]
        res = core_model.Resource(self.id, occi_sla.AGREEMENT, mixins)
        res.attributes = {'occi.agreement.state': 'accepted',
                          'occi.agreement.effectiveFrom': '2014-11-02T02:20:26+00:00',
                          'occi.agreement.effectiveUntil': '2015-11-02T02:20:27+00:00'
                          }

        comp_res = core_model.Resource(self.compute_id, infrastructure.COMPUTE, [])
        comp_res.attributes = {}

        link_res = core_model.Link(self.link_id, occi_sla.AGREEMENT_LINK, [], res, comp_res)
        link_res.attributes = {}

        res.links = [link_res]

        northbound_api = api.build()
        resources = EntityDictionary(northbound_api.registry)
        resources[self.id] = res
        resources[self.compute_id] = comp_res
        resources[self.link_id] = link_res

        resources.registry.populate_resources()

        myrulesengine = rulesengine.RulesEngine(resources.registry)
        myrulesengine.active_policies = {}
        myrulesengine.active_agreements = {}

        myrulesengine.start_engine(0)

        temp_policy_record = DB.policies.find({'agreement_id': self.id}, {'_id': 0})

        self.assertEqual(temp_policy_record.count(), 1)


    def test_reason_agreement_no_policy(self):
        """
		   Tests an agreement reasoning when there is no policy in the db.
		"""

        attributes = {'occi.agreement.effectiveFrom': '2014-11-02T02:20:26+00:00',
                      'occi.agreement.effectiveUntil': '2015-11-02T02:20:27+00:00',
                      'occi.agreement.state': 'accepted',
                      'availability.term.type': 'SLO-TERM',
                      'availability.term.state': 'fulfilled',
                      'availability.term.desc': '',
                      'availability.term.remedy': 0.10,
                      'gold.availability.uptime.limiter_value': 2,
                      'gold.availability.uptime.limiter_type': 'margin',
                      'gold.availability.uptime': 98,
                      }

        terms = {
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
        }

        agreement_id = self.id

        myrulesengine = rulesengine.RulesEngine()

        monitored_metrics = {'uptime': 90}

        self.assertRaises(AttributeError, myrulesengine.reason_agreement, self.id, monitored_metrics,
                          '/compute/dummy_id')

    def test_reason_agreement_intellect_error(self):
        """
			Reasons an agreement policy which has wrong syntax
		"""
        attributes = {'occi.agreement.effectiveFrom': '2014-11-02T02:20:26+00:00',
                      'occi.agreement.effectiveUntil': '2015-11-02T02:20:27+00:00',
                      'occi.agreement.state': 'accepted',
                      'efficiency.term.type': 'SLO-TERM',
                      'efficiency.term.state': 'fulfilled',
                      'efficiency.term.desc': '',
                      'efficiency.term.remedy': 0.10,
                      'gold.efficiency.power.limiter_type': 'max',
                      'gold.efficiency.power': 98,
                      }

        terms = {
            "efficiency": {
                "metrics": {
                    "power": {
                        "limiter_type": "max",
                        "value": "98"
                    }
                },
                "remedy": "0.10"
            }
        }

        agreement_id = self.id

        policy = "import logging\n\n" \
                 "rule \"efficiency for /agreement/4545-4545454-sdasdas\":\n" \
                 "        when:\n" \
                 "                $RulesEngineHelper := RulesEngineHelper(agreement_term_violated(\"/agreement/4545-4545454-sdasdas\",\"efficiency\"))\n" \
                 "        then:\n                log(\"A violation is fired for :/agreement/4545-4545454-sdasdas - efficiency\")\n" \
                 "                $RulesEngineHelper.agreement_term_apply_remedy(\"/agreement/4545-4545454-sdasdas\",\"efficiency\")\n\n"

        DB.policies.insert({'agreement_id': agreement_id, 'policy': policy, 'terms': terms})

        myrulesengine = rulesengine.RulesEngine()

        monitored_metrics = {'power': 100}

        self.assertRaises(AttributeError, myrulesengine.reason_agreement, self.id, monitored_metrics,
                          '/compute/dummy_id')


if __name__ == '__main__':
    unittest.main()
