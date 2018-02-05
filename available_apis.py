#!/usr/bin/env python

import sys
import json
import requests
import kubernetes
from kubernetes import config
from kubernetes.client.api_client import ApiClient


class Helper(object):

    def __init__(self, apiversion=None, kind=None):
        config.load_kube_config()
        self.client = ApiClient()
        self._apiversion = apiversion
        self._kind = kind
        if kind and apiversion:
            self.get_attributes()

    def get_attributes(self):
        if self._apiversion == 'v1':
            prefixes = ['/api/', '/oapi/']
        else:
            prefixes = ['/apis/']
        candidates = {}
        for prefix in prefixes:
            url = self._cluster + prefix
            resources = get_resources_for_group(url, self._apiversion)
            filtered = {k[0]: v for k, v in resources.items() if self._kind == k[1]}
            if filtered:
                candidates[prefix] = filtered
        if len(candidates.keys()) != 1:
            import ipdb
            ipdb.set_trace()
        self._prefix = candidates.keys()[0]
        self._resources = candidates.values()[0]

    def apis_for(self, action):
        candidates = []
        for name, resource in self._resources.items():
            if action in resource['verbs']:
                candidates.append(name)
        if len(candidates) != 1:
            import ipdb
            ipdb.set_trace()
        return sorted(candidates, key=len)[0]

    def list(self, namespace=None):
        resource_path = self.apis_for('list')
        return requests.get('/'.join([self._cluster, self._prefix, self._apiversion, resource_path]), verify=False)

    def get(self, name=None, namespace=None):
        return requests.get('/'.join([self._url, self._prefix, self._apiversion, self._kind]), verify=False)

    def create(self, name=None, namespace=None, body=None):
        pass

    def delete(self, name=None, namespace=None):
        pass

    def update(self, name=None, namespace=None, body=None):
        pass

    def patch(self, name=None, namespace=None, body=None):
        pass

    def watch(self, name=None, namespace=None):
        pass

    def deletecollection(self, name=None, namespace=None):
        pass

    def proxy(self, name=None, namespace=None):
        pass

    def get_api_groups(self):
        groups = self.request('GET', '/apis')['groups']
        return [item for sublist in map(lambda x: map(lambda y: y['groupVersion'], x['versions']), groups) for item in sublist]

    def get_resources_for_group(self, prefix, group):
        resources = self.request('GET', '/'.join([prefix, group]))['resources']
        return {(x['name'], x['kind'], group): x for x in resources}

    def request(self, method, path, body=None, **params):

        path_params = {}
        query_params = []
        if 'pretty' in params:
            query_params.append(('pretty', params['pretty']))
        header_params = {}
        form_params = []
        local_var_files = {}
        body_params = None
        # HTTP header `Accept`
        header_params['Accept'] = self.client.\
            select_header_accept(['application/json', 'application/yaml', 'application/vnd.kubernetes.protobuf'])

        # HTTP header `Content-Type`
        header_params['Content-Type'] = self.client.\
            select_header_content_type(['*/*'])

        # Authentication setting
        auth_settings = ['BearerToken']

        return json.loads(self.client.call_api(path, method.upper(),
                                        path_params,
                                        query_params,
                                        header_params,
                                        body=body,
                                        post_params=form_params,
                                        files=local_var_files,
                                        auth_settings=auth_settings,
                                        _preload_content=False)[0].data)



def main():
    import ipdb
    with ipdb.launch_ipdb_on_exception():
        helper = Helper()
        api_groups = helper.get_api_groups()
        resources = { k: v for d in map(lambda x: helper.get_resources_for_group('/apis', x), api_groups) for k, v in d.items() }
        resources.update(helper.get_resources_for_group('/api', 'v1'))
        resources.update(helper.get_resources_for_group('/oapi', 'v1'))
        ret = {}
        for (name, _, group), resource in resources.items():
            ret[group + '/' + name] = resource

        print(json.dumps(ret, sort_keys=True, indent=4))


if __name__ == '__main__':
    sys.exit(main())
