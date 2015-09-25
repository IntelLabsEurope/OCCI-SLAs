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
OCCI model extensions for OCCI SLA.
"""

from occi.core_model import Kind
from occi.core_model import Link
from occi.core_model import Mixin
from occi.core_model import Action
from occi.core_model import Resource

#  Agreement Definition
# ************************************

ACCEPT_ACTION = Action(scheme="http://schemas.ogf.org/occi/sla#",
                       term="accept",
                       title="Accept an agreement offer")

REJECT_ACTION = Action(scheme="http://schemas.ogf.org/occi/sla#",
                       term="reject",
                       title="Reject an agreement offer")

SUSPEND_ACTION = Action(scheme="http://schemas.ogf.org/occi/sla#",
                        term="suspend",
                        title="Suspend suspend an agreement")

UNSUSPEND_ACTION = Action(scheme="http://schemas.ogf.org/occi/sla#",
                          term="unsuspend",
                          title="Unsuspend a suspened agreement")

AGREEMENT = Kind(scheme="http://schemas.ogf.org/occi/sla#",
                 term="agreement",
                 title="SLA Agreement",
                 attributes={"occi.agreement.state": "immutable",
                             "occi.agreement.agreedAt": "immutable",
                             "occi.agreement.effectiveFrom": "mutable",
                             "occi.agreement.effectiveUntil": "mutable"},
                 actions=[ACCEPT_ACTION,
                          REJECT_ACTION,
                          SUSPEND_ACTION,
                          UNSUSPEND_ACTION],
                 related=[Resource.kind],
                 location="/agreement/")

#  Agreement Link Definition
# ************************************

AGREEMENT_LINK = Kind(scheme="http://schemas.ogf.org/occi/sla#",
                      term="agreement_link",
                      title="SLA Agreement Link",
                      related=[Link.kind],
                      location="/agreement_link/")

#  Agreement Term Definition
# ************************************

AGREEMENT_TERM = Mixin(scheme="http://schemas.ogf.org/occi/sla#",
                       term="agreement_term",
                       title="Agreement Term",
                       attributes={},
                       location="/agreement_term/")

#  Agreement Template  Definition
# ************************************

AGREEMENT_TEMPLATE = Mixin(scheme="http://schemas.ogf.org/occi/sla#",
                           term="agreement_tpl",
                           title="Agreement Template",
                           location="/agreement_tpl/")
