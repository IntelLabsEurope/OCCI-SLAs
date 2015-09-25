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
from pymongo import MongoClient
import ConfigParser
import json

DB = MongoClient().sla
METRICS = json.load(file("configs/metrics.json"))


def load_monitoring_capabilities():
    """
        Loads the monitoring capabilities in terms of list
        of monitorable metrics and collector API
    """
    config = ConfigParser.ConfigParser()
    for metric_name, metric_infos in METRICS.iteritems():
        if 'monitoring' in metric_infos.keys():
            monitoring_sys = str(metric_infos['monitoring'])
            config.read('configs/' + monitoring_sys + '.cfg')
            collector_api = config.get(monitoring_sys, 'collector_api')

            monitoring_records = DB.monitoring.find({'name': monitoring_sys})
            if monitoring_records.count() > 0:

                mon_record = monitoring_records[0]
                try:
                    mon_metrics = mon_record['metrics']
                    if metric_name not in mon_metrics:
                        mon_metrics.append(metric_name)
                        mon_record['metrics'] = mon_metrics

                        DB.monitoring.update({'name': monitoring_sys},
                                             mon_record, upsert=True)
                except KeyError:
                    print monitoring_sys + \
                          ' record malformed or insert to DB failed.'
            else:
                mon_record = {'name': monitoring_sys,
                              'metrics': [metric_name],
                              'api': collector_api}
                DB.monitoring.insert(mon_record)


if __name__ == '__main__':
    load_monitoring_capabilities()
