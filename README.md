## OCCI SLAs

> :warning: **DISCONTINUATION OF PROJECT** - 
> *This project will no longer be maintained by Intel.
> Intel has ceased development and contributions including, but not limited to, maintenance, bug fixes, new releases, or updates, to this project.*
> **Intel no longer accepts patches to this project.**
> *If you have an ongoing need to use this project, are interested in independently developing it, or would like to maintain patches for the open source software community, please create your own fork of this project.*

This package is the implementation of the OCCI SLA management framework. 
It is an OCCI server which allows an OCCI SLA agreement to be created, updated and actioned, as is oultined in the OCCI SLA standard.
It also includes components for the violation detection (e.g. Rules Engine) and SLA monitoring (e.g. Aggregator and Collector).

Requirements:
* Running instance of Mongodb. Other specific requirements of the installation can be found in the setup python script.
* You need to implement a collector class (within the api/collectors.py) which will invoke a monitoring API for the resources linked with a SLA. A dummy collector implementation is provided that included the basic structure of the class and a substription functionality. 

Configuration:
Within the configs directory several config files need to be placed. We also place the json files for introducing templates to the OCCI SLAs framework.
* rabbit.cfd: config for interacting with the RabbitMQ
* metrics.json: list of the metrics that can be used in a template.


#### Starting the server:

    $ python runme.py
                     
This creates a running instance at http://localhost:8888

#### Creating an agreement:

    $ curl -i -X POST \
       -H "Category:agreement; scheme=\"http://schemas.ogf.org/occi/sla#\"" \
       -H "Category:gold;scheme=\"http://sla.ran.org/agreements#\"" \
       -H "Content-Type:text/occi" \
       -H "Provider:DSS" \
       -H "Provider_pass:dss_pass" \
       -H "customer:lola" \
       -H "X-OCCI-Attribute:occi.agreement.effectiveFrom=\"2014-11-02T02:20:26Z\"" \
       -H "X-OCCI-Attribute:occi.agreement.effectiveUntil=\"2014-11-02T02:20:27Z\"" \
       -d \
    '' \
     'http://localhost:8888/agreement/'

#### Retrieving an Agreement

    $ curl -i -X GET \
       -H "Provider:DSS" \
       -H "Provider_pass:dss_pass" \
     'http://localhost:8888/agreement/f9f94d68-913d-4448-b025-7e1e8d4fbe59'
     
#### Retrieving all agreements
    curl -i -X GET \
     'http://localhost:8888/agreement/'  

#### Accepting an agreement

    $ curl -i -X POST \
       -H "Category:accept; scheme=\"http://schemas.ogf.org/occi/sla#\"" \
       -H "Content-Type:text/occi" \
       -H "Provider:DSS" \
       -H "Provider_pass:dss_pass" \
       -d \
    '' \
     'http://localhost:8888/agreement/19cd4293-55bf-4d1a-ad90-8a5e8ca391ac?action=accept'

#### Deleting an agreement

    $ curl -i -X DELETE \
       -H "Provider:DSS" \
       -H "Provider_pass:dss_pass" \
     'http://localhost:8888/agreement/f9f94d68-913d-4448-b025-7e1e8d4fbe59'
 
#### Browsing agreements using GUI
Using a browser go to the URL http://localhost:8888.  This will present an interface to the API which allows you to view any created agreements.



                      
