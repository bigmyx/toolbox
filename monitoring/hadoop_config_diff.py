#!/usr/bin/env python
import argparse
import os
import xml.etree.ElementTree as ElementTree
import time
import socket
import json
import requests

# constants
DEFAULT_CONF_URL = '/conf?format=json'
HADOOP_CONF_PATH = '/etc/hadoop/conf'
HBASE_CONF_PATH = '/etc/hbase/conf'
TIME = int(time.time())
HOSTNAME = socket.gethostname()

CONFIG_BLACKLIST = ['slave.host.name', 'dfs.datanode.hostname', 'mapreduce.jobtracker.webinterface.trusted',
                    'fs.s3n.awsSecretAccessKey', 'fs.s3n.awsAccessKeyId']  # Add more ...

DAEMONS = {
    'namenode': ['50070', 'namenode'],
    'datanode': ['50075', 'regionserver'],
    'hmaster': ['16010', 'namenode'],
    'regionserver': ['16030', 'regionserver']
}


PORT_BLACKLIST = {
    '60010': ['fs.defaultFS', 'hfile.block.cache.size', 'hbase.rootdir', 'hbase.client.retries.number',
              'dfs.client.socket-timeout', 'dfs.datanode.socket.write.timeout'],
    '60030': ['mapred.job.tracker', 'fs.defaultFS', 'hbase.rootdir', 'hbase.client.retries.number', 'dfs.client.socket-timeout',
              'dfs.datanode.socket.write.timeout', 'hbase.master.cleaner.interval', 'hbase.master.logcleaner.ttl',
              'dfs.datanode.balance.bandwidthPerSec'],
    '50070': ['fs.defaultFS'],
    '50075': ['fs.defaultFS', 'dfs.namenode.name.dir', 'dfs.namenode.checkpoint.dir']
}

KEYS_TO_SORT = frozenset(['dfs.datanode.data.dir', 'dfs.namenode.name.dir', 'dfs.namenode.checkpoint.dir'])

DEPRECATED_PROPERTIES = {
    "create.empty.dir.if.nonexist": "mapreduce.jobcontrol.createdir.ifnotexist",
    "topology.script.file.name": "net.topology.script.file.name",
    "topology.script.number.args": "net.topology.script.number.args",
    "user.name": "mapreduce.job.user.name",
    "webinterface.private.actions": "mapreduce.jobtracker.webinterface.trusted"
    # Add more ...
}


def _xml_to_dict(xml_string, port):
    """
    Parse an XML configuration, and turn it into key value pairs.
    :param xml_string: a string representing an XML file
    :param port: the port of the dameon we are checking
    :return: a dict() of key->value pairs representing the xml
    :raise e:
    """
    xml_dict = {}
    try:
        root = ElementTree.fromstring(xml_string)
    except Exception, e:
        print('unable to parse xml configuration: {}'.format(e))
        raise e
    for prop in root.getiterator('property'):
        children = dict((child.tag, child) for child in prop)
        property_name = children['name'].text.strip()
        # up convert deprecated property to new value first
        if property_name in DEPRECATED_PROPERTIES:
            property_name = DEPRECATED_PROPERTIES[property_name]
        if property_name in CONFIG_BLACKLIST:
            continue
        # see if the key is in the port blacklist
        try:
            if property_name in PORT_BLACKLIST[port]:
                continue
        except Exception:
            print('BlacklistNotFoundException: port {}'.format(port))

        if property_name in KEYS_TO_SORT:
            property_value = sort_csv(children['value'].text.strip())
        else:
            property_value = children['value'].text.strip()

        xml_dict[property_name] = property_value
    return xml_dict


def get_configuration_from_url(port):
    """
    Given a port, query the URI for a running Hadoop configuration. Return a key-value dict()
    of configuration properties, as well as what local files these configurations
    came from
    :param port: the port to connect to
    :return: a dict() of key-value config properties, and a list() of local onfiguration files
    """
    config = {}
    conf_files = {}
    resp = requests.get(url='http://localhost:{}{}'.format(port, DEFAULT_CONF_URL))
    result = json.loads(resp.text)
    for _ in result['properties']:
        # exclude defaults, deprecated, and programatically generated sources
        if any(x in _['resource'] for x in ['default', 'deprecated', 'programatically']):
            continue
        if _['key'] in CONFIG_BLACKLIST:
            continue

        # see if the key is in the port blacklist
        try:
            if _['key'] in PORT_BLACKLIST[port]:
                continue
        except Exception:
            print('BlacklistNotFoundException: port {}'.format(port))

        if _['key'] in KEYS_TO_SORT:
            _['value'] = sort_csv(_['value'])

        config[str(_['key'])] = str(_['value'])
        # add the config file to the list
        conf_files[_['resource']] = None
    return config, conf_files.keys()


def sort_csv(csv):
    """
    Sort a CSV string alphabetically.
    :param csv: a comma-separated string
    :return: a CSV string sorted alphabetically
    """
    try:
        sorted_property = sorted(csv.split(','))
        csv_string = ','.join(sorted_property)
    except Exception:
        csv_string = property
    return csv_string


def get_configuration_from_file(conf_path, port):
    """
    Given a Hadoop XML structured configuration file, return a dict()
    of key => value pairs representing the configuration. Ex: core-site.xml
    Ex: {'fs.default.name': 'hdfs://namenode:8020'}
    :param conf_path: the full path of where to read the configuration file from
    :param conf_path: the port of the daemon we are checking
    :return: a dict() representing config_name => value
    :raise e: Log and re-raise an exception if we encounter an error
    """
    conf_file = open(conf_path, 'r')
    try:
        result = conf_file.read()
    except Exception, e:
        print('unable to read configuration file: {}'.format(e))
        raise e
    finally:
        conf_file.close()
    config = _xml_to_dict(result, port)
    return config


class DictDiffer(object):
    """
    Calculate the difference between two dictionaries as:
    (1) items added
    (2) items removed
    (3) keys same in both but changed values
    (4) keys same in both and unchanged values
    """
    def __init__(self, current_dict, past_dict):
        self.current_dict, self.past_dict = current_dict, past_dict
        self.set_current, self.set_past = set(current_dict.keys()), set(past_dict.keys())
        self.intersect = self.set_current.intersection(self.set_past)

    def added(self):
        return self.set_current - self.intersect

    def removed(self):
        return self.set_past - self.intersect

    def changed(self):
        return set(o for o in self.intersect if self.past_dict[o] != self.current_dict[o])

    def unchanged(self):
        return set(o for o in self.intersect if self.past_dict[o] == self.current_dict[o])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', help="debug configuration drift",
                        action="store_true", default=False)
    args = parser.parse_args()

    for daemon, _ in DAEMONS.items():
        if _[1] not in HOSTNAME:
            continue
        else:
            # initialize variables
            local_config = {}
            port = _[0]

            # grab running configuration, and a list of local configuration files to parse
            running_conf, conf_files = get_configuration_from_url(port)

            # load local configuration to determine differences
            for _ in conf_files:
                if 'hbase' in _:
                    file_name = os.path.join(HBASE_CONF_PATH, _)
                else:
                    file_name = os.path.join(HADOOP_CONF_PATH, _)
                conf = get_configuration_from_file(file_name, port)
                # merge dictionaries
                local_config = dict(local_config.items() + conf.items())

            # calculate property differences
            diff = DictDiffer(running_conf, local_config)

            # We compare running to local (DictDiffer(running_conf, local_config)).
            # 'removed' means not in the running config
            # 'added' means it's in the local, and not the running config
            print "hadoop.config.{}.ParamsAdded {}".format(daemon, len(diff.added()))
            print "hadoop.config.{}.ParamsRemoved {}".format(daemon, len(diff.removed()))
            print "hadoop.config.{}.ParamsChanged {}".format(daemon, len(diff.changed()))
            # debug mode if we wish to print out the differences.
            if args.verbose:
                print 'removed from running configuration'
                for _ in diff.removed():
                    print "\t{}".format(_)
                print 'added to local conf, but not running'
                for _ in diff.added():
                    print "\t{}".format(_)
                print 'values changed between running and local'
                for _ in diff.changed():
                    print "\t{}\n\t\trunning={}\n\t\t  local={}".format(_, running_conf[_], local_config[_])


if __name__ == '__main__':
    main()
