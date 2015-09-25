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
  Constructing SLA OCCI API Extension
"""


from registry import PersistentReg
from occi.core_model import Mixin
from wsgi import Application
from pymongo import MongoClient
import occi_sla
import occi_violation
import backends
import violations_backend

DB = MongoClient().sla
NORTH_BND_API = None


def build():
    """
        Construct API as an OCCI Application
    """
    global NORTH_BND_API
    NORTH_BND_API = Application(registry=PersistentReg())

    # Register Agreement
    agreement = backends.Agreement()
    NORTH_BND_API.register_backend(occi_sla.AGREEMENT, agreement)
    NORTH_BND_API.register_backend(occi_sla.ACCEPT_ACTION, agreement)
    NORTH_BND_API.register_backend(occi_sla.REJECT_ACTION, agreement)
    NORTH_BND_API.register_backend(occi_sla.SUSPEND_ACTION, agreement)
    NORTH_BND_API.register_backend(occi_sla.UNSUSPEND_ACTION, agreement)

    # Register Agreement Link
    link_backend = backends.AgreementLink()
    NORTH_BND_API.register_backend(occi_sla.AGREEMENT_LINK, link_backend)

    # Register Agreement Term
    agreement_term = backends.AgreementTerm()
    NORTH_BND_API.register_backend(occi_sla.AGREEMENT_TERM, agreement_term)

    # Register Agreement template
    agreement_template = backends.AgreementTemplate()
    NORTH_BND_API.register_backend(occi_sla.AGREEMENT_TEMPLATE,
                                   agreement_template)

    # Registrer violations
    violation = violations_backend.Violation()
    violation_link = violations_backend.ViolationLink()
    NORTH_BND_API.register_backend(occi_violation.VIOLATION, violation)
    NORTH_BND_API.register_backend(occi_violation.VIOLATION_LINK, violation_link)
    
    # Add Provider templates as mixins
    create_provider_mixins_2(agreement_template)

    # Add Previous resources into the registry
    NORTH_BND_API.registry.populate_resources()

    return NORTH_BND_API


def create_provider_mixins_2(agreement_template):
    """
        For each service provider pull out their template list from the DB and
        add templates and terms as mixins
    """
    mixins = []
    for template_list in DB.templates.find({}):
        add_provider_mixins(template_list, agreement_template)
    return mixins


def add_provider_mixins(template_lst, agreement_template):
    """
        Registers mixins with the OCCI model
    """
    templates, terms = build_template_lst_mixins(template_lst)
    tmp_mixins = templates + terms
    for mixin in tmp_mixins:
        NORTH_BND_API.register_backend(mixin, agreement_template)


def build_template_lst_mixins(template_list):
    """
        Takes a list of templates and returns all template and term mixins
    """
    scheme = str(template_list["scheme"])
    terms_scheme = scheme[:-1] + "/terms#"
    
    temp_mxns = []
    term_mxns = []

    for temp_key, template in template_list["templates"].iteritems():
        related = [occi_sla.AGREEMENT_TEMPLATE]

        for term_key, term in template["terms"].iteritems():
            term_scheme = terms_scheme + term_key
            if term_scheme not in related:
                related.append(term_scheme)
        term_mxns += build_term_mixins2(temp_key, template["terms"], scheme)
        mxn = Mixin(scheme, temp_key, related=related, title=temp_key,
                    attributes={})

        temp_mxns.append(mxn)
    return temp_mxns, flatten(term_mxns)


def flatten(mxns):
    """
        removes any duplicate mixins
    """
    flattened_mxns = []
    for mxn in mxns:
        if mxn not in flattened_mxns:
            flattened_mxns.append(mxn)
    return flattened_mxns


def build_term_mixins(template_terms, scheme):
    """
        Pulls out terms from the template and adds them as mixins
    """
    scheme = scheme[:-1] + "/terms#"
    related = [occi_sla.AGREEMENT_TERM]
    terms = []

    for term_key, term in template_terms.iteritems():
        attrs = {}
        for metric_key in term:
            attrs[str(metric_key)] = "immutable"

        term = Mixin(scheme, term_key, related=related, title=term_key,
                     attributes=attrs)
        terms.append(term)


def build_term_mixins2(template_name, template_terms, scheme):
    """
        Pulls out terms from the template and adds them as mixins for the
        new template format
    """
    scheme = scheme[:-1] + "/terms#"
    related = [occi_sla.AGREEMENT_TERM]
    terms = []

    for term_key, term in template_terms.iteritems():
        attrs = {}

        term_metrics = term['metrics']

        attrs[term_key+'.term.desc'] = "immutable"
        attrs[term_key+'.term.state'] = "immutable"
        attrs[term_key+'.term.type'] = "immutable"
        if 'remedy' in term:
            attrs[term_key+'.term.remedy'] = "immutable"

        for metric_key in term_metrics:
            attrs[str(metric_key)] = "immutable"

        term = Mixin(scheme, term_key, related=related, title=term_key,
                     attributes=attrs)
        terms.append(term)

    return terms
