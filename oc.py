#!/usr/bin/env python

import sys
import json
import yaml

from available_apis import Helper

def methods(name):
    return {
        'list': lambda resource, *args: resource.list(*args),
        'get': lambda resource, *args: resource.get(*args),
        'delete': lambda resource, *args: resource.delete(*args),
        'create': create
    }[name]

def create(resource, *args):
    args = list(args)

    pos = args.index('-f')
    args.pop(pos)
    filename = args.pop(pos)

    with open(filename, 'r') as f:
        body = yaml.load(f.read())

    return resource.create(body, *args)

def default_search(term):
    def inner(resource):
        for value in resource.__dict__.values():
            if term == value:
                return True
            elif isinstance(value, (list, tuple)):
                if term in value:
                    return True
        return False
    return inner


def main():
    action = sys.argv[1]
    search_term = sys.argv[2]
    args = sys.argv[3:]

    helper = Helper()
    search_results = helper.search_resources(default_search(search_term))
    resource = search_results[0]
    return methods(action)(resource, *args)

def pprint(x):
    print(json.dumps(x, sort_keys=True, indent=4))

if __name__ == '__main__':
    import ipdb
    with ipdb.launch_ipdb_on_exception():
        pprint(main())
