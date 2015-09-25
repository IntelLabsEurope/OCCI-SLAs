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
    Tests to ensure that this interface conforms tp OCCI SLA Specification
"""

import occi
import unittest
import logging
from api import api

LOG = logging.getLogger(__name__)


#TODO:  Add test to ensure that ^ is not used as a key name for attributes
# as it is used later to substitute '.' inkeynames which is refused by
# mongo.

class TestOcciSlaAgreement(unittest.TestCase):
    """
        Tests to ensure SLA Agreement Kind is compliant to standard
    """

    def setUp(self):
        api_n = api.build()
        self.agreement = api_n.registry.get_category("/agreement/", None)

    def test_agreement_type(self):
        self.assertNotEqual(self.agreement, None)
        LOG.info("Agreement Category retrieved")

        self.assertTrue(isinstance(self.agreement, occi.core_model.Kind))
        LOG.info("Agreement verified as type kind")

        expected_scheme = "http://schemas.ogf.org/occi/sla#"
        self.assertEqual(self.agreement.scheme, expected_scheme)
        LOG.info("Agreement scheme verified: {0}".format(expected_scheme))

    def test_agreement_is_linked_to_resource(self):
        expected_scheme = "http://schemas.ogf.org/occi/core#"
        expected_term = "resource"
        expected_related = {(expected_scheme, expected_term)}
        actual_related = set(
            [(rel.scheme, rel.term) for rel in self.agreement.related])

        intrsct_actual_expected = expected_related.intersection(actual_related)
        self.assertEqual(intrsct_actual_expected, expected_related)
        LOG.info("Agreement is related to occi core resource")

    def test_agreement_attributes(self):
        expected_attributes = {"occi.agreement.state": "immutable",
                               "occi.agreement.agreedAt": "immutable",
                               "occi.agreement.effectiveFrom": "mutable",
                               "occi.agreement.effectiveUntil": "mutable"}
        self.assertEqual(self.agreement.attributes, expected_attributes)
        LOG.info("Agreement attributes verified")

    def test_agreement_actions(self):
        scheme = self.agreement.scheme
        expected_terms = [
            ("accept", scheme), ("reject", scheme), ("suspend", scheme),
            ("unsuspend", scheme)]
        terms = [
            (action.term, action.scheme) for action in self.agreement.actions]
        self.assertEqual(set(terms), set(expected_terms))
        LOG.info("Agreement Actions verified")


class TestOcciSlaAgreementLink(unittest.TestCase):
    """
        Tests to ensure SLA 'Agreement Link Kind' is compliant to standard
    """

    def setUp(self):
        api_n = api.build()
        self.agreement_link = api_n.registry.get_category("/agreement_link/",
                                                          None)

    def test_agreement_link_in_registry(self):
        self.assertIsNotNone(self.agreement_link)
        LOG.info("Agreement Link in Registry")

    def test_agreement_link_is_of_type_kind(self):
        self.assertTrue(isinstance(self.agreement_link, occi.core_model.Kind))
        LOG.info("Agreement Link is of type Kind")

    def test_agreement_link_is_related_to_occi_core_link(self):
        """
            This test is part of a requirement set in the OGF OCCI SLA spec
        """
        expected_scheme = "http://schemas.ogf.org/occi/core#"
        expected_term = "link"
        expected_related = {(expected_scheme, expected_term)}
        actual_related = set(
            [(rel.scheme, rel.term) for rel in self.agreement_link.related])

        intrsct_actual_expected = expected_related.intersection(actual_related)
        self.assertEqual(intrsct_actual_expected, expected_related)
        LOG.info("Agreement Link is related to occi core link")


class TestOcciSlaAgreementTern(unittest.TestCase):
    """
        Tests to ensure SLA 'Agreement Term' Mixin is compliant to standard
    """

    def setUp(self):
        api_n = api.build()
        self.agreement_term = api_n.registry.get_category("/agreement_term/",
                                                          None)

    def test_agreement_term_in_registry(self):
        self.assertIsNotNone(self.agreement_term)
        LOG.info("Agreement term is in registry")

    def test_agreement_term_is_of_type_mixin(self):
        self.assertTrue(isinstance(self.agreement_term, occi.core_model.Mixin))
        LOG.info("Agreement term is of type Mixin")

    def test_agreement_term_scheme(self):
        expected_scheme = "http://schemas.ogf.org/occi/sla#"
        self.assertEqual(self.agreement_term.scheme, expected_scheme)
        LOG.info("Agreement term has scheme {}".format(expected_scheme))

    def test_agreement_term_term(self):
        expected_term = "agreement_term"
        self.assertEqual(self.agreement_term.term, expected_term)
        LOG.info("Agreement Term has term {0}".format(expected_term))


class TestOcciSlaAgreementTemplate(unittest.TestCase):
    """
        Tests to ensure SLA 'Agreement Template' Mixin is compliant to standard
    """

    def setUp(self):
        api_n = api.build()
        self.agreement_template = api_n.registry.get_category("/agreement_tpl/",
                                                              None)

    def test_agreement_template_in_registery(self):
        self.assertIsNotNone(self.agreement_template)
        LOG.info("Agreement template is not in registry")

    def test_agreement_template_is_of_type_mixin(self):
        self.assertTrue(isinstance(self.agreement_template,
                                   occi.core_model.Mixin))
        LOG.info("Agreement template is of type Mixin")

    def test_agreement_template_scheme(self):
        expected_scheme = "http://schemas.ogf.org/occi/sla#"
        self.assertEqual(self.agreement_template.scheme, expected_scheme)
        LOG.info("Agreement template has scheme {}".format(expected_scheme))

    def test_agreement_template_term(self):
        expected_term = "agreement_tpl"
        self.assertEqual(self.agreement_template.term, expected_term)
        LOG.info("Agreement Template has term {0}".format(expected_term))
