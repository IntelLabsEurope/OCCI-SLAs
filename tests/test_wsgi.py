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
import unittest
from api import wsgi

class TestWsgi(unittest.TestCase):
    """
    Test WSGI.PY
    """
    def test_correct_credentials_returned(self):
        environ = {"HTTP_PROVIDER" : "DSS", "HTTP_PROVIDER_PASS" : "dss_pass"}
        credentials = wsgi._get_prov_credentials(environ)
        expected = {"DSS": "dss_pass"}
        self.assertEqual(credentials, expected)

    def test_correct_customer_returned(self):
        environ = {"HTTP_CUSTOMER": "Fernando"}
        customer = wsgi._get_customer(environ)
        expected = "Fernando"
        self.assertEqual(customer, expected)

    def test_wsgi_call(self):
        environ = {"HTTP_PROVIDER": "IMS",
                   "HTTP_PROVIDER_PASS": "ims_pass",
                   "HTTP_CUSTOMER": "Ricardo"}
        auth = TestApplication().__call__(environ, None)
        self.assertEqual(auth["customer"], "Ricardo")
        self.assertEqual(auth["security"], {"IMS": "ims_pass"})


class TestApplication(wsgi.Application):
    def _call_occi(self, *args, **kwargs):
        return kwargs
