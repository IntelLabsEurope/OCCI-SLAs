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
    Overloading OCCI registry so that the created agreements can be saved to
    Database
"""

from occi.registry import NonePersistentRegistry
import arrow

from entity_dictionary import EntityDictionary
import occi_sla


class PersistentReg(NonePersistentRegistry):
    """
        Overriding OCCI 'NonePersistentRegistry' so that agreements are saved
        to a database which is defined in EntityDictionary.
    """
    def __init__(self):
        super(PersistentReg, self).__init__()
        self.resources = EntityDictionary(self)

    def add_resource(self, key, resource, extras):
        """
            Adding a resource.
        """
        super(PersistentReg, self).add_resource(key, resource, extras)

    def populate_resources(self):
        """
            Loads agreements from the database on instantiation
        """

        self.resources.populate_from_db()

        return self

    def get_active_agreement_resources(self):
        """
            Loads active agreements from the database on instantiation
        """
        valid_resources = []
        db_resources = self.resources.items()

        for resource_key, resource in db_resources:

            if resource.kind == occi_sla.AGREEMENT:

                if resource.attributes["occi.agreement.state"] == 'accepted':

                    end_t = arrow.get(resource.attributes[
                        "occi.agreement.effectiveUntil"]).timestamp
                    start_t = arrow.get(resource.attributes[
                        "occi.agreement.effectiveFrom"]).timestamp
                    now_a = arrow.utcnow()
                    now_t = now_a.timestamp
                    if start_t < now_t < end_t:
                        valid_resources.append(resource)

        return valid_resources
