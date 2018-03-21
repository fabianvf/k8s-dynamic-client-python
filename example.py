#!/usr/bin/env python

import json

from available_apis import Helper


def main():
    helper = Helper()
    namespaces = helper.get_resources(lambda x: x.name=='namespaces')[0]
    print(json.dumps(helper.list(namespaces), sort_keys=True, indent=4))


if __name__ == '__main__':
    main()
