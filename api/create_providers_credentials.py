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
from pymongo import MongoClient

DB = MongoClient().sla


def load_providers():
    """
        Loads some sample provider credentials into the database
    """
    provider_1 = {"username": "DSS",
                  "password": "dss_pass"}
    provider_2 = {"username": "IMS",
                  "password": "ims_pass"}
    provider_3 = {"username": "EPC",
                  "password": "epc_pass"}
    provider_4 = {"username": "RAN",
                  "password": "ran_pass"}

    DB.providers.update({"username": "DSS"}, provider_1, upsert=True)
    DB.providers.update({"username": "IMS"}, provider_2, upsert=True)
    DB.providers.update({"username": "EPC"}, provider_3, upsert=True)
    DB.providers.update({"username": "RAN"}, provider_4, upsert=True)

if __name__ == '__main__':
    load_providers()
