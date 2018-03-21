#!/usr/bin/env python

import json

from available_apis import Helper


def main():
    helper = Helper()
    namespaces = helper.get_resources(lambda x: x.name=='namespaces')[0]
    # List namespaces
    pprint(helper.list(namespaces))
    # Get default namespace
    pprint(helper.get(namespaces, 'default'))

    dcs = helper.get_resources(lambda x: x.name=='deploymentconfigs')[0]
    # List deploymentconfigs
    pprint(helper.list(dcs))
    # List deploymentconfigs in the default namespace
    pprint(helper.list(dcs, 'default'))
    # Get the router deploymentconfig from the default namespace
    pprint(helper.get(dcs, 'router', 'default'))

    services = helper.get_resources(lambda x: x.name=='services')[0]
    # List all services
    pprint(helper.list(services))

    # delete the webconsole service from the openshift-web-console
    helper.delete(services, 'webconsole', 'openshift-web-console')





def pprint(x):
    print(json.dumps(x, sort_keys=True, indent=4))
if __name__ == '__main__':
    import ipdb
    with ipdb.launch_ipdb_on_exception():
        main()
