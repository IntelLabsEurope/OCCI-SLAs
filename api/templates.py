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
    Load and validate Provider template lists into the database
"""

from pymongo import MongoClient
import numbers
import json
DB = MongoClient().sla
METRICS = json.load(file("configs/metrics.json"))


def load_templates(templates):
    """
        Takes a single list of templates for a provider and loads them into
        the database
    """

    validate_templates_3(templates)

    _id = {"_id": templates["scheme"]}
    templates.update(_id)

    if DB.templates.find(_id).count() == 0:
        DB.templates.insert(templates)
    else:
        current_temp = DB.templates.find(_id)[0]['templates']
        for temp in templates['templates'].keys():
            current_temp[temp] = templates['templates'][temp]
        templates['templates'] = current_temp
        DB.templates.update(_id, templates)


def validate_templates_3(templates):
    """
        Validates the template list. Throws an exception if invalid.
        This is a new version of the validation method based on the
        updated template format (e.g. term  type and conditions included)
    """

    if "scheme" not in templates:
        raise AttributeError("Scheme must be specified")

    if len(templates["templates"]) == 0:
        raise AttributeError("No templates in template list")

    for temp_key, template in templates["templates"].iteritems():
        if len(template) > 0:
            #if 'allowed_links' in template.keys():
            #    allowed_links_schemas = template['allowed_links']
                # validate allowed links
            if "terms" not in template.keys():
                raise AttributeError("Template {0} has no terms".format(temp_key))

            for term_k, term in template["terms"].iteritems():
                if len(term) > 0:
                    if term['type'] == 'SLO-TERM':
                        for metric_k in term['metrics']:
                            metric = term['metrics'][metric_k]
                            if metric_k in METRICS:
                                validate_metric2(metric_k, metric)
                            else:
                                raise AttributeError("{0} not a valid metric"
                                                     .format(metric_k))
                else:
                    raise AttributeError("{0} has no metrics".format(term_k))
        else:
            raise AttributeError("{0} has no terms".format(temp_key))


def validate_templates_2(templates):
    """
        Validates the template list. Throws an exception if invalid.
    """
    if "scheme" not in templates:
        raise AttributeError("Scheme must be specified")
    if len(templates["templates"]) == 0:
        raise AttributeError("No templates in template list")

    for temp_key, template in templates["templates"].iteritems():
        if len(template) > 0:
            for term_k, term in template.iteritems():
                if len(term) > 0:
                    for metric_k, metric in term.iteritems():
                        if metric_k in METRICS:
                            validate_metric(metric_k, metric)
                        else:
                            raise AttributeError("{0} not a valid metric"
                                                 .format(metric_k))
                else:
                    raise AttributeError("{0} has no metrics".format(term_k))
        else:
            raise AttributeError("{0} has no terms".format(temp_key))


def validate_templates(templates):
    """
        Validates the template list. Throws an exception if invalid.
    """
    if "scheme" not in templates:
        raise AttributeError("Scheme must be specified")
    if len(templates["templates"]) == 0:
        raise AttributeError("No templates in template list")

    for temp_key, template in templates["templates"].iteritems():
        if len(template.keys()) > 0:
            for metric_k, metric in template.iteritems():
                if metric_k in METRICS:
                    validate_metric(metric_k, metric)
                else:
                    raise AttributeError("{0} not a valid metric".
                                         format(metric_k))
        else:
            raise AttributeError("{0} has no metrics".format(temp_key))


# ToDo remove this method
def validate_metric(key, metric):
    """
        Takes a metric from a template and validates it
    """
    validate_metric_value(key, metric)
    validate_correct_limits(key, metric)

    if "max" in metric:
        validate_max(key, metric)
    if "min" in metric:
        validate_min(key, metric)
    if "margin" in metric:
        validate_margin(key, metric)
    if "enum" in metric:
        validate_enum(key, metric)


def validate_metric2(key, metric):
    """
        Takes a metric from a template and validates it
    """
    validate_metric_value(key, metric['value'])
    validate_correct_limits(key, metric)

    if "max" in metric['limiter_type']:
        # validate_max(key, metric)
        pass
    if "min" in metric['limiter_type']:
        # validate_min(key, metric)
        pass
    if "margin" in metric['limiter_type']:
        validate_margin(key, metric)
    if "enum" in metric['limiter_type']:
        # validate_enum(key, metric)
        pass


def validate_correct_limits(key, metric):
    """
        Ensures that the correct limits are for a given metric
    """
    allowed_limits = []
    if METRICS[key]["limiters"] is not None:
        allowed_limits = set(METRICS[key]["limiters"])

    limits = metric['limiter_type']

    if limits not in allowed_limits:
        raise AttributeError("{0}: Incorrect Limits".format(key))


def validate_enum(key, metric):
    """
        Ensures that the enum conforms to type and value is member of enum
    """
    enum_list = metric["enum"]
    if not isinstance(enum_list, list):
        raise AttributeError("{0}: Enum container must be a list".format(key))

    for enum in enum_list:
        if not isinstance(enum, basestring):
            raise AttributeError("{0}: Enum type as value".format(key))

    if metric["value"] not in enum_list:
        raise AttributeError("Metric value not in enum list")


def validate_margin(key, metric):
    """
        This method validate that the margin is of the correct type and within
        the range 0-100
    """
    validate_type(metric["value"], "real", key)
    if 'limiter_value' not in metric.keys():
        raise AttributeError("{0}: Missing limiter_value for margin limiter ".
                             format(key))
    if metric["limiter_value"] < 0 or metric["limiter_value"] > 100:
        raise AttributeError("{0}: Margin  must be  0-100 incl ".format(key))


# ToDo to remove those checks
def validate_min(key, metric):
    """
        Validates that min is being valid for an SLA term.
    """
    expctd_min_type = METRICS[key]["value"]
    validate_type(metric["value"], expctd_min_type, key)

    if metric["min"] > metric["value"]:
        raise AttributeError("{0} value must be greater than min".format(key))


# ToDo to remove those checks
def validate_max(key, metric):
    """
        Validates that min is being valid for an SLA term.
    """
    expctd_max_type = METRICS[key]["value"]
    validate_type(metric["value"], expctd_max_type, key)

    if metric["max"] < metric["value"]:
        raise AttributeError("{0} value must be less than max".format(key))


def validate_metric_value(key, metric):
    """
        Validates the current metric value against the value specified in the
        metric schema
    """
    expctd_value_type = METRICS[key]["value"]
    validate_type(metric, expctd_value_type, key)


def validate_type(actual, expected, term):
    """
        Validates whether the type given is the same as expected. Raises an
        Exception if not.
    """

    value_type = None
    if expected == "integer":
        value_type = numbers.Integral
    elif expected == "real":
        value_type = numbers.Real
    elif expected == "string":
        value_type = basestring
    if not isinstance(actual, value_type):
        raise AttributeError("{0} is not of type {1}".format(term, expected))
