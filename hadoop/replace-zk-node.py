"""
Replace a zookeeper node
"""
from collections import defaultdict

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

import brood
import sys

ZONES = [
    {'name': 'ec2.stam_exexample.com',
     'id': '<ID>',
     'private': True},
    {'name': 'ec2.stam_exadmin.com',
     'id': '<ID>',
     'private': False}]

ENV = '''export ZK_NODE={host_name}
export SECURITY_GROUP={sec_group}
export SECURITY_GROUP_ID={sec_group_id}
export SUBNET_ID={subnet_id}
export ROLE=zookeeper
export NAMESPACE={namespace}
export DEPLOYMENT={deployment}
export INSTANCE_TYPE=c3.2xlarge
export AVAILABILITY_ZONE={az}
export REGION={region}
export AMI_ID=$(curl -s https://ami.stam_exadmin.com/api/prod/latest/hvm)
export USER_DATA="#cloud-config\\nhostname: $ZK_NODE\\nrole: \
$ROLE\\nnamespace: $NAMESPACE\\ndeployment: $DEPLOYMENT"'''


class ZkReplace:
    PUPPET_MASTER = 'puppetmaster-ca-001'
    ZK_INIT = '/etc/init.d/zookeeper-server'

    def __init__(self, host_name):
        self._host_name = host_name
        self._private_fqdn = '{}.ec2.stam_exexample.com'.format(self._host_name)
        self._public_fqdn = '{}.ec2.stam_exadmin.com'.format(self._host_name)
        self._meta = self._fetch_meta()
        self._is_vpc = self._meta['vpc_id'] != ''
        self._check_sanity()

    def _check_sanity(self):
        if self._is_vpc:
            assert self._meta['subnet_id'], 'Subnet-id not set for vpc'
            assert self._meta['sec_group'] == 'vpc-data-layer', \
                'Sec group for vpc node must be vpc-data-layer but was {}' \
                    .format(self._meta['sec_group'])
        else:
            assert not self._meta['subnet_id'], 'Subnet-id set for non vpc'

        for key in ['private_ip', 'deployment', 'az', 'namespace',
                    'sec_group', 'region']:
            assert self._meta[key], '{0} not found for {1} in cmdb' \
                .format(key, self._host_name)

    def _fetch_meta(self):
        client = brood.Brood()
        fields = 'aws_launch_time,' \
                 'facts.deployment,' \
                 'facts.namespace,' \
                 'config.internal_address,' \
                 'config.external_address,' \
                 'security_groups,' \
                 'location,' \
                 'security_group_ids,' \
                 'vpc_id,' \
                 'subnet_id,' \
                 'region'

        # When we query CMDB we don't specify the state since node
        # could've been already terminated
        query = 'config.name:{0}'.format(self._host_name)
        nodes = client.get_query(query=query, fields=fields)
        assert len(nodes) >= 1, "Expected at-least one instance from " \
                                "CMDB found {0}".format(len(nodes))
        ordered_by_launch = sorted(nodes, key=lambda k: k['aws_launch_time'],
                                   reverse=True)
        node = defaultdict(str, ordered_by_launch[0])
        return {
            'private_ip': node['config.internal_address'],
            'public_ip': node['config.external_address'],
            'sec_group': node['security_groups'],
            'sec_group_id': node['security_group_ids'],
            'subnet_id': node['subnet_id'],
            'deployment': node['facts.deployment'],
            'az': node['location'],
            'namespace': node['facts.namespace'],
            'vpc_id': node['vpc_id'],
            'region': node['region'],
            'host_name': self._host_name
        }

    @staticmethod
    def format_ssh_commands(host, commands):
        return "\n".join(["ssh {0} {1}".format(host, c) for c in commands])

    def clear_puppet_cert(self):
        cmds = ['sudo puppet cert clean {0}'.format(self._private_fqdn)]
        return self.format_ssh_commands(self.PUPPET_MASTER, cmds)

    def update_dns(self):
        cmds = []
        for z in ZONES:
            ip = self._meta['private_ip'] if z['private'] \
                else self._meta['public_ip']
            if ip:
                cmds.append('route53 del_record {0} {1}.{2} A {3}'
                            .format(z['id'], self._host_name, z['name'], ip))
        return '\n'.join(cmds)

    def shutdown_zk_server(self):
        cmds = [
            'sudo {0} stop'.format(self.ZK_INIT),
            'sudo /sbin/shutdown -h now'
        ]
        return self.format_ssh_commands(self._host_name, cmds)

    def set_env(self):
        return ENV.format(**self._meta)

    def launch_instance(self):
        cmd = 'aws ec2 run-instances ' \
              '--region $REGION ' \
              '--instance-type $INSTANCE_TYPE ' \
              '--disable-api-termination ' \
              '--iam-instance-profile Name=base ' \
              '--key-name ops ' \
              '--user-data "$(echo -e $USER_DATA)" ' \
              '--image-id $AMI_ID '
        if not self._is_vpc:
            return cmd + '--security-groups $SECURITY_GROUP ' \
                         '--placement AvailabilityZone=$AVAILABILITY_ZONE'
        else:
            return cmd + '--security-group-ids $SECURITY_GROUP_ID ' \
                         '--subnet-id $SUBNET_ID '


def dump_commands(host_name, terminated):
    def command(command_func):
        def echo_wrapper(msg):
            sys.stderr.write('#%s\n' % msg)
            print('{0}\n'.format(command_func()))

        return echo_wrapper

    zkr = ZkReplace(host_name)
    command(zkr.set_env)("Setting environment")
    if not terminated:
        command(zkr.clear_puppet_cert)("Clearing puppet cert"),
        command(zkr.update_dns)("Delete DNS records"),
        command(zkr.shutdown_zk_server)("Shutting down ZK server")
    command(zkr.launch_instance)("Launching new instance")


def main():
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument("--terminated", dest="terminated", action='store_true',
                        help="Zookeeper host to replace")
    parser.add_argument("host", help="Zookeeper host to replace")
    args = parser.parse_args()
    dump_commands(args.host, args.terminated)


if __name__ == '__main__':
    main()

