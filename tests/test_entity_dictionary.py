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
import unittest
import json
import requests
import sample_data.server
import logging
import tests.sample_data.the_test_data as test_data
from api.entity_dictionary import EntityDictionary
from api import api
from pymongo import errors
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from occi import core_model
import sample_data.sample_mixins
from api import occi_sla
from api import backends

import pdb

LOG = logging.getLogger(__name__)


class AddingToDictionary(unittest.TestCase):
    """
        Tests that check that the entities are being added correctly
    """

    def setUp(self):
        self.db = self._get_db_connection()

    def tearDown(self):
        self.db.entities.remove({})
        pass

    def _get_db_connection(self):
        db_client = MongoClient()
        db = db_client.sla
        return db

    def test_add_resource_to_dictionary(self):
        """
            Test that a resource is being added to the DB
        """
        resources = EntityDictionary(None)
        id = {"_id": "/agreement/4545-4545454-sdasdas"}
        res = core_model.Resource("4777", None, [])
        resources[id["_id"]] = res

        self.assertGreater(self.db.entities.find(id).count(), 0)
        LOG.info("Added dictionary item to db")

    def test_resource_added_to_DB_reflects_resource_sent(self):
        """
            Test to ensure that the correct data is being sent to the DB
        """
        resources = EntityDictionary(None)
        id = {"_id": "/agreement/4545-4545454-sdasdas-blah"}
        res = core_model.Resource("1245", None, [])
        resources[id["_id"]] = res

        self.assertEqual(id["_id"],
                         self.db.entities.find_one({}, {"_id": 1})["_id"])
        LOG.info("Correct entity added to the db")

    def test_add_resource_which_is_already_in_dictionary(self):
        """
            Add a resource with the same ID of a value already in the database
        """
        id = {"_id": "/agreement/4545-4545454-sdasdas-blah"}

        res_0 = core_model.Resource("11235", None, None)
        res_1 = core_model.Resource("18512", None, None)

        resources = EntityDictionary(None)
        resources[id["_id"]] = res_0
        resources[id["_id"]] = res_1

        self.assertEqual(self.db.entities.find().count(), 1)
        self.assertEqual(self.db.entities.find_one(id)["identifier"],
                         res_1.identifier)
        LOG.info("Overwriting existing entry in dict reflected in DB")

    def test_mixins_are_being_added_to_db(self):
        """
            Test that mixins are being added to the DB
        """
        resources = EntityDictionary(None)

        id = {"_id": "/agreement/45454-ghghg53-454545"}
        res = core_model.Resource(id["_id"],
                                  None,
                                  [test_data.epc_mixin, test_data.ran_mixin])
        resources[id["_id"]] = res
        cursor = self.db.entities.find_one(id, {"_id": 0, "mixins": 1})
        mixins = cursor["mixins"]
        self.assertEqual(len(mixins), 2)
        LOG.info("Correct number of mixins added to DB with resource")

    def test_correct_mixins_are_being_added_to_db(self):
        """
            Test that the correct mixin ids are being added to the database.
            Using mixin location as the mixin id.
        """
        resources = EntityDictionary(None)

        id = {"_id": "/agreement/45454-ghghg53-aaees"}
        res = core_model.Resource(id["_id"],
                                  None,
                                  [test_data.epc_mixin, test_data.ran_mixin])
        resources[id["_id"]] = res
        cursor = self.db.entities.find_one(id, {"_id": 0, "mixins": 1})

        self.assertIn(test_data.epc_mixin.location, cursor["mixins"])
        self.assertIn(test_data.ran_mixin.location, cursor["mixins"])
        LOG.info("Correct mixins are being added to the DB")

    def test_correct_resource_links_collection_are_being_added_to_db(self):
        """
            Test if the correct links are being added to the resource record
            in the DB. note: these are links within resources. Not links as
            resources
        """
        # Create resources and Link
        src_res_id = "124816"
        tar_res_id = "112358"
        src_res = core_model.Resource(src_res_id, None, None)
        tar_res = core_model.Resource(tar_res_id, None, None)

        lnk_id = {"_id": "/agreement/add-link-entity"}
        lnk = core_model.Link(lnk_id["_id"], None, None, src_res, tar_res)

        # Load Link      
        resources = EntityDictionary(None)
        resources[lnk_id["_id"]] = lnk

        result_dict = self.db.entities.find_one(lnk_id["_id"])
        self.assertEqual(result_dict["source"], src_res_id)
        self.assertEqual(result_dict["target"], tar_res_id)
        LOG.info("Correct resource links added to the DB")

    def test_add_resource_with_kind(self):
        res_id = "/agreement/adding-resource-kind"
        res = core_model.Resource(res_id, occi_sla.AGREEMENT, None)

        resources = EntityDictionary(None)
        resources[res_id] = res

        result_dict = self.db.entities.find_one(res_id)
        self.assertEqual(result_dict["kind"], occi_sla.AGREEMENT.location)

    def test_add_resource_with_attributes(self):
        res_id = "/agreement/adding-resource-with-agreements"
        res = core_model.Resource(res_id, None, None)

        res_attr = {"the.test.attr": "1", "attr-2": "2", "attr_3": "3",
                    "attr||four": "4"}
        res.attributes = res_attr
        resources = EntityDictionary(None)
        resources[res_id] = res
        persisted_res = self.db.entities.find_one(res_id)
        pstd_res_attrs = persisted_res["attributes"]

        self.assertEqual(pstd_res_attrs["the^test^attr"],
                         res_attr["the.test.attr"])
        self.assertEqual(pstd_res_attrs["attr-2"], res_attr["attr-2"])
        self.assertEqual(pstd_res_attrs["attr_3"], res_attr["attr_3"])


class TestResourceGeneral(unittest.TestCase):
    """
        General tests looking at the resource dictionary from a slighly higher
        level
    """

    def setUp(self):
        self.db = self._get_db_connection()

    def tearDown(self):
        self.db.entities.remove({})

    def _get_db_connection(self):
        db_client = MongoClient()
        db = db_client.sla
        return db

    def test_that_db_reflects_the_in_memory_list(self):
        """
            Create a few resources and links and make sure that the in memory
            (normal) dictionary looks the same as the DB.
        """
        # Create resources and add them

        # Ceate resources with links and mixins and add them

        # Creat resources with actions and add them

        # create links and add them

        # verify that the DB is looking the same as the normal dictionary.
        pass

    def test_retrieve_dictionary_keys(self):
        res_id_1 = "/agreement/delete-resource-dict-using-clear_1"
        res_1 = core_model.Resource(res_id_1, None, None)

        res_id_2 = "/agreement/delete-resource-dict-using-clear_2"
        res_2 = core_model.Resource(res_id_2, None, None)

        resources = EntityDictionary(None)
        resources[res_id_1] = res_1
        resources[res_id_2] = res_2

        s1 = set(resources.keys())
        s2 = {res_id_1, res_id_2}

        self.assertEqual(s1, s2)


class TestResourceFunctionality(unittest.TestCase):
    """
        Ensure that the resource dictionary behaves transparently.
    """

    def setUp(self):
        # self._create_occi_server()
        # self._create_test_resources_on_server()
        self.db = self._get_db_connection()

    def tearDown(self):
        self.db.entities.remove({})
        # self.occi_server.stop()


    def test_retrieve_correct_resource_with_mixins_from_dictionary(self):
        """
            retrieve a resource from the dictionary with the same mixins
        """
        test_resource_id = "/agreement/retrieve-mixins-from-dictionary"
        test_resource = core_model.Resource(test_resource_id, None,
                                            [test_data.epc_mixin])
        registry = api.build().registry
        resources = EntityDictionary(registry)
        resources[test_resource_id] = test_resource

        returned_resource = resources[test_resource_id]

        rtrnd_mxn = returned_resource.mixins[0]

        self.assertEqual(test_resource.mixins[0].location, rtrnd_mxn.location)
        self.assertEqual(test_resource.mixins[0].term, rtrnd_mxn.term)
        self.assertEqual(test_resource.mixins[0].scheme, rtrnd_mxn.scheme)

    def _get_db_connection(self):
        db_client = MongoClient()
        db = db_client.sla
        return db

    def _create_occi_server(self):
        api = api.build()
        occi_server = None
        self.occi_server = server.OcciServer(api=api)
        self.occi_server.start()

    def _create_test_resources_on_server(self):
        req_data = json.load(file('tests/sample_data/rest_requests.json'))

        req_1 = requests.post("http://localhost:8888/agreement/",
                              headers=req_data["agree_std_1"])
        link_1 = req_1.headers["location"]

        req_2 = requests.post("http://localhost:8888/agreement/",
                              headers=req_data["agree_std_2"])
        link_2 = req_2.headers["location"]

        lnk = "<{0}>; category=\"http://schemas.ogf.org/occi/sla#agreement\"\
              ".format(link_1)

        r3_hdrs = req_data["agree_lnk_1"]
        r3_hdrs["Link"] = lnk

        req_3 = requests.post("http://localhost:8888/agreement/",
                              headers=r3_hdrs)


class DeletingFromDictionary(unittest.TestCase):
    """
        Test to ensure that the dictionary delete is working as expoected
    """

    def setUp(self):
        self.db = self._get_db_connection()

    def tearDown(self):
        self.db.entities.remove({})

    def _get_db_connection(self):
        db_client = MongoClient()
        db = db_client.sla
        return db

    def test_delete_entity_from_dictionary_and_DB(self):
        """
            Tests that a delete on the dictionary removes entity from the
            database
        """
        # Create a resource
        id = {"_id": "/agreement/resource-for-deletion"}
        resource = core_model.Resource(id["_id"], None, [])

        entities = EntityDictionary(None)
        entities[id["_id"]] = resource

        # delete the resource

        del entities[id["_id"]]
        db_res = self.db.entities.find_one(id)

        self.assertEqual(db_res, None)
        self.assertEqual(len(entities), 0)

    def test_delete_multiple_entities_from_dictionary(self):
        """
            Delete multiple entities and ensure others not deleted are
            persisted
        """
        res_0 = core_model.Resource("res_0", None, None)
        res_1 = core_model.Resource("res_1", None, None)
        res_2 = core_model.Resource("res_2", None, None)
        res_3 = core_model.Resource("res_3", None, None)
        res_4 = core_model.Resource("res_4", None, None)
        res_5 = core_model.Resource("res_5", None, None)
        lnk_0 = core_model.Link("lnk_0", None, None, res_1, res_5)
        lnk_1 = core_model.Link("lnk_1", None, None, res_1, res_5)

        entities = EntityDictionary(None)
        entities[res_0.identifier] = res_0
        entities[res_1.identifier] = res_1
        entities[res_2.identifier] = res_2
        entities[res_3.identifier] = res_3
        entities[res_4.identifier] = res_4
        entities[res_5.identifier] = res_5
        entities[lnk_0.identifier] = lnk_0
        entities[lnk_1.identifier] = lnk_1

        del entities[res_1.identifier]
        del entities[res_5.identifier]
        del entities[lnk_1.identifier]

        self.assertIsNotNone(self.db.entities.find_one("res_0"))
        self.assertIsNotNone(self.db.entities.find_one("res_2"))
        self.assertIsNotNone(self.db.entities.find_one("res_3"))
        self.assertIsNotNone(self.db.entities.find_one("res_4"))
        self.assertIsNotNone(self.db.entities.find_one("lnk_0"))

        self.assertIsNone(self.db.entities.find_one("res_1"))
        self.assertIsNone(self.db.entities.find_one("res_5"))
        self.assertIsNone(self.db.entities.find_one("lnk_1"))

        self.assertTrue("res_0" in entities)
        self.assertTrue("res_2" in entities)
        self.assertTrue("res_3" in entities)
        self.assertTrue("res_4" in entities)
        self.assertTrue("lnk_0" in entities)

        self.assertFalse("res_1" in entities)
        self.assertFalse("res_5" in entities)
        self.assertFalse("lnk_1" in entities)

    def test_delete_entire_dictionary(self):
        """
            Delete the entire dictionary using "del dict_instance"
        """
        res_0 = core_model.Resource("res_0", None, None)
        res_1 = core_model.Resource("res_1", None, None)
        res_2 = core_model.Resource("res_2", None, None)
        res_3 = core_model.Resource("res_3", None, None)

        entities = EntityDictionary(None)
        entities[res_0.identifier] = res_0
        entities[res_1.identifier] = res_1
        entities[res_2.identifier] = res_2
        entities[res_3.identifier] = res_3

        del entities

        self.assertIsNone(self.db.entities.find_one("res_0"))
        self.assertIsNone(self.db.entities.find_one("res_1"))
        self.assertIsNone(self.db.entities.find_one("res_2"))
        self.assertIsNone(self.db.entities.find_one("res_3"))

    def test_entire_dictionary_using_clear(self):
        res_id_1 = "/agreement/delete-resource-dict-using-clear_1"
        res_1 = core_model.Resource(res_id_1, None, None)

        res_id_2 = "/agreement/delete-resource-dict-using-clear_2"
        res_2 = core_model.Resource(res_id_2, None, None)

        resources = EntityDictionary(None)
        resources[res_id_1] = res_1
        resources[res_id_2] = res_2

        resources.clear()

        db_results = self.db.entities.find({})

        self.assertEqual(len(resources), 0)
        self.assertEqual(db_results.count(), 0)

    def test_delete_using_pop(self):
        res_id_1 = "/agreement/delete-resource-dict-using-clear_1"
        res_1 = core_model.Resource(res_id_1, None, None)

        resources = EntityDictionary(None)
        resources[res_id_1] = res_1

        resources.pop(res_id_1)

        db_results = self.db.entities.find({})

        self.assertEqual(len(resources), 0)
        self.assertEqual(db_results.count(), 0)


class PopulatingDictionaryFromDB(unittest.TestCase):
    """
        These tests are to ensure that agreements in the database are loaded
        into the in memory space as resource objects
    """

    def setUp(self):
        self.db = self._get_db_connection()
        self.api = api.build()
        self.api.register_backend(test_data.epc_mixin, backends.AgreementTemplate())
        self.api.register_backend(test_data.ran_mixin, backends.AgreementTemplate())

    def tearDown(self):
        self.db.entities.remove({})

    def _get_db_connection(self):
        db_client = MongoClient()
        db = db_client.sla
        return db


    def test_populate_dictionary_with_basic_resource_from_DB(self):
        """
            This test retrieves a resource from the resource dictionary
        """
        # Create resource and save to DB
        res_id = "/agreement/load-basic-from-db"
        test_resource = core_model.Resource(res_id, occi_sla.AGREEMENT, None)

        resources = EntityDictionary(self.api.registry)
        # bypass normal resource add so that only the db record exists and not
        # the in memeory dictionary
        resources._persist_resource(res_id, test_resource)

        resources.populate_from_db()

        print test_resource.__dict__
        print resources[res_id].__dict__
        self.assertEqual(len(resources), 1)
        self.assertTrue(isinstance(resources[res_id], core_model.Resource))

    def test_load_resource_with_mixin_type_from_DB(self):
        """
            retrieve a resource from the db with the same mixins
        """
        res_id = "/agreement/load-resource-with-mixin-from-db"
        test_resource = core_model.Resource(res_id, occi_sla.AGREEMENT,
                                            [test_data.epc_mixin])
        resources = EntityDictionary(self.api.registry)

        resources._persist_resource(res_id, test_resource)

        resources.populate_from_db()

        res_mixins = resources[res_id].mixins
        self.assertEqual(len(res_mixins), 1)
        self.assertTrue(isinstance(res_mixins[0], core_model.Mixin))

    def test_load_multiple_resource_with_mixins_from_DB(self):
        """
            retrieve a resource from the dictionary with the same mixins
        """
        res_id = "/agreement/load-mult-mixins-from-db"
        test_resource = core_model.Resource(res_id, None,
                                            [test_data.epc_mixin, test_data.ran_mixin])

        resources = EntityDictionary(self.api.registry)
        resources._persist_resource(res_id, test_resource)

        resources.populate_from_db()

        test_mxn_loc = [mix.location for mix in test_resource.mixins]
        rtrnd_mxn_loc = [mixin.location for mixin in resources[res_id].mixins]

        self.assertEqual(test_mxn_loc.sort(), rtrnd_mxn_loc.sort())

    def test_populate_dictionary_with_basic_link_from_DB(self):
        # Create resources and Link
        src_id = "124816"
        tar_id = "112358"
        src_res = core_model.Resource(src_id, occi_sla.AGREEMENT, None)
        tar_res = core_model.Resource(tar_id, occi_sla.AGREEMENT, None)

        lnk_id = "/agreement/load-link-entity-from-DB"
        lnk = core_model.Link(lnk_id, None, None, src_res, tar_res)

        links = EntityDictionary(self.api.registry)
        links._persist_resource(src_id, src_res)
        links._persist_resource(tar_id, tar_res)
        links._persist_link(lnk_id, lnk)

        links.populate_from_db()

        self.assertEqual(len(links), 3)
        self.assertTrue(isinstance(links[lnk_id], core_model.Link))
        self.assertEqual(links[lnk_id].identifier, lnk_id)
        # Removing assistive field templates for comparison
        temp_src = links[lnk_id].source.__dict__
        temp_trgt = links[lnk_id].target.__dict__
        temp_src.pop('templates')
        temp_trgt.pop('templates')
        self.assertEqual(temp_src, src_res.__dict__)
        self.assertEqual(temp_trgt, tar_res.__dict__)

    def test_populate_dictionary_with_resource_containing_attributes(self):
        res_id = "/agreement/load_resource_w_attributes"
        res = core_model.Resource(res_id, None, None)
        res_attrs = {"the.test.attr": "1", "attr-2": "2", "attr_3": "3",
                     "attr||four": "4"}
        res.attributes = res_attrs

        resources = EntityDictionary(self.api.registry)
        resources._persist_resource(res_id, res)
        resources.populate_from_db()

        self.assertEqual(resources[res_id].attributes, res_attrs)


    def test_populate_dictionary_with_resource_containing_links(self):
        # Test entities - creating a resource with two links
        res_tar_1_id = "/an-id/res_tar_1"
        res_src_1_id = "/an-id/res_src_1"
        lnk_1_id = "/an-id/lnk_1_id"
        res_tar_2_id = "/an-id/res_tar_2"
        res_src_2_id = "/an-id/res_src_2"
        lnk_2_id = "/an-id/lnk_2_id"
        res_m_id = "/an-id/res_m"

        res_src_1 = core_model.Resource(res_src_1_id, occi_sla.AGREEMENT, None)
        res_tar_1 = core_model.Resource(res_tar_1_id, occi_sla.AGREEMENT, None)
        lnk_1 = core_model.Link(lnk_1_id, occi_sla.AGREEMENT_LINK, None, res_src_1, res_tar_1)
        res_src_2 = core_model.Resource(res_src_2_id, occi_sla.AGREEMENT, None)
        res_tar_2 = core_model.Resource(res_tar_2_id, occi_sla.AGREEMENT, None)
        lnk_2 = core_model.Link(lnk_2_id, occi_sla.AGREEMENT_LINK, None, res_src_2, res_tar_2)
        res_m = core_model.Resource(res_m_id, occi_sla.AGREEMENT, None, [lnk_1, lnk_2])

        # Persist all to DB but not dict in memory
        entities = EntityDictionary(self.api.registry)
        entities._persist_link(lnk_1_id, lnk_1)
        entities._persist_link(lnk_2_id, lnk_2)
        entities._persist_resource(res_src_1_id, res_src_1)
        entities._persist_resource(res_tar_1_id, res_tar_1)
        entities._persist_resource(res_src_2_id, res_src_2)
        entities._persist_resource(res_tar_2_id, res_tar_2)
        entities._persist_resource(res_m_id, res_m)

        entities.populate_from_db()

        self.assertEqual(len(entities), 7)
        self.assertEqual(len(entities[res_m_id].links), 2)

        for link in entities[res_m_id].links:
            if link.identifier == lnk_1_id:
                # Removing assistive field templates for comparison
                temp_src = link.source.__dict__
                temp_trgt = link.target.__dict__
                temp_src.pop('templates')
                temp_trgt.pop('templates')
                self.assertEqual(temp_src, res_src_1.__dict__)
                self.assertEqual(temp_trgt, res_tar_1.__dict__)
            else:
                # Removing assistive field templates for comparison
                temp_src = link.source.__dict__
                temp_trgt = link.target.__dict__
                temp_src.pop('templates')
                temp_trgt.pop('templates')
                self.assertEqual(temp_src, res_src_2.__dict__)
                self.assertEqual(temp_trgt, res_tar_2.__dict__)
