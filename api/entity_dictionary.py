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
Entity Dictionary adds a persistence layer to a normal dictionary, tailored to
store occi core model entities.
"""

import copy

from pymongo import MongoClient
from occi import core_model
import occi_sla


class EntityDictionary(dict):
    """
        Dictionary for registry resources. Saves entities in the db and into
        a normal dictionary.

        Allows seamless use of a dictionary for entities
        which manages the serialisation of objects to and from the database and
        maintaing consistency with the in-memry (normal) dictionary.

        Esentially adds a persistence layer to a normal dictionary, tailored to
        occi core model entities.
    """

    def __init__(self, registry, host=None, port=None):
        super(EntityDictionary, self).__init__()

        # Get the Database collection
        client = MongoClient(host, port)
        sla_db = client.sla
        self.entities = sla_db.entities

        # Registry needed to determine mixin types
        self.registry = registry

    def __setitem__(self, key, val):
        """
            Stores the entity as both an in-memory dictionary and db record.
        """
        if isinstance(val, core_model.Resource):
            self._persist_resource(key, val)
        else:
            self._persist_link(key, val)

        super(EntityDictionary, self).__setitem__(key, val)

    def __delitem__(self, key):
        """
            Removes the in-memory dictionary and the db record
        """
        self.entities.remove(key)
        super(EntityDictionary, self).__delitem__(key)

    def __del__(self):
        """
            clears the database if the object is deleted.
        """
        self.entities.remove({})

    def _get_mixins(self, entity):
        """
            Returns a list of mixin objects from a list of mixin locations.
        """
        entity = copy.deepcopy(entity)
        mixins = []
        if entity.mixins is not None:
            for mxn_loc in entity.mixins:
                mxn = self.registry.get_category(mxn_loc, None)
                mixins.append(mxn)

        if not mixins == []:
            entity.mixins = mixins

        return entity.mixins

    def clear(self):
        """
            Overide clear to delete all db records.
        """
        self.entities.remove({})
        super(EntityDictionary, self).clear()

    def pop(self, key):
        self.entities.remove(key)
        super(EntityDictionary, self).pop(key)

    @staticmethod
    def _encode_attributes(attributes):
        """
            Modifys the attributes from an entity so that they can be stored in
            a database.  (This was neccasary as mongodb was disallowing key
            names that used a '.')
        """
        attrs_d = {}
        for a_key, a_val in attributes.iteritems():
            a_key = a_key.replace(".", "^")
            attrs_d[a_key] = str(a_val)
        attributes = attrs_d
        return attributes

    @staticmethod
    def _decode_attributes(attributes):
        """
            Translate the attributes from DB representation to a representation
            that can be used with the OCCI PYSSF package.
        """
        attrs_d = {}
        for a_key, a_val in attributes.iteritems():
            a_key = a_key.replace("^", ".")
            attrs_d[a_key] = a_val
        attributes = attrs_d
        return attributes

    def _add_resource(self, entity_record, add_link=True):
        """
            Takes a dictionary representation of a resource and generates a
            resource object and adds to the dictionary data structure.
        """
        key = entity_record["_id"]

        del entity_record["_id"]
        entity = core_model.Resource("", None, None)
        entity.__dict__ = entity_record

        entity.kind = self.registry.get_category(entity.kind, None)

        entity.mixins = self._get_mixins(entity)

        links = []

        if entity.links is not None and add_link:
            for link_id in entity.links:
                link_record = self.entities.find_one(link_id)
                self._add_link(link_record)
                links.append(self[link_id])

        # if links is not []:
        if len(links) > 0:
            entity.links = links

        entity.attributes = self._decode_attributes(entity.attributes)
        super(EntityDictionary, self).__setitem__(key, entity)

    def _add_link(self, entity_record):
        """
            Takes a dictionary representation of a link and generates a Link
            Object to the dictionary data structure.  Will automatically add
            source and target objects and their dependencies to the collection
            if they are not already there.
        """
        key = entity_record["_id"]
        del entity_record["_id"]

        entity = core_model.Link(None, None, None, None, None)
        entity.__dict__ = entity_record
        entity.kind = self.registry.get_category(entity.kind, None)

        entity.mixins = self._get_mixins(entity)

        if entity.source not in self:
            source_rec = self.entities.find_one(entity.source)
            self._add_resource(source_rec, False)

        entity.source = self.__getitem__(entity.source)

        if entity.target not in self:
            target_rec = self.entities.find_one(entity.target)
            if target_rec:
                self._add_resource(target_rec, False)
                entity.target = self.__getitem__(entity.target)

        else:
            entity.target = self.__getitem__(entity.target)

        entity.attributes = self._decode_attributes(entity.attributes)
        super(EntityDictionary, self).__setitem__(key, entity)

    @staticmethod
    def is_link(entity_record):
        """
            Returns true if the record has the structure of an OCCI Link,
            otherwise returns false
        """
        return "source" in entity_record

    def populate_from_db(self):
        """
            Populate the dictionary data structure from the entities
            in the database.
        """
        entity_records = self.entities.find({})

        entity_records = self.sort_records(entity_records)

        for entity_record in entity_records:
            entity_record = self._clean_dictionary(entity_record)

            if entity_record["_id"] not in self:

                if self.is_link(entity_record):
                    self._add_link(entity_record)
                else:
                    self._add_resource(entity_record)

    def get_resources_from_db(self):
        """
            Populate the dictionary data structure from the entities
            in the database and return it.
        """
        entity_records = self.entities.find({})

        for entity_record in entity_records:
            entity_record = self._clean_dictionary(entity_record)

            if self.is_link(entity_record):
                self._add_link(entity_record)
            else:
                self._add_resource(entity_record)

        return self.items()

    def sort_records(self, records):
        """
            Sort the records from teh db. First the resources then the links.
        """
        sorted_list = []
        for record in records:
            if self.is_link(record):
                sorted_list.append(record)
            else:
                sorted_list.insert(0, record)
        return sorted_list

    def _persist_link(self, key, link):
        """
            Prepare a link entity and save to the database.
        """
        entity = copy.deepcopy(link.__dict__)  # to localise dict manipulation
        entity["_id"] = key

        self._flatten_kind(entity)
        self._flatten_mixin(entity)
        entity["source"] = link.source.identifier
        if isinstance(link.target, core_model.Resource):
            entity["target"] = link.target.identifier
        else:
            entity["target"] = link.target

        entity["attributes"] = self._encode_attributes(entity["attributes"])
        self._persist_entity(entity, key)

    def _persist_resource(self, key, resource):
        """
            Prepare a resource entity and save to the database.
        """
        entity = copy.deepcopy(resource.__dict__)  # to localise dict
        entity["_id"] = key
        
        # templates entry in resource prep
        templates = []
 
        if resource.mixins:
            for mixin in resource.mixins:
                if occi_sla.AGREEMENT_TEMPLATE in mixin.related:
                    templates.append(mixin.scheme + mixin.term)
        
        entity["templates"] = templates

        self._flatten_kind(entity)
        self._flatten_mixin(entity)  # by ref
        self._flatten_links(entity)
        entity["attributes"] = self._encode_attributes(entity["attributes"])
        self._persist_entity(entity, key)

    def _persist_entity(self, entity, key):
        """
            Saves an occi core model entity (Resource, Link) to the database.
        """
        if self.entities.find({"_id": key}).count() == 0:
            self.entities.insert(entity)
        else:
            self.entities.update({"_id": key}, entity)

    @staticmethod
    def _flatten_kind(entity):
        """
            Flattens "Kind" classes for storage in the database
        """
        if entity["kind"] is not None:
            entity["kind"] = entity["kind"].location

    @staticmethod
    def _flatten_mixin(entity):
        """
            Removes mixin objects in a resources mixins list and replaces it
            with the mixin identifier so that it can be saved to the DB
        """
        mixins = []
        if entity["mixins"] is not None:
            for mixin in entity["mixins"]:
                mixins.append(mixin.location)
        # only checking this to keep db consistent with obj
        if not mixins == []:
            entity["mixins"] = mixins

    @staticmethod
    def _flatten_links(entity):
        """
            Removes link objects in a resources links list and replaces it
            with the link identifier so that it can be saved to the DB
        """

        linked_resources = []
        if entity["links"] is not None:
            for linked_resource in entity["links"]:
                if isinstance(linked_resource, core_model.Link):
                    linked_resources.append(linked_resource.identifier)
        # check this to keep db consistent with obj
        if not linked_resources == []:
            entity["links"] = linked_resources

    @classmethod
    def _clean_dictionary(cls, entity_dict):
        """
            Removes unicode strings from the dictionary.
        """
        if isinstance(entity_dict, dict):
            return {cls._clean_dictionary(key): cls._clean_dictionary(value)
                    for key, value in entity_dict.iteritems()}
        elif isinstance(entity_dict, list):
            return [cls._clean_dictionary(element) for element in entity_dict]
        elif isinstance(entity_dict, unicode):
            return str(entity_dict)
        else:
            return entity_dict
