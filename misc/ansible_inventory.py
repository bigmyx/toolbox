#!/usr/bin/env python

import requests
import json

_cmdburl = 'https://cmdb/api/cmdb/getquery'
_fields = [
    'id',
    'config.name',
    'config.instance_type',
    'cloud.aws.placement.availability_zone',
    'security_groups',
    'config.internal_address',
    'config.external_address',
    'aws_launch_time',
    'deployment',
    'nodepool'
    ]

class ansible_translater(json.JSONDecoder):
    """
    Take json answer from cmdb and translate to ansible json
    """

    # in the hash below, key labels are seen in cmdb,
    # value labels are needed for ansible
    attribute_map = {
        'aws_launch_time': 'ec2_launch_time',
        'cloud.aws.placement.availability_zone': 'ec2_placement',
        'config.external_address': 'ec2_ip_address',
        'config.instance_type': 'ec2_instance_type',
        'config.internal_address': 'ec2_private_ip_address',
        'config.name': 'name',
        'id': 'ec2_id',
        'security_groups': 'ec2_security_group_names'
        }

    def decode(self,json_string):
        """
        expected entry point
        https://docs.python.org/2.7/library/json.html

        Read in existing json, and build a new structure
        more to ansible's liking.
        """

        # use the default decode to interpret original json as python obj
        default_obj = super(ansible_translater,self).decode(json_string)

        # initialize a response object
        docroot = {
            'cmdb': { 'hosts': [] },
            '_meta': {'hostvars': {} }
            }

        for host in default_obj:
            nodename = self.ansible_nodename(host)
            deployment = host['deployment']
            nodepool = host['nodepool']

            # populate --list information
            self.group_append(docroot, 'cmdb', nodename)
            self.group_append(docroot, deployment, nodename)
            self.group_append(docroot, nodepool, nodename)
            
            # populate --host information
            node = {nodename: self.remap_attributes(host) }
            node[nodename].update({'ansible_ssh_host': host['config.internal_address']})
            docroot['_meta']['hostvars'].update(node)

        return docroot

    def ansible_nodename(self,node):
        """
        generate a node name for ansible
        currently, we're following the ec2 dyn_inv practice
        of just returning internal ip address
        """
        nodeip = node['config.internal_address']
        return '_'.join(nodeip.split('.'))

    def group_append(self, docroot, group, nodename):
        if group is None:
            return
        if group not in docroot.keys():
            docroot.update({group: {'hosts': []}})
        docroot[group]['hosts'].append(nodename)

    def remap_attributes(self,node):
        newnode = {}
        recognized = self.attribute_map.keys()
        for k, v in node.iteritems():
            if k in recognized:
                new = self.attribute_map[k]
                newnode[new] = v
            else:
                newnode[k] = v
        return newnode

def get_all_instance_data(options=None):
    """
    query cmdb for the state of all running instances
    """
    filter_data = {"query": "state:running", "fields": ','.join(_fields) }
    r = requests.post(_cmdburl, data=filter_data)
    return r.json()

def translate(data):
    """
    translate cmdb attributes to a nomenclature better fitting ansible
    """
    return json.loads(json.dumps(data),cls=ansible_translater)

def print_json(data):
    """
    output data with some format preferences
    """
    print json.dumps(data, indent=4, sort_keys=True)

def main():
    data = get_all_instance_data()
    translated = translate(data)
    print_json(translated)

if __name__ == "__main__":
    main()

