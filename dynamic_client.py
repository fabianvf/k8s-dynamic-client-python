#!/usr/bin/env python

import sys
import json
from functools import partial

import kubernetes
from kubernetes import config
from kubernetes.client.api_client import ApiClient
from kubernetes.client.rest import ApiException

class Resource(object):

    def __init__(self, prefix=None, group=None, apiversion=None, kind=None,
                 namespaced=False, verbs=None, name=None, preferred=False, client=None,
                 singularName=None, shortNames=None, categories=None, **kwargs):

        if None in (apiversion, kind):
            raise Exception("At least kind and apiversion must be provided")

        self._prefix = prefix
        self.group = group
        self.apiversion = apiversion
        self.kind = kind
        self.namespaced = namespaced
        self.verbs = verbs
        self.name = name
        self.preferred = preferred
        self.client = client
        self.singular_name = singularName
        self.short_names = shortNames
        self.categories = categories

        self.extra_args = kwargs

    def __repr__(self):
        if self.group:
            groupversion = '{}/{}'.format(self.group, self.apiversion)
        else:
            groupversion = self.apiversion
        return '<{}({}.{}>)'.format(self.__class__.__name__, groupversion, self.kind)


    @staticmethod
    def make_resource(prefix, group, apiversion, resource, preferred=False, client=None):
        if prefix == 'oapi':
            return OpenshiftResource(prefix=prefix, group=group, apiversion=apiversion, client=client, preferred=preferred, **resource)
        else:
            return K8sResource(prefix=prefix, group=group, apiversion=apiversion, client=client, preferred=preferred, **resource)

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

    def __getattr__(self, name):
        return partial(getattr(self.client, name), self)


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


def flatten(l):
    return [item for sublist in l for item in sublist]

class DynamicClient(object):

    def __init__(self):
        config.load_kube_config()
        self.client = ApiClient()
        self._groups = self.get_api_groups()
        self._resources = flatten([self.get_resources_for_group(*group_parts) for group_parts in self._groups])

    def default_groups(self):
        groups = [('api', '', 'v1', True)]

        try:
            self.request('get', '/version/openshift')
            is_openshift = True
        except ApiException:
            is_openshift = False

        if is_openshift:
            groups.append(('oapi', '', 'v1', True))
        return groups

    def get_api_groups(self):
        """ Returns a list of API groups in the format:
            (api_prefix, group_name, version, preferred)

            api_prefix is the url prefix to access the group (usually /apis, but
            /api for core kubernetes resources and /oapi for core openshift resources)

            group_name and version are the name and version of the group

            preferred is a boolean indicating whether this version of the group is preferred
        """
        prefix = 'apis'
        groups_response = self.request('GET', '/{}'.format(prefix))['groups']

        groups = self.default_groups()

        for group in groups_response:
            for version in group['versions']:
                groups.append([
                    prefix,
                    group['name'],
                    version['version'],
                    version == group['preferredVersion']
                ])

        return groups

    def get_resources_for_group(self, prefix, group, apiversion, preferred=False):
        """ returns the list of resources associated with provided groupVersion"""

        path = '/'.join(filter(None, [prefix, group, apiversion]))
        resources_response = self.request('GET', path)['resources']

        # Filter out subresources
        resources_raw = filter(lambda resource: '/' not in resource['name'], resources_response)

        resources = []
        for resource in resources_raw:
            resources.append(Resource.make_resource(
                prefix,
                group,
                apiversion,
                resource,
                client=self,
                preferred=preferred
            ))
        return resources

    def search_resources(self, conditional):
        """ Takes a conditional test and returns a list of resources that satisfy the test
            The test should take an object of the Resource type as an argument,
            and return a boolean

        Ex:
            def is_namespaces(resource):
                return resource.name == 'namespaces'

            client.search_resources(is_namespaces)

        will return all resources with the name 'namespaces'
        """
        return list(filter(conditional, self._resources))

    def list(self, resource, namespace=None):
        path_params = {}
        if resource.namespaced and namespace:
            resource_path = resource.urls['namespaced_base']
            path_params['namespace'] = namespace
        else:
            resource_path = resource.urls['base']
        return self.request('get', resource_path, path_params=path_params)

    def get(self, resource, name=None, namespace=None):
        if name is None:
            return self.list(resource, namespace=namespace)
        path_params = {'name': name}
        if resource.namespaced and namespace:
            resource_path = resource.urls['namespaced_full']
            path_params['namespace'] = namespace
        else:
            resource_path = resource.urls['full']
        return self.request('get', resource_path, path_params=path_params)

    def create(self, resource, body, namespace=None):
        path_params = {}
        if resource.namespaced and namespace:
            resource_path = resource.urls['namespaced_base']
            path_params['namespace'] = namespace
        elif resource.namespaced and not namespace:
            if body.get('metadata') and body['metadata'].get('namespace'):
                resource_path = resource.urls['namespaced_base']
                path_params['namespace'] = body['metadata']['namespace']
        else:
            resource_path = resource.urls['base']
        return self.request('post', resource_path, path_params=path_params, body=body)

    def delete(self, resource, name, namespace=None):
        path_params = {'name': name}
        if resource.namespaced and namespace:
            resource_path = resource.urls['namespaced_full']
            path_params['namespace'] = namespace
        else:
            resource_path = resource.urls['full']
        return self.request('delete', resource_path, path_params=path_params)

    # def update(self, name=None, namespace=None, body=None):
    #     raise NotImplementedError

    def patch(self, resource, body, name, namespace=None):
        path_params = {'name': name}
        if resource.namespaced and namespace:
            resource_path = resource.urls['namespaced_full']
            path_params['namespace'] = namespace
        elif resource.namespaced and not namespace:
            if body.get('metadata') and body['metadata'].get('namespace'):
                resource_path = resource.urls['namespaced_full']
                path_params['namespace'] = body['metadata']['namespace']
        else:
            resource_path = resource.urls['full']
        content_type = self.client.\
            select_header_content_type(['application/json-patch+json', 'application/merge-patch+json', 'application/strategic-merge-patch+json'])

        return self.request('patch', resource_path, path_params=path_params, body=body, content_type=content_type)

#     def watch(self, name=None, namespace=None):
#         raise NotImplementedError

#     def deletecollection(self, name=None, namespace=None):
#         raise NotImplementedError

#     def proxy(self, name=None, namespace=None):
#         raise NotImplementedError

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
        # HTTP header `Accept`
        header_params['Accept'] = self.client.\
            select_header_accept(['application/json', 'application/yaml', 'application/vnd.kubernetes.protobuf'])

        # HTTP header `Content-Type`
        header_params['Content-Type'] = params.get('content_type', self.client.\
            select_header_content_type(['*/*']))

        # Authentication setting
        auth_settings = ['BearerToken']

        return json.loads(self.client.call_api(
            path,
            method.upper(),
            path_params,
            query_params,
            header_params,
            body=body,
            post_params=form_params,
            files=local_var_files,
            auth_settings=auth_settings,
            _preload_content=False
        )[0].data)


def main():
    client = DynamicClient()
    ret = {}
    for resource in client._resources:
        if resource.namespaced:
            key = resource.urls['namespaced_full']
        else:
            key = resource.urls['full']
        ret[key] = dict(list(filter(lambda kv: kv[0] != 'client', resource.__dict__.items())))

    print(json.dumps(ret, sort_keys=True, indent=4))
    return 0


if __name__ == '__main__':
    sys.exit(main())
