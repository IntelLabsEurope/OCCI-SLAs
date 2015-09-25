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
import json
import unittest
import pdb
from pymongo import MongoClient
from api import templates


class PersistingTemplateDefintions(unittest.TestCase):
    def setUp(self):
        samp_temp_addr = "tests/sample_data/testdata_template_definition.json"
        self.sample_templates = json.load(file(samp_temp_addr))
        self.db = self._get_db_connection()

    def tearDown(self):
        self.db.templates.remove()

    def _get_db_connection(self):
        db_client = MongoClient()
        db = db_client.sla
        return db

    def test_persist_template_definitions(self):
        """
            check that template is saved to the database
        """
        persistable_temp = self.sample_templates.get("persistable")
        templates.load_templates(persistable_temp)
        scheme = persistable_temp["scheme"]
        temp_record_db = self.db.templates.find({"_id": scheme})
        self.assertEqual(temp_record_db.count(), 1)

    def test_update_template_in_db(self):
        """
            Test to ensure that the same template definition is not saved twice
            and updates the db record
        """
        persistable_temp = self.sample_templates.get("persistable")
        templates.load_templates(persistable_temp)
        persistable_temp["fake_attr"] = "dummy_value"
        templates.load_templates(persistable_temp)

        key = persistable_temp["scheme"]
        db_record = self.db.templates.find({"_id": key})

        self.assertEqual(db_record.count(), 1)
        self.assertIn("fake_attr", db_record[0])


class ValidatingTemplateDefinitions(unittest.TestCase):
    def setUp(self):
        samp_temp_addr = "tests/sample_data/testdata_template_definition.json"
        self.sample_templates = json.load(file(samp_temp_addr))
        self.db = self._get_db_connection()

    def tearDown(self):
        self.db.templates.remove()

    def _get_db_connection(self):
        db_client = MongoClient()
        db = db_client.sla
        return db

    def test_verify_template_list_has_scheme(self):
        """
            Add a second list of templates with the same scheme as the first.
            Should throw an exception
        """
        invalid_template_lst = {"name": "Test Template List", "templates": {}}

        self.assertRaises(AttributeError, templates.validate_templates,
                          invalid_template_lst)

    def test_verify_template_list_has_templates(self):
        """
            Ensure that there are agreement terms in the template list
        """
        invalid_template_lst = {"name": "Test Template List", "scheme": "",
                                "templates": {}}

        self.assertRaises(AttributeError, templates.validate_templates,
                          invalid_template_lst)

    def test_verify_template_list_template_has_terms(self):
        """
            Ensure that each template has atleast 1 term
        """
        invalid_template_lst = self.sample_templates.get("no_terms")
        self.assertRaises(AttributeError, templates.validate_templates,
                          invalid_template_lst)

    def test_verify_template_terms_have_metric(self):
        """
            Ensure that each term has atleast 1 metric
        """
        invalid_template_lst = self.sample_templates.get("no_metrics")
        self.assertRaises(AttributeError, templates.validate_templates,
                          invalid_template_lst)

    def test_verify_sla_term_is_in_metric_list(self):
        """
            Checks term metrics against static metrics list
        """
        invalid_template_lst = self.sample_templates.get("unknown_metric")
        self.assertRaises(AttributeError, templates.validate_templates,
                          invalid_template_lst)

    def test_verify_sla_term_value_type_integer_is_a_integer(self):
        """
            checks that a term marked as type integer is an integer
        """
        invalid_template_lst = self.sample_templates.get("not_integer")
        self.assertRaises(AttributeError, templates.validate_templates,
                          invalid_template_lst)

    def test_verify_sla_term_value_type_real_numbr_is_real_numbr(self):
        """
            checks that a term marked as type rational is a rational
        """
        invalid_template_lst = self.sample_templates.get("not_real")
        self.assertRaises(AttributeError, templates.validate_templates,
                          invalid_template_lst)


    def test_verify_sla_term_value_type_string_is_a_string(self):
        """
            Checks that a value defined as a string is a string
        """
        invalid_template_lst = self.sample_templates.get("not_string")
        self.assertRaises(AttributeError, templates.validate_templates,
                          invalid_template_lst)

    def test_sla_term_limits_max(self):
        """
            Check that if a template uses max, that it is the correct type and
            greater than or equal to value
        """
        invalid_template_lst = self.sample_templates.get("max_incorrect_type")
        self.assertRaises(AttributeError, templates.validate_templates,
                          invalid_template_lst)

        value_gt_max_temp = self.sample_templates.get("max_lt_value")
        self.assertRaises(AttributeError, templates.validate_templates,
                          value_gt_max_temp)

    def test_sla_term_limits_min(self):
        """
             Check that if a template uses min, that it is the correct type and
            greater than or equal to value
        """
        incorrect_min_type = self.sample_templates.get("min_incorrect_type")
        self.assertRaises(AttributeError, templates.validate_templates,
                          incorrect_min_type)
        incorrect_min_value = self.sample_templates.get("min_gt_value")
        self.assertRaises(AttributeError, templates.validate_templates,
                          incorrect_min_value)

    def test_sla_term_limit_margin(self):
        """
            Ensure that the margin is between 1 and 100 and is a number
        """
        bad_margin_type = self.sample_templates.get("margin_bad_type")
        self.assertRaises(AttributeError, templates.validate_templates,
                          bad_margin_type)
        bad_margin_value = self.sample_templates.get("margin_bad_value")
        self.assertRaises(AttributeError, templates.validate_templates,
                          bad_margin_value)

    def test_sla_term_limit_enum(self):
        """
            Ensure that the enums are of the string type and that the value is
            a member of the enum list
        """
        bad_enum_container = self.sample_templates.get("bad_enum_container")
        self.assertRaises(AttributeError, templates.validate_templates,
                          bad_enum_container)
        bad_enum_type = self.sample_templates.get("bad_enum_type")
        self.assertRaises(AttributeError, templates.validate_templates,
                          bad_enum_type)
        value_not_enum = self.sample_templates.get("value_not_enum")
        self.assertRaises(AttributeError, templates.validate_templates,
                          value_not_enum)

    def test_string_type_metric_cannot_have_certain_limits(self):
        """
            Make sure that a string type vlaue can only have enum limit
        """
        incorrect_limits = self.sample_templates.get("incorrect_limits")
        self.assertRaises(AttributeError, templates.validate_templates,
                          incorrect_limits)

    def test_enum_validation(self):
        metric = {"name": "OS",
                  "enum": ["WIN", "LINUX"],
                  "value": "Centos"}
        self.assertRaises(AttributeError, templates.validate_enum, "OS", metric)
