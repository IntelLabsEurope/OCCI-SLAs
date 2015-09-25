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
    OCCI SLA framework API
"""
from setuptools import setup

setup(name='occi-sla',
      version='0.3',
      description='OCCI SLA API',
      author_email='gregory.katsaros@intel.com',
      url='http://www.intel.com',
      license='Apache 2.0',
      packages=['api'],
      install_requires=['pyssf', 'arrow', 'pymongo', 'Intellect', 'requests', 'httpretty', 'pika'],
      zip_safe=False)
