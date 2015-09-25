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
  Backends for SLA violations
"""

from occi.backend import ActionBackend, KindBackend, MixinBackend
from pymongo import MongoClient
from api import occi_sla
import logging
import arrow
import copy
import api

DB = MongoClient().sla
LOG = logging.getLogger(__name__)

class Violation(KindBackend, ActionBackend):
    """Backend for OCCI violation"""

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)

    def create(self, entity, extras):
        # Validate
        self.verify_provider(extras)
        self.validate(entity)

        # Init Agreement
        entity.provider = self._get_provider(extras)
        entity.customer = self.get_customer(extras)
        now_iso = arrow.utcnow().isoformat()
        entity.attributes["occi.violation.timestamp"] = now_iso

    def retrieve(self, entity, extras):
        if not self._correct_provider(entity, extras):
            raise AttributeError("Provider Denied")

    def update(self, old, new, extras):
        """
            Only allow updates for agreement duration
        """
        pass

    def delete(self, entity, extras):
        if not self._correct_provider(entity, extras):
            raise AttributeError("Provider Denied")

    def action(self, entity, action, attributes, extras):
        """
            Changes the state of the agreement
        """
        if not self._correct_provider(entity, extras):
            raise AttributeError("Provider Denied")

    def validate(self, entity):
        """
            Validate entity on creation
        """
        if self._immutable_attribute(entity):
            raise AttributeError("Cannot change immutable attributes")

    def verify_provider(self, extras):
        """
            Check the provider ID and pass against registered providers
        """
        if self._extras_valid(extras, False):
            provider = extras["security"]
            user, pword = provider.items()[0]
            cred = DB.providers.find_one({"username": user, "password": pword})
            if not cred:
                raise AttributeError("Incorrect Provider Credentials")
        else:
            raise AttributeError("Malformed Provider Credentials")

    @classmethod
    def _immutable_attribute(cls, entity):
        """
            Returns True if any attribute is immutable
        """
        for attr_k in entity.attributes:
            if (attr_k in entity.kind.attributes and
                        entity.kind.attributes[attr_k] == "immutable"):
                return True
            else:
                for mixin in entity.mixins:
                    if attr_k in mixin.attributes:
                        if mixin.attributes[attr_k] == "immutable":
                            return True
                        else:
                            break  # no need to keep searching for attribute
        return False

    def _correct_provider(self, entity, extras):
        """
            Returns true if the entity provider and extras provider match
        """
        self.verify_provider(extras)
        provider = self._get_provider(extras)

        if entity.provider == provider:
            return True
        return False

    @classmethod
    def _get_provider(cls, extras):
        """
            returns the provider id and password from extras
        """
        provider = extras["security"].items()[0][0]
        return provider

    def get_customer(self, extras):
        """
            Returns a customer ID if available
        """
        if self._extras_valid(extras, True):
            return extras["customer"]
        else:
            raise AttributeError("Customer Id Malformed")

    @classmethod
    def _extras_valid(cls, extras, customer):
        """
            Validates if the extras dictionary is valid.
        """
        if extras is None or "security" not in extras or \
                        type(extras["security"]) != dict or len(extras["security"]) == 0:
            return False
        if customer:
            if "customer" not in extras or \
                    not isinstance(extras["customer"], basestring):
                return False
        return True

class ViolationLink(KindBackend):
    """
    Backend for OCCI Violation link
    """

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)

    def create(self, entity, extras):

        Violation().verify_provider(extras)

        Violation().get_customer(extras)

        agreement_id = entity.attributes['occi.core.source']
        target_id = entity.attributes['occi.core.target']

        if target_id == '':
            raise AttributeError('Target endpoint is empty!')

        link_id = entity.identifier

        db_agreements = DB.entities.find({'_id': agreement_id})
        if db_agreements.count() > 0:
            for agreement in db_agreements:
                if agreement['kind'] == '/agreement/' and link_id \
                        not in agreement['links']:
                    agreement['links'].append(link_id)
                    DB.entities.update({'_id': agreement_id}, agreement)

        # Init Agreement
        entity.provider = Violation()._get_provider(extras)
        entity.customer = Violation().get_customer(extras)

    def retrieve(self, entity, extras):
        if not self._correct_provider(entity, extras):
            raise AttributeError("Provider Denied")

    def delete(self, entity, extras):
        if not self._correct_provider(entity, extras):
            raise AttributeError("Provider Denied")

        agreement_id = entity.attributes['occi.core.source']
        link_id = entity.identifier

        db_agreements = DB.entities.find({'_id': agreement_id})
        if db_agreements.count() > 0:
            for agreement in db_agreements:
                if agreement['kind'] == '/agreement/' and link_id \
                        in agreement['links']:
                    agreement['links'].remove(link_id)
                    DB.entities.update({'_id': agreement_id}, agreement)

    def verify_provider(self, extras):
        """
            Check the provider ID and pass against registered providers
        """
        if self._extras_valid(extras, False):
            provider = extras["security"]
            user, pword = provider.items()[0]
            cred = DB.providers.find_one({"username": user, "password": pword})
            if not cred:
                raise AttributeError("Incorrect Provider Credentials")
        else:
            raise AttributeError("Malformed Provider Credentials")

    @classmethod
    def _immutable_attribute(cls, entity):
        """
            Returns True if any attribute is immutable
        """
        for attr_k in entity.attributes:
            if (attr_k in entity.kind.attributes and
                        entity.kind.attributes[attr_k] == "immutable"):
                return True
            else:
                for mixin in entity.mixins:
                    if attr_k in mixin.attributes:
                        if mixin.attributes[attr_k] == "immutable":
                            return True
                        else:
                            break  # no need to keep searching for attribute
        return False

    def _correct_provider(self, entity, extras):
        """
            Returns true if the entity provider and extras provider match
        """
        self.verify_provider(extras)
        provider = self._get_provider(extras)

        if entity.provider == provider:
            return True
        return False

    @classmethod
    def _get_provider(cls, extras):
        """
            returns the provider id and password from extras
        """
        provider = extras["security"].items()[0][0]
        return provider

    def get_customer(self, extras):
        """
            Returns a customer ID if available
        """
        if self._extras_valid(extras, True):
            return extras["customer"]
        else:
            raise AttributeError("Customer Id Malformed")

    @classmethod
    def _extras_valid(cls, extras, customer):
        """
            Validates if the extras dictionary is valid.
        """
        if extras is None or "security" not in extras or \
                        type(extras["security"]) != dict or len(extras["security"]) == 0:
            return False
        if customer:
            if "customer" not in extras or \
                    not isinstance(extras["customer"], basestring):
                return False
        return True
