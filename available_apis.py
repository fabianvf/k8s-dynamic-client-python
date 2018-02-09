#!/usr/bin/env python

import sys
import json
import requests
import kubernetes
from kubernetes import config
from kubernetes.client.api_client import ApiClient

class Resource(object):

    def __init__(self, prefix=None, group=None, apiversion=None, kind=None, namespace=None, name=None, definition=None):
        if None in (apiversion, kind):
            raise Exception("At least kind and apiversion must be provided")

        self._prefix = prefix
        self.group = group
        self.apiversion = apiversion
        self.kind = kind
        self.namespace = namespace
        self.name = name
        self.definition = definition

    @property
    def prefix(self):
        raise NotImplementedError

    @property
    def resource_name(self):
        return self.kind.lower() + 's'

    @property
    def urls(self):
        if self.group:
            full_prefix = '{}/{}/{}'.format(self.prefix, self.group, self.apiversion)
        else:
            full_prefix = '{}/{}'.format(self.prefix, self.apiversion)
        return {
            'base': '{}/{}'.format(full_prefix, self.resource_name),
            'namespaced_base': '{}/namespaces/{{namespace}}/{}'.format(full_prefix, self.resource_name),
            'full': '{}/{}/{{name}}'.format(full_prefix, self.resource_name),
            'namespaced_full': '{}/namespaces/{{namespace}}/{}/{{name}}'.format(full_prefix, self.resource_name)
        }

class K8sResource(Resource):

    @property
    def prefix(self):
        if self._prefix:
            return self._prefix
        elif self.apiversion == 'v1' and not self.group:
            return '/api'
        else:
            return '/apis'

class OpenshiftResource(Resource):

    @property
    def prefix(self):
        if self._prefix:
            return self._prefix
        elif self.apiversion == 'v1' and not self.group:
            return '/oapi'
        else:
            return '/apis'



class ApisHelper(object):

    def __init__(self):
        config.load_kube_config()
        self.client = ApiClient()
        # self._groups = [('/api/v1'), ('/oapi/v1')] + self.get_api_groups()
        # self._resources = map(self.get_resources_for_group, self._groups)

    # def get_attributes(self):
    #     if self._apiversion == 'v1':
    #         prefixes = ['/api/', '/oapi/']
    #     else:
    #         prefixes = ['/apis/']
    #     candidates = {}
    #     for prefix in prefixes:
    #         url = self._cluster + prefix
    #         resources = get_resources_for_group(url, self._apiversion)
    #         filtered = {k[0]: v for k, v in resources.items() if self._kind == k[1]}
    #         if filtered:
    #             candidates[prefix] = filtered
    #     if len(candidates.keys()) != 1:
    #         import ipdb
    #         ipdb.set_trace()
    #     self._prefix = candidates.keys()[0]
    #     self._resources = candidates.values()[0]


    def get_api_groups(self):
        groups = self.request('GET', '/apis')['groups']
        return [('apis', item) for sublist in map(lambda x: map(lambda y: y['groupVersion'], x['versions']), groups) for item in sublist]

    def get_resources_for_group(self, prefix_group):
        prefix, group = prefix_group
        resources = self.request('GET', '/'.join([prefix, group]))['resources']
        return {(x['name'], x['kind'], group): x for x in resources}

    def list(self, resource):
        if resource.namespace:
            resource_path = resource.urls['namespaced_base']
        else:
            resource_path = resource.urls['base']
        return self.request('get', resource_path)

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

    def request(self, method, path, body=None, **params):

        if not path.startswith('/'):
            path = '/' + path

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
