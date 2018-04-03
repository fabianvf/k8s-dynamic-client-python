#!/usr/bin/env python

from __future__ import print_function

import sys
import json
import yaml

import urllib3

from dynamic_client import DynamicClient
from dynamic_client import ResourceInstance

urllib3.disable_warnings()

USAGE = """ {cmd}: A dynamic python cli for kubernetes

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


def main():
    if len(sys.argv) <= 2 or '--help' in sys.argv or '-h' in sys.argv:
        print(USAGE.format(cmd=sys.argv[0]))
        sys.exit()
    action = sys.argv[1]
    search_term = sys.argv[2]
    args = sys.argv[3:]
    kwargs = parse_args(args)

    helper = DynamicClient()
    search_results = helper.search_resources(default_search(search_term))
    try:
        resource = search_results[0]
    except IndexError:
        print('Invocation error: Search term `{}` did not match any resource.'.format(search_term), file=sys.stderr)
        sys.exit(1)
    try:
        return globals()[action](resource, **kwargs)
    except KeyError:
        print('Invocation error: Action `{}` is not supported, supported actions are [get|list|update|replace|delete]'.format(action), file=sys.stderr)
        sys.exit(1)


def parse_args(args):
    args = list(args)
    kwargs = {
        'namespace': parse_flag('-n', args),
        'filename': parse_flag('-f', args),
    }
    kwargs['name'] = args.pop(0) if args else None
    if args:
        raise RuntimeError('Too many arguments, parsed {}, not sure what to do with {}'.format(kwargs, args))
    return {k: v for k, v in kwargs.items() if v}


def parse_flag(flag, args):
    value = None
    if flag in args:
        pos = args.index(flag)
        args.pop(pos)
        value = args.pop(pos)
    return value


def list_resources(resource, namespace=None):
    return resource.list(namespace=namespace)


def get(resource, name=None, namespace=None):
    return resource.get(name=name, namespace=namespace)


def delete(resource, name=None, namespace=None):
    return resource.delete(name, namespace)


def create(resource, namespace=None, filename=None):
    with open(filename, 'r') as f:
        body = yaml.load(f.read())

    return resource.create(body, namespace=namespace)


def update(resource, name=None, namespace=None, filename=None):
    with open(filename, 'r') as f:
        body = yaml.load(f.read())

    return resource.update(body, name=name, namespace=namespace)


def replace(resource, name=None, namespace=None, filename=None):
    with open(filename, 'r') as f:
        body = yaml.load(f.read())

    return resource.replace(body, name=name, namespace=namespace)


def default_search(term):
    terms = [term.lower(), term.lower()[:-1]]

    def inner(resource):
        for value in resource.__dict__.values():
            if str(value).lower() in terms or str(value).lower()[:-1] in terms:
                return resource.preferred
            elif isinstance(value, (list, tuple)):
                if term in value:
                    return resource.preferred
        return False
    return inner


def pprint(x):
    print(json.dumps(x, sort_keys=True, indent=4))


if __name__ == '__main__':
    try:
        resource = main()
        pprint(resource.todict())
    except Exception as e:
        print(USAGE.format(cmd=sys.argv[0]))
        print('Invocation failed! {}'.format(e), file=sys.stderr)
        sys.exit(1)
