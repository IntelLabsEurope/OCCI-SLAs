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
from occi.core_model import Mixin
from api import occi_sla

m1 = Mixin("http://www.ran_epc_sp.org/templates#",
                          "epc",
                          related=[occi_sla.AGREEMENT_TEMPLATE],
                          title="EPC SLA Template",
                          attributes={"epc.occi.SLO_A": "immutable",
                                      "epc.occi.SLO_B": "required",
                                      "epc.occi.SLO_K": "required"})

m2 = Mixin("http://www.ran_epc_sp.org/templates#",
                          "ran",
                          related=[occi_sla.AGREEMENT_TEMPLATE],
                          title="RAN SLA Template",
                          attributes={"ran.occi.SLO_1": "required",
                                      "ran.occi.SLO_2": "immutable",
                                      "ran.occi.SLO_3": '',
                                      "ran.occi.SLO_4": ''})
