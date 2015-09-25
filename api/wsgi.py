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
    Overriding wsgi Application to modify what is past on through extras
"""
import occi.wsgi


class Application(occi.wsgi.Application):
    """
        WSGI Application
    """
    def __call__(self, environ, response):
        cred = _get_prov_credentials(environ)
        cust = _get_customer(environ)

        return self._call_occi(environ, response, security=cred, customer=cust)


def _get_prov_credentials(environ):
    """
    Returns the provider credentials, which are passed as Header items.
    :param environ: Environment Dictionary containing the headers
    :return: Provider Credentials
    """
    prov = environ["HTTP_PROVIDER"] if "HTTP_PROVIDER" in environ else None
    prov_pass = environ["HTTP_PROVIDER_PASS"] if "HTTP_PROVIDER_PASS" \
        in environ else None
    return {prov: prov_pass}


def _get_customer(environ):
    """
    Returns customer ID, which is passed as a header item
    :param environ:  Environment Dictionary containing the header
    :return: Customer ID
    """
    return environ["HTTP_CUSTOMER"] if "HTTP_CUSTOMER" in environ else None
