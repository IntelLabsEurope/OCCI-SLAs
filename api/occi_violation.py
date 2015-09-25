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
OCCI model vioaltion entities for the MCN project. 
"""

from occi.core_model import Kind
from occi.core_model import Link
from occi.core_model import Mixin
from occi.core_model import Action
from occi.core_model import Resource

#  Violation defintiion
# ************************************

VIOLATION = Kind(scheme="http://schemas.ogf.org/occi/sla#",
                 term="violation",
                 title="SLA Agreement violation",
                 attributes={"occi.violation.timestamp.start": "immutable",
                             "occi.violation.term": "immutable",
                             "occi.violation.metrics": "immutable",
                             "occi.violation.device": "immutable",
                             "occi.violation.remedy": "immutable"},
                 actions=[],
                 related=[Resource.kind],
                 location="/violation/")

#  Agreement Violation Link Definition
# ************************************

VIOLATION_LINK = Kind(scheme="http://schemas.ogf.org/occi/sla#",
                      term="violation_link",
                      title="SLA Violation Link",
                      related=[Link.kind],
                      location="/violation_link/")

