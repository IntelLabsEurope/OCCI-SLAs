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
"""
  Backends for SLA OCCI Extensions
"""

from occi.backend import ActionBackend, KindBackend, MixinBackend
from pymongo import MongoClient
from api import occi_sla
import logging
import arrow
import copy
import api

DB = MongoClient().sla


class Agreement(KindBackend, ActionBackend):
    """Backend for OCCI SLA Agreement extension"""

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)

    def create(self, entity, extras):
        # Validate
        self.verify_provider(extras)
        self.validate(entity)

        # Init Agreement
        entity.provider = self._get_provider(extras)
        entity.customer = self.get_customer(extras)
        entity.attributes["occi.agreement.state"] = "pending"
        self._format_contract_time(entity.attributes)

        # Add term mixins and attributes to the entity
        mxns = []
        attrs = {}
        for mxn in entity.mixins:
            if occi_sla.AGREEMENT_TEMPLATE in mxn.related:
                for tmp_lst in DB.templates.find({}):
                    if mxn.scheme == tmp_lst["scheme"] \
                            and mxn.term in tmp_lst["templates"]:
                        template = tmp_lst["templates"][mxn.term]['terms']

                        for term_name in template:
                            mxns.append(self._get_term(term_name))
                            attrs.update(self._get_term_metrics
                                         (mxn.term, template, term_name))
                            # ToDo check in needed
                            # attrs.update(self._get_term_type_attrs(
                            # term_name))

                        break
        entity.mixins.extend(mxns)
        entity.attributes.update(attrs)

    def retrieve(self, entity, extras):
        if not self._correct_provider(entity, extras):
            raise AttributeError("Provider Denied")

    def update(self, old, new, extras):
        """
            Only allow updates for agreement duration
        """
        if not self._correct_provider(old, extras):
            raise AttributeError("Provider Denied")

        if ("occi.agreement.effectiveFrom" in new.attributes or
                    "occi.agreement.effectiveUntil" in new.attributes) and \
                        old.attributes["occi.agreement.state"] == "pending":
            self._update_agreement_duration(old, new)

    def delete(self, entity, extras):
        if not self._correct_provider(entity, extras):
            raise AttributeError("Provider Denied")

    def action(self, entity, action, attributes, extras):
        """
            Changes the state of the agreement
        """
        if not self._correct_provider(entity, extras):
            raise AttributeError("Provider Denied")

        if action == occi_sla.ACCEPT_ACTION:
            if not self._agreement_expired(entity):
                self._set_state(entity, "accepted", "pending")
                now_iso = arrow.utcnow().isoformat()
                entity.attributes["occi.agreement.agreedAt"] = now_iso
            else:
                raise AttributeError("Expired. re-negotiate duration")
        elif action == occi_sla.REJECT_ACTION:
            self._set_state(entity, "rejected", "pending")
        elif action == occi_sla.SUSPEND_ACTION:
            self._set_state(entity, "suspended", "accepted")
        elif action == occi_sla.UNSUSPEND_ACTION:
            self._set_state(entity, "accepted", "suspended")

    @classmethod
    def _get_template_attributes(cls, template, template_name):
        """
            Runs through a template and extracts all the attributes from the
            terms
        """
        attributes = {}
        for term_name, term in template['terms'].iteritems():
            for metric in term['metrics']:
                key = template_name + "." + term_name + "." + metric
                attributes[key] = term['metrics'][metric]['value']
        return attributes

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

    @classmethod
    def _unrecognised_attribute(cls, entity):
        """
            Returns True if an attribute is not belonging to the agreement
            or a mixin
        """
        posted_attributes = copy.deepcopy(entity.attributes)
        # check agreement attributes
        for a_attr_k in entity.kind.attributes:
            if a_attr_k in posted_attributes:
                del posted_attributes[a_attr_k]

        # check mixin types
        for mixin in entity.mixins:
            for m_attr_k in mixin.attributes:
                if m_attr_k in posted_attributes:
                    del posted_attributes[m_attr_k]

        if len(posted_attributes) > 0:
            return True
        return False

    @classmethod
    def _required_attr_missing(cls, entity):
        """
            Checks whether the agreement or mixin has required attributes
            which are not part of the request.
        """
        # loop agreement attribute schema
        for attr_key, attr_val in entity.kind.attributes.iteritems():
            if attr_val.strip() == "required":
                if attr_key not in entity.attributes:
                    return True

        # loop mixins attribute schema
        for mixin_inst in entity.mixins:
            for m_attr_key, m_attr_val in mixin_inst.attributes.iteritems():
                if m_attr_val.strip() == "required":
                    if m_attr_key not in entity.attributes:
                        return True

        return False

    @classmethod
    def _has_bad_num_of_prvder_mxns(cls, mixins):
        """
            returns true if there are more or less than 1 provider mixin
        """
        pro_mxn_cnt = 0
        for mixin in mixins:
            for tmp_lst in DB.templates.find():
                if tmp_lst["scheme"] == mixin.scheme:
                    if mixin.term in tmp_lst["templates"]:
                        pro_mxn_cnt += 1

        if pro_mxn_cnt != 1:
            return True
        else:
            return False

    @classmethod
    def _agreement_expired(cls, entity):
        """
            Returns True if agreement has expired
        """
        closing_s = entity.attributes["occi.agreement.effectiveUntil"]
        closing_t = arrow.get(closing_s).timestamp
        now_a = arrow.utcnow()
        now_t = now_a.timestamp
        return now_t > closing_t

    @classmethod
    def _get_term(cls, name):
        """
            Returns a term mixin matchin the name (term) from the registry
        """
        location = "{1}{0}{1}".format(name, "/")
        return api.NORTH_BND_API.registry.get_category(location, None)

    @classmethod
    def _get_term_metrics(cls, template_name, template, term):
        """
            Extracts the metrics and their values from the terms
        """
        attrs = {}

        term_metrics = template[term]['metrics']
        term_type = template[term]['type']
        term_state_key = "{}.term.state".format(term)
        type_key = "{}.term.type".format(term)
        term_desc = template[term]['desc']
        desc_key = "{}.term.desc".format(term)

        attrs[desc_key] = term_desc
        attrs[type_key] = term_type
        attrs[term_state_key] = 'undefined'  # Initialization of term state

        for metric in term_metrics:
            key = "{}.{}.{}".format(template_name, term, metric)

            attrs[key] = term_metrics[metric]['value']
            if term_type == 'SLO-TERM':
                key = "{}.{}.{}.{}".format(
                    template_name, term, metric, 'limiter_type'
                )
                attrs[key] = term_metrics[metric]['limiter_type']
                if term_metrics[metric]['limiter_type'] == 'margin':
                    key = "{}.{}.{}.{}".format(
                        template_name, term, metric, 'limiter_value')
                    attrs[key] = term_metrics[metric]['limiter_value']

                if 'remedy' in template[term]:
                    term_remedy = template[term]['remedy']
                    key = "{}.{}.{}".format(term, 'term', 'remedy')
                    attrs[key] = term_remedy

        return attrs

    @classmethod
    def _get_term_type_attrs(cls, term):
        """
            Adds the standard SLA term type attributes for the agreement
        """
        type_key = "{}.term.type".format(term)
        state_key = "{}.term.state".format(term)
        desc_key = "{}.term.desc".format(term)

        return {type_key: "SLO", state_key: "undefined", desc_key: ""}

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
    def _bad_contract_period(cls, attributes):
        """
            Returns True if 'occi.agreement.effectiveFrom"\' and
            'occi.agreement.effectiveUntil' date range is correct. Using
            datetime.timedelta()
        """
        if "occi.agreement.effectiveFrom" in attributes and \
                        "occi.agreement.effectiveUntil" in attributes:
            try:
                from_t = arrow.get(attributes["occi.agreement.effectiveFrom"])
                untl_t = arrow.get(attributes["occi.agreement.effectiveUntil"])
                delta = from_t - untl_t
                if delta.days < 0:
                    return False  # Period Good
            except BaseException:
                return True
        return True

    def validate(self, entity):
        """
            Validate entity on creation
        """
        if self._immutable_attribute(entity):
            raise AttributeError("Cannot change immutable attributes")
        if self._unrecognised_attribute(entity):
            raise AttributeError("Unrecognised attribute. Review attributes")
        if self._required_attr_missing(entity):
            raise AttributeError("Required attributes missing")
        if len(entity.mixins) == 0:
            raise AttributeError("SLA Template Required")
            # ToDo: Fix provider validation
            # Allow more than one mixins from the same provider
            # for multiple templates to be inserted.
            # if self._has_bad_num_of_prvder_mxns(entity.mixins):
            # raise AttributeError("Agreement takes exactly 1 provider template")
        if self._bad_contract_period(entity.attributes):
            raise AttributeError("Contract duration required. ISO 8601 format")

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
    def _format_contract_time(cls, attributes):
        """
            Format user input for time into one form of ISO 8601
        """
        from_t = arrow.get(attributes["occi.agreement.effectiveFrom"])
        until_t = arrow.get(attributes["occi.agreement.effectiveUntil"])
        attributes["occi.agreement.effectiveFrom"] = from_t.isoformat()
        attributes["occi.agreement.effectiveUntil"] = until_t.isoformat()

    def _update_agreement_duration(self, old, new):
        """
            update occi.agreement.effectiveFrom & occi.agreement.effectiveUntil
            attributes
        """
        attrs = {}
        from_s = "occi.agreement.effectiveFrom"
        until_s = "occi.agreement.effectiveUntil"

        if from_s in new.attributes:
            attrs[from_s] = new.attributes[from_s]
        else:
            attrs[from_s] = old.attributes[from_s]

        if until_s in new.attributes:
            attrs[until_s] = new.attributes[until_s]
        else:
            attrs[until_s] = old.attributes[until_s]

        if self._bad_contract_period(attrs):
            raise AttributeError("Contract duration required. ISO 8601 format")

        old.attributes.update(attrs)
        self._format_contract_time(old.attributes)

    @classmethod
    def _set_state(cls, entity, new, required):
        """
            sets the state of the entity, depending on the required state
        """
        state = "occi.agreement.state"
        if entity.attributes[state] == required:
            entity.attributes[state] = new
        else:
            raise AttributeError("Action ignored")


class AgreementLink(KindBackend):
    """
    Backend for OCCI SLA Agreement extension
    """

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)

    def create(self, entity, extras):
        # Validate Source AgreementLink

        Agreement().verify_provider(extras)

        # ToDo: validation needs to be corrected. 'Cannot change immutable
        # attributes' error NOT when only one immutable attribute appears.
        # Agreement().validate(entity.source)
        Agreement().get_customer(extras)

        agreement_id = entity.attributes['occi.core.source']
        target_id = entity.attributes['occi.core.target']

        if target_id == '':
            raise AttributeError('Target endpoint is empty!')

        link_id = entity.identifier

        db_agreements = DB.entities.find({'_id': agreement_id})
        if db_agreements.count() > 0:
            for agreement in db_agreements:
                # checking if the target link in the link is of the kind
                # allowed in the accosiated templates of the source agreement
                # self._check_target_link_kind(agreement, target_id)

                if agreement['kind'] == '/agreement/' and link_id \
                        not in agreement['links']:
                    agreement['links'].append(link_id)
                    DB.entities.update({'_id': agreement_id}, agreement)

        # Init Agreement
        entity.provider = Agreement()._get_provider(extras)
        entity.customer = Agreement().get_customer(extras)

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

    # Still under development
    def _check_target_link_kind(self, source_agreement, target_id):
    	"""
    	   Checks if the kind of the target resource is in the allowed list
    	   of kinds declared in the template(s) of the source entity.
    	"""

        # Get allowed links from all the templates accosiated with the agreement
    	templates = source_agreement['templates']
        allowed_links = []
    	for template in templates:
    	    out = template.split('#')
    	    scheme = out[0] + '#'
    	    term = out[1]
            db_templates = DB.templates.find({'_id': scheme})
            for tmpl in db_templates:

                if 'allowed_links' in tmpl['templates'][term]:
                    allowed_links = allowed_links + tmpl['templates'][term]['allowed_links']

        # Remove agreement kind while this is allowed by default
        if 'http://schemas.ogf.org/occi/sla#agreement' in allowed_links:
            allowed_links.remove('http://schemas.ogf.org/occi/sla#')

        # ToDo
    	if len(allowed_links) > 0:
            raise AttributeError('Check target resource kind')
            # get kind for target resource
         	# check if target kind is in allowed_kinds

    def _correct_provider(self, entity, extras):
        """
            Returns true if the entity provider and extras provider match
        """
        self.verify_provider(extras)
        provider = self._get_provider(extras)
        if entity.provider == provider:
            return True
        return False

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
    def _get_provider(cls, extras):
        """
            returns the provider id and password from extras
        """
        provider = extras["security"].items()[0][0]
        return provider

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


class AgreementTerm(MixinBackend):
    """
    Backend for OCCI SLA Agreement Template extension
    """
    pass


class AgreementTemplate(MixinBackend):
    """
    Backend for OCCI SLA Agreement Template extension
    """
    pass


def clean_dictionary(attr_dict):
    """
    Removes unicode strings from the dictionary.
    """
    if isinstance(attr_dict, dict):
        return {clean_dictionary(key): clean_dictionary(value)
                for key, value in attr_dict.iteritems()}
    elif isinstance(attr_dict, list):
        return [clean_dictionary(element) for element in attr_dict]
    elif isinstance(attr_dict, unicode):
        return str(attr_dict)
    else:
        return attr_dict
