#!/usr/bin/env python

import sys
import json
import requests
import kubernetes
from kubernetes import config
from kubernetes.client.api_client import ApiClient

class Resource(object):

    def __init__(self, prefix=None, group=None, apiversion=None, kind=None, namespaced=False, verbs=None, name=None, **kwargs):
        if None in (apiversion, kind):
            raise Exception("At least kind and apiversion must be provided")

        self._prefix = prefix
        self.group = group
        self.apiversion = apiversion
        self.kind = kind
        self.namespaced = namespaced
        self.verbs = verbs
        self.name = name

        allowed_extra_args = ['singularName', 'shortNames', 'categories']
        self.extra_args = kwargs
        for kwarg in kwargs.keys():
            if kwarg not in allowed_extra_args:
                import pdb
                pdb.set_trace()

    def __repr__(self):
        if self.group:
            groupversion = '{}/{}'.format(self.group, self.apiversion)
        else:
            groupversion = self.apiversion
        return '{}({}.{})'.format(self.__class__.__name__, groupversion, self.kind)


    @staticmethod
    def make_resource(prefix, group, apiversion, resource):
        if prefix == 'oapi':
            return OpenshiftResource(prefix=prefix, group=group, apiversion=apiversion, **resource)
        else:
            return K8sResource(prefix=prefix, group=group, apiversion=apiversion, **resource)

    @property
    def prefix(self):
        if self._prefix:
            return self_prefix
        raise NotImplementedError

    @property
    def urls(self):
        if self.group:
            full_prefix = '{}/{}/{}'.format(self.prefix, self.group, self.apiversion)
        else:
            full_prefix = '{}/{}'.format(self.prefix, self.apiversion)
        return {
            'base': '/{}/{}'.format(full_prefix, self.name),
            'namespaced_base': '/{}/namespaces/{{namespace}}/{}'.format(full_prefix, self.name),
            'full': '/{}/{}/{{name}}'.format(full_prefix, self.name),
            'namespaced_full': '/{}/namespaces/{{namespace}}/{}/{{name}}'.format(full_prefix, self.name)
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


class Helper(object):

    def __init__(self):
        config.load_kube_config()
        self.client = ApiClient()
        self._groups = [('api', ('', 'v1')), ('oapi', ('', 'v1'))] + self.get_api_groups()
        self._resources = [x for sublist in map(self.get_resources_for_group, self._groups) for x in sublist]

    def get_api_groups(self):
        groups = self.request('GET', '/apis')['groups']
        return [('apis', item) for sublist in map(lambda x: map(lambda y: (x['name'], y['version']), x['versions']), groups) for item in sublist]

    def get_resources_for_group(self, prefix_groupVersion):
        prefix, (group, apiversion) = prefix_groupVersion
        resources = filter(lambda x: '/' not in x['name'], self.request('GET', '/'.join(filter(lambda x: x, [prefix, group, apiversion])))['resources'])
        return [Resource.make_resource(prefix, group, apiversion, x) for x in resources]

    def get_resources(self, conditional):
        return filter(conditional, self._resources)

    def list(self, resource, namespace=None):
        path_params = {}
        if resource.namespaced and namespace:
            resource_path = resource.urls['namespaced_base']
            path_params['namespace'] = namespace
        else:
            resource_path = resource.urls['base']
        return self.request('get', resource_path, path_params=path_params)

    def get(self, resource, name, namespace=None):
        path_params = {'name': name}
        if resource.namespaced and namespace:
            resource_path = resource.urls['namespaced_full']
            path_params['namespace'] = namespace
        else:
            resource_path = resource.urls['full']
        return self.request('get', resource_path, path_params=path_params)

    def create(self, name=None, namespace=None, body=None):
        pass

    def delete(self, resource, name, namespace=None):
        path_params = {'name': name}
        if resource.namespaced and namespace:
            resource_path = resource.urls['namespaced_full']
            path_params['namespace'] = namespace
        else:
            resource_path = resource.urls['full']
        return self.request('delete', resource_path, path_params=path_params)

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

        path_params = params.get('path_params', {})
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
        ret = {}
        for resource in helper._resources:
            if resource.namespaced:
                key = resource.urls['namespaced_full']
            else:
                key = resource.urls['full']
            ret[key] = resource.__dict__

        print(json.dumps(ret, sort_keys=True, indent=4))


if __name__ == '__main__':
    sys.exit(main())
