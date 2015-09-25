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
from occi.core_model import Kind
from occi.core_model import Link
from occi.core_model import Mixin
from occi.core_model import Action
from occi.core_model import Resource
from api import occi_sla
from occi.core_model import Mixin
# **************************** test_backends *********************************

# m1 & m2 are used in test_attributes_belong_to_agreement_or_mixin
# These mixins just need to have attributes

m1 = Mixin("", "", attributes={"uptime":"mutable","cpu_load":"mutable"})
m2 = Mixin("", "", attributes={"filtering":"immutable",
                             "location":"mutable",
                             "thru_put":"mutable"})
m3 = Mixin("", "", attributes={"os": "mutable","vm_cores": "required",
                    "memory": "required" })


# Complete Mixins

epc_mixin = Mixin("http://www.ran_epc_sp.org/templates#",
                          "epc",
                          related=[occi_sla.AGREEMENT_TEMPLATE],
                          title="EPC SLA Template",
                          attributes={"epc.occi.SLO_A": "immutable",
                                      "epc.occi.SLO_B": "required",
                                      "epc.occi.SLO_K": "required"})

ran_mixin = Mixin("http://www.ran_epc_sp.org/templates#",
                          "ran",
                          related=[occi_sla.AGREEMENT_TEMPLATE],
                          title="RAN SLA Template",
                          attributes={"ran.occi.SLO_1": "required",
                                      "ran.occi.SLO_2": "immutable",
                                      "ran.occi.SLO_3": '',
                                      "ran.occi.SLO_4": ''})
