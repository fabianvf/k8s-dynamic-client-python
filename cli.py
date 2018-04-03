#!/usr/bin/env python

from __future__ import print_function

import sys
import json
import yaml

from dynamic_client import DynamicClient

USAGE=""" {cmd}: A dynamic python cli for kubernetes

USAGE:
    {cmd} list RESOURCE [-n NAMESPACE]
    {cmd} get RESOURCE [NAME] [-n NAMESPACE]
    {cmd} delete RESOURCE NAME [-n NAMESPACE]
    {cmd} create RESOURCE [-n NAMESPACE] -f FILE
    {cmd} update RESOURCE [-n NAMESPACE] -f FILE
    {cmd} replace RESOURCE [-n NAMESPACE] -f FILE

    RESOURCE is a string that will be used to search for a matching resource in the cluster
    NAME is the name of a specific resource
    NAMESPACE is the name of the namespace the resource(s) you are interacting with reside
    FILE is a valid kubernetes resource definition
"""


def methods(name=None):
    method_mapping = {
        'list': list_resources,
        'get': get,
        'delete': delete,
        'create': create,
        'update': update,
        'replace': replace
    }
    if name:
        return method_mapping[name]
    return method_mapping

def parse_namespace(args):
    args = list(args)
    namespace = None
    if '-n' in args:
        pos = args.index('-n')
        args.pop(pos)
        namespace = args.pop(pos)
    return namespace, args

def list_resources(resource, *args):
    namespace, args = parse_namespace(args)
    if args:
        raise RuntimeError("Too many arguments provided to `list`")
    return resource.list(namespace=namespace)


def get(resource, *args):
    namespace, args = parse_namespace(args)
    if len(args) > 1:
        raise RuntimeError("Too many arguments provided to `get`")
    name = args[0] if args else None
    return resource.get(name=name, namespace=namespace)


def delete(resource, *args):
    namespace, args = parse_namespace(args)
    if not args:
        raise RuntimeError("Missing argument: `delete` requires a name for a resource")
    elif len(args) > 1:
        raise RuntimeError("Too many arguments provided to `delete`")

    name = args[0]

    return resource.delete(name, namespace)


def create(resource, *args):
    args = list(args)
    namespace, args = parse_namespace(args)

    pos = args.index('-f')
    args.pop(pos)
    filename = args.pop(pos)

    if args:
        raise RuntimeError("Too many arguments provided to `create`")

    with open(filename, 'r') as f:
        body = yaml.load(f.read())

    return resource.create(body, namespace=namespace)


def update(resource, *args):
    args = list(args)
    namespace, args = parse_namespace(args)

    pos = args.index('-f')
    args.pop(pos)
    filename = args.pop(pos)

    with open(filename, 'r') as f:
        body = yaml.load(f.read())

    if len(args) > 1:
        name = args.pop()
    else:
        name = None

    if args:
        raise RuntimeError("Too many arguments provided to `update`")

    return resource.update(body, name=name, namespace=namespace)


def replace(resource, *args):
    args = list(args)
    namespace, args = parse_namespace(args)

    pos = args.index('-f')
    args.pop(pos)
    filename = args.pop(pos)

    with open(filename, 'r') as f:
        body = yaml.load(f.read())

    if len(args) > 1:
        name = args.pop()
    else:
        name = None

    if args:
        raise RuntimeError("Too many arguments provided to `update`")

    return resource.replace(body, name=name, namespace=namespace)

def default_search(term):
    def inner(resource):
        for value in resource.__dict__.values():
            if term == value:
                return resource.preferred
            elif isinstance(value, (list, tuple)):
                if term in value:
                    return resource.preferred
        return False
    return inner


def main():
    if len(sys.argv) <= 2 or '--help' in sys.argv or '-h' in sys.argv:
        print(USAGE.format(cmd=sys.argv[0]))
        sys.exit()
    action = sys.argv[1]
    search_term = sys.argv[2]
    args = sys.argv[3:]

    helper = DynamicClient()
    search_results = helper.search_resources(default_search(search_term))
    try:
        resource = search_results[0]
    except IndexError:
        print('Invocation error: Search term `{}` did not match any resource.'.format(search_term), file=sys.stderr)
        sys.exit(1)
    try:
        return methods(action)(resource, *args)
    except KeyError:
        print('Invocation error: Action `{}` is not supported, supported actions are {}'.format(action, '|'.join(methods().keys())), file=sys.stderr)
        sys.exit(1)


def pprint(x):
    print(json.dumps(x, sort_keys=True, indent=4))


if __name__ == '__main__':
    try:
        import ipdb
        with ipdb.launch_ipdb_on_exception():
            pprint(main())
    except Exception as e:
        print(USAGE.format(cmd=sys.argv[0]))
        print('Invocation failed! {}'.format(e), file=sys.stderr)
        sys.exit(1)
