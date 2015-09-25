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
from api import create_providers_credentials as provider_details
from occi.backend import ActionBackend, KindBackend, MixinBackend
import sample_data.the_test_data as test_data
from api import occi_sla, backends
from pymongo import MongoClient
from occi import core_model
from api import templates
from api import api
import unittest
import logging
import arrow
import time
import json
import pdb

LOG = logging.getLogger(__name__)
DB = MongoClient().sla


class TestAgreementBackend(unittest.TestCase):
    def setUp(self):
        self.agree_back = backends.Agreement()
        self.extras = {"security": {"DSS": "dss_pass"}, "customer": "larry"}
        self.entity = core_model.Resource('', occi_sla.AGREEMENT,
                                          [occi_sla.AGREEMENT_TEMPLATE])
        self.entity.attributes = \
            {"occi.agreement.effectiveFrom": "2114-11-02T02:17:26Z",
             "occi.agreement.effectiveUntil": "2114-11-02T02:17:29Z"}
        self.template_list = json.load(
            file("tests/sample_data/template_definition_v2.json"))
        provider_details.load_providers()

    def tearDown(self):
        self.entity = None
        DB.templates.remove({})
        DB.providers.remove({})

    def test_agreement_rejects_immutable_attributes(self):
        # Raise error for immutable attributes
        immut_attr = [key for key, val in self.entity.kind.attributes.items()
                      if val == "immutable"][0]
        self.entity.attributes[immut_attr] = "irrelevant"
        self.assertRaises(AttributeError, self.agree_back.create, self.entity,
                          self.extras)
        LOG.info("Agreement won't allow immutable attributes")

    def test_attributes_belong_to_agreement_or_mixin(self):
        """
            Test to ensure attributes that don't belong to the agreement or
            mixin are rejected.
        """
        # m1 & m2 just mixins containing some attributes
        self.entity.mixins.append(test_data.m1)
        self.entity.mixins.append(test_data.m2)

        self.entity.attributes = {"occi.agreement.effectiveFrom": "14001245",
                                  "unknown": "whatever"}

        self.assertRaises(AttributeError, self.agree_back.create, self.entity,
                          self.extras)
        LOG.info("Agreement wont allow unknown attributes")

    def test_that_required_attributes_are_used(self):
        """
            Test that required attributes are being used.
        """
        # m3 has required attributes 
        self.entity.mixins.append(test_data.m3)

        self.entity.attributes = {"occi.agreement.effectiveFrom": "14001245",
                                  "os": "ubuntu", "vm_cores": "4"}
        self.assertRaises(AttributeError, self.agree_back.create, self.entity,
                          self.extras)
        LOG.info("Agreement ensures use of required variables")

    def test_agreement_state_set_pending_on_creation(self):
        """
            Test that the agreement state is set to pending on creation
        """
        api.build()  # instantiate api for backends
        self.entity.mixins.append(self._get_sample_provider_mixins()[0][0])
        self.agree_back.create(self.entity, self.extras)

        entity_state = self.entity.attributes["occi.agreement.state"]
        self.assertEqual(entity_state, "pending")
        LOG.info("Agreement has inital state set to 'pending'.")

    def test_agreement_changes_from_pending_to_accepted_on_accept_action(self):
        """
            Test correct transition of state on accept
        """
        self.entity.attributes["occi.agreement.state"] = "pending"
        self.entity.__dict__["provider"] = "DSS"
        action = occi_sla.ACCEPT_ACTION
        self.agree_back.action(self.entity, action, None, self.extras)

        entity_state = self.entity.attributes["occi.agreement.state"]
        self.assertEqual(entity_state, "accepted")

    def test_agreement_update_agreedAt_onagreement_acceptance(self):
        """
            Test to ensure that the agreedAt attribute is set when the
            agreement is accepted and that it is being set to (relatively) the
            correct value.
        """
        action = occi_sla.ACCEPT_ACTION
        self.entity.__dict__["provider"] = "DSS"
        self.entity.attributes["occi.agreement.state"] = "pending"
        self.agree_back.action(self.entity, action, None, self.extras)

        agreedat_s = self.entity.attributes["occi.agreement.agreedAt"]

        delta = time.time() - arrow.get(agreedat_s).timestamp

        self.assertGreaterEqual(delta, -1)
        self.assertLessEqual(delta, 1)
        LOG.info("Agreement set agreedAt atrribute on agreement acceptance")

    def test_refusal_of_accept_on_any_agreement_with_state_not_pending(self):
        """
            This test is to ensure that an accept action raises an error on any
            agreement that is not in state pending
        """
        action = occi_sla.ACCEPT_ACTION
        self.entity.__dict__["provider"] = "DSS"
        self.entity.attributes["occi.agreement.state"] = "rejected"
        self.assertRaises(Exception, self.agree_back.action, self.entity,
                          action, None, self.extras)

        self.entity.attributes["occi.agreement.state"] = "accepted"
        self.assertRaises(Exception, self.agree_back.action, self.entity,
                          action, None, self.extras)

        self.entity.attributes["occi.agreement.state"] = "suspended"
        self.assertRaises(Exception, self.agree_back.action, self.entity,
                          action, None, self.extras)
        LOG.info("Agreement not allowing accept action on an invalid \
                 agreement state")

    def test_reject_action_on_pending_agreement(self):
        """
            ENsure that the reject action changes the state appropriately
        """
        action = occi_sla.REJECT_ACTION
        self.entity.attributes["occi.agreement.state"] = "pending"
        self.entity.__dict__["provider"] = "DSS"

        self.agree_back.action(self.entity, action, None, self.extras)
        agreement_state = self.entity.attributes["occi.agreement.state"]
        self.assertEqual(agreement_state, "rejected")
        LOG.info("Aggreement transitions to correct state on reject action")

    def test_refusal_of_reject_on_any_agreement_with_state_not_pending(self):
        """
            This test is to ensure that an accept action raises an error on any
            agreement that is not in state pending
        """
        action = occi_sla.REJECT_ACTION
        self.entity.attributes["occi.agreement.state"] = "rejected"
        self.assertRaises(Exception, self.agree_back.action, self.entity,
                          action, None, None)

        self.entity.attributes["occi.agreement.state"] = "accepted"
        self.assertRaises(Exception, self.agree_back.action, self.entity,
                          action, None, None)

        self.entity.attributes["occi.agreement.state"] = "suspended"
        self.assertRaises(Exception, self.agree_back.action, self.entity,
                          action, None, None)
        LOG.info("Agreement not allowing reject action on an invalid \
                 agreement state")

    def test_suspend_action_on_accepted_agreement(self):
        """
            Esure that the suspend action changes the state appropriately
        """
        action = occi_sla.SUSPEND_ACTION
        self.entity.attributes["occi.agreement.state"] = "accepted"
        self.entity.__dict__["provider"] = "DSS"

        self.agree_back.action(self.entity, action, None, self.extras)
        agreement_state = self.entity.attributes["occi.agreement.state"]
        self.assertEqual(agreement_state, "suspended")
        LOG.info("Aggreement transitions to correct state on suspend action")

    def test_refusal_of_suspend_on_any_agreement_with_state_not_accepted(self):
        """
            This test is to ensure that a suspend action raises an error on \
            any agreement that is not in state accepted
        """
        action = occi_sla.SUSPEND_ACTION
        self.entity.attributes["occi.agreement.state"] = "rejected"
        self.entity.__dict__["provider"] = "DSS"
        self.assertRaises(Exception, self.agree_back.action, self.entity,
                          action, None, self.extras)

        self.entity.attributes["occi.agreement.state"] = "pending"
        self.assertRaises(Exception, self.agree_back.action, self.entity, action, None, self.extras)

        self.entity.attributes["occi.agreement.state"] = "suspended"
        self.assertRaises(Exception, self.agree_back.action, self.entity,
                          action, None, self.extras)
        LOG.info("Agreement not allowing suspend action on an invalid \
                 agreement state")

    def test_unsuspend_action_on_suspended_agreement(self):
        """
            Esure that the suspend action changes the state appropriately
        """
        action = occi_sla.UNSUSPEND_ACTION
        self.entity.attributes["occi.agreement.state"] = "suspended"
        self.entity.__dict__["provider"] = "DSS"

        self.agree_back.action(self.entity, action, None, self.extras)
        agreement_state = self.entity.attributes["occi.agreement.state"]
        self.assertEqual(agreement_state, "accepted")
        LOG.info("Agreement transitions to correct state on unsuspend action")

    def test_refusal_of_suspend_on_any_agreement_with_state_not_accepted(self):
        """
            This test is to ensure that a suspend action raises an error on \
            any agreement that is not in state accepted
        """
        action = occi_sla.UNSUSPEND_ACTION
        self.entity.attributes["occi.agreement.state"] = "rejected"
        self.entity.__dict__["provider"] = "DSS"
        self.assertRaises(Exception, self.agree_back.action, self.entity,
                          action, None, self.extras)

        self.entity.attributes["occi.agreement.state"] = "pending"
        self.assertRaises(Exception, self.agree_back.action, self.entity, action, None, self.extras)

        self.entity.attributes["occi.agreement.state"] = "accepted"
        self.assertRaises(Exception, self.agree_back.action, self.entity,
                          action, None, self.extras)
        LOG.info("Agreement not allowing suspend action on an invalid \
                 agreement state")

    def test_correct_attributes_are_retrieved_for_a_given_template(self):
        """
            Given a template a the attributes for each term are extracted and
            returned. ID names are ammended to avoid conflicts.
        """
        template = self.template_list["templates"]["gold"]
        attributes = self.agree_back._get_template_attributes(template, "gold")
        expected_attributes = {"gold.compute.vcpu": 4,
                               "gold.compute.os": "ubuntu",
                               "gold.compute.memory": 2048,
                               "gold.availability.uptime": 98,
                               "gold.efficiency.power": 120.0}
        self.assertEqual(attributes, expected_attributes)


    def test_create_all_terms_for_a_template(self):
        """
            Checks that the correct terms are added for a given template
        """
        # api being build
        self._load_template_database()
        nrth_bnd_api = api.build()
        tmp_mxn = nrth_bnd_api.registry.get_category("/silver/", None)
        cmp_trm = nrth_bnd_api.registry.get_category("/compute/", None)
        avl_trm = nrth_bnd_api.registry.get_category("/availability/", None)
        expctd_mxns = [tmp_mxn, cmp_trm, avl_trm]

        self.entity.mixins = [tmp_mxn]
        self.agree_back.create(self.entity, self.extras)

        # Add temp so now the entity should have terms and silver template mixin
        self.assertEqual(set(self.entity.mixins), set(expctd_mxns))

    def test_add_attributes_from_terms_to_agreement(self):
        """
            Takes attributes from the terms and adds them to the agreement
        """
        expected_attrs = {"silver.compute.vcpu": 1,
                          "silver.compute.os": "ubuntu",
                          "silver.compute.memory": 1024,
                          "silver.availability.uptime": 85}
        self._load_template_database()
        nrth_bnd_api = api.build()
        tmp_mxn = nrth_bnd_api.registry.get_category("/silver/", None)

        self.entity.mixins = [tmp_mxn]
        self.agree_back.create(self.entity, self.extras)
        issub_set = all(item in self.entity.attributes.items() for item in expected_attrs.items())
        self.assertTrue(issub_set)

    def test_term_type_attributes_added_on_creation(self):
        """
            Ensures that the agreement terms attributes are added for each term
        """
        expctd_attrs = {"compute.term.type": 'SERVICE-TERM',
                        "compute.term.state": 'undefined',
                        "compute.term.desc": "",
                        "availability.term.type": 'SLO-TERM',
                        "availability.term.state": 'undefined',
                        "availability.term.desc": ''
                        }

        self._load_template_database()
        nrth_bnd_api = api.build()
        tmp_mxn = nrth_bnd_api.registry.get_category("/silver/", None)

        self.entity.mixins = [tmp_mxn]
        self.agree_back.create(self.entity, self.extras)

        issub_set = all(item in self.entity.attributes.items() for item in expctd_attrs.items())

        self.assertTrue(issub_set)

    def test_provider_login_credentials_correct(self):
        """
            Compares the submitted user credentials against the database
        """
        extras = {"security": {"unknown": "incorrect"}}
        self._load_template_database()
        nrth_bnd_api = api.build()
        tmp_mxn = nrth_bnd_api.registry.get_category("/silver/", None)

        self.entity.mixins = [tmp_mxn]
        self.assertRaises(AttributeError, self.agree_back.create, self.entity, extras)

    def test_provider_login_credentials_when_none(self):
        """
            No security details provided
        """
        extras = {}
        self._load_template_database()
        nrth_bnd_api = api.build()
        tmp_mxn = nrth_bnd_api.registry.get_category("/silver/", None)

        self.entity.mixins = [tmp_mxn]
        self.assertRaises(AttributeError, self.agree_back.create, self.entity, extras)

    def test_provider_id_added_to_entity(self):
        """
            Ensures that provider id is added to a newly created agreement 
        """
        self._load_template_database()
        nrth_bnd_api = api.build()
        tmp_mxn = nrth_bnd_api.registry.get_category("/silver/", None)
        self.entity.mixins = [tmp_mxn]
        DB.providers.insert({"username": "prov_123", "password": "pass"})
        extras = {"security": {"prov_123": "pass"}, "customer": "test"}

        self.agree_back.create(self.entity, extras)
        self.assertEqual(self.entity.provider, "prov_123")
        DB.providers.remove({"username": "prov_123"})

    def test_customer_id_added_to_entity(self):
        """
            Ensures that customer id is added to the agreement
        """
        self._load_template_database()
        nrth_bnd_api = api.build()
        tmp_mxn = nrth_bnd_api.registry.get_category("/silver/", None)
        self.entity.mixins = [tmp_mxn]
        extras = {"security": {"DSS": "dss_pass"}, "customer": "customer_1234"}

        self.agree_back.create(self.entity, extras)
        self.assertEqual(self.entity.customer, "customer_1234")

    def test_retrieve_agreement_with_incorrect_provider_id(self):
        """
            Checks that agreement cannot be retrieved by a provider with wrong
            id.
        """
        self.entity.provider = "prov_123"
        extras = {"security": {"DSS": "dss_pass"}, "customer": "cust_1234"}

        self.assertRaises(AttributeError, self.agree_back.retrieve, self.entity,
                          extras)

    def test_delete_only_works_for_correct_provider(self):
        """
            Ensure that only the correct provider can delete an agreement
        """
        self.entity.provider = "prov_123"
        extras = {"security": {"DSS": "dss_pass"}, "customer": "cust_1234"}

        self.assertRaises(AttributeError, self.agree_back.delete, self.entity,
                          extras)

    def test_delete_only_works_for_correct_provider(self):
        """
            Ensure that only the correct provider can delete an agreement
        """
        self.entity.provider = "prov_123"
        extras = {"security": {"DSS": "dss_pass"}, "customer": "cust_1234"}

        self.assertRaises(AttributeError, self.agree_back.update, self.entity,
                          self.entity, extras)

    def test_action_only_works_for_correct_provider(self):
        """
            Ensure that only the correct provider can delete an agreement
        """
        self.entity.provider = "prov_123"
        extras = {"security": {"DSS": "dss_pass"}, "customer": "cust_1234"}
        action = occi_sla.ACCEPT_ACTION
        self.entity.attributes["occi.agreement.state"] = "pending"

        self.assertRaises(AttributeError, self.agree_back.action, self.entity,
                          action, None, extras)

    def test_attribute_effective_from_in_attributes(self):
        """
            Ensures that the 'occi.agreement.effectiveFrom' attribute is set
        """
        self._load_template_database()
        nrth_bnd_api = api.build()
        tmp_mxn = nrth_bnd_api.registry.get_category("/silver/", None)
        self.entity.mixins = [tmp_mxn]
        del self.entity.attributes["occi.agreement.effectiveFrom"]
        self.assertRaises(AttributeError, self.agree_back.create, self.entity,
                          self.extras)

    def test_attribute_effective_Until_in_attributes(self):
        """
            Ensures that the 'occi.agreement.effectiveUntil' attribute is set
        """
        self._load_template_database()
        nrth_bnd_api = api.build()
        tmp_mxn = nrth_bnd_api.registry.get_category("/silver/", None)
        self.entity.mixins = [tmp_mxn]
        del self.entity.attributes["occi.agreement.effectiveUntil"]
        self.assertRaises(AttributeError, self.agree_back.create, self.entity,
                          self.extras)

    def test_agreement_period_positive(self):
        """
            Check that the time between 'occi.agreement.effectiveFrom' and
            'occi.agreement.effectiveUntil' is positive
        """
        self._load_template_database()
        nrth_bnd_api = api.build()
        tmp_mxn = nrth_bnd_api.registry.get_category("/silver/", None)
        self.entity.mixins = [tmp_mxn]
        times = {"occi.agreement.effectiveFrom": "2014-11-02T02:20:26Z",
                 "occi.agreement.effectiveUntil": "2014-11-02T02:17:26Z"}
        self.entity.attributes = times
        self.assertRaises(AttributeError, self.agree_back.create, self.entity,
                          self.extras)

    def test_only_accept_before_end_of_contract(self):
        """
            Only allow accept action before the contract expires
        """
        attrs = {"occi.agreement.effectiveFrom": "2014-11-05T14:00:00Z",
                 "occi.agreement.effectiveUntil": "2014-11-12T14:00:00Z",
                 "occi.agreement.state": "pending"}
        self.entity.attributes = attrs
        self.entity.__dict__["provider"] = "DSS"
        action = occi_sla.ACCEPT_ACTION
        self.assertRaises(AttributeError, self.agree_back.action, self.entity,
                          action, None, self.extras)

    def test_update_contract_duration(self):
        """
            Test that "occi.agreement.effectiveFrom" and
            "occi.agreement.effectiveUntil" are updated
        """
        # entity comes pre-loaded with from and until times diff to below
        self.entity.__dict__["provider"] = "DSS"
        self.entity.attributes["occi.agreement.state"] = "pending"
        attrs = {"occi.agreement.effectiveFrom": "2014-11-05T14:00:00Z",
                 "occi.agreement.effectiveUntil": "2014-11-12T14:00:00Z",
                 "occi.agreement.state": "pending"}
        new = core_model.Resource('', occi_sla.AGREEMENT,
                                  [occi_sla.AGREEMENT_TEMPLATE])
        new.attributes = attrs
        self.agree_back.update(self.entity, new, self.extras)

        from_expected = arrow.get(attrs["occi.agreement.effectiveFrom"])
        from_actual = arrow.get(
            self.entity.attributes["occi.agreement.effectiveFrom"])
        until_expected = arrow.get(attrs["occi.agreement.effectiveUntil"])
        until_actual = arrow.get(
            self.entity.attributes["occi.agreement.effectiveUntil"])

        self.assertEqual(from_expected, from_actual)
        self.assertEqual(until_expected, until_actual)

    def _get_sample_provider_mixins(self):
        tmps = self._load_template_database()
        # get template mixins
        return api.build_template_lst_mixins(tmps)

    def _load_template_database(self):
        # load template definition into database
        tmps = json.load(file("tests/sample_data/template_definition_v2.json"))
        templates.load_templates(tmps)
        return tmps
        # TODO: Validate customer. cal validate extras from getcutomer
        # TODO: More tests to test extras validation. cover all if statements
        # TODO:  Add test to ensure that ^ is not used as a key name for attributes
        # as it is used later to substitute '.' inkeynames which is refused by
        # mongo.
