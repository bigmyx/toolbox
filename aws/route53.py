#!/usr/bin/env python
import socket
import time

import boto
from boto.route53.record import ResourceRecordSets


# Route53 Zone Information
_ZONES = [
    {
        'name': 'example1.com',
        'id': 'XXXXXXXXXXXXX',
        'private': True
    },
    {
        'name': 'example2.com',
        'id': 'YYYYYYYYYYYY',
        'private': False
    }]

# adding the reverse lookup info if we're in this IP block.
#
_RDNS_ZONE = {  'name': '1.10.in-addr.arpa',
                'id': 'XYXYXYXY',
                'private': True }


def is_ip_address(ip_string):
    try:
        socket.inet_aton(ip_string)
        return True
    except socket.error:
        return False
    except TypeError:
        return False


def load_zone(route53_conn, zone_id):
    record_set = ResourceRecordSets(route53_conn, zone_id)
    return record_set


def add_entry(log, record_set, hostname, value, record_type='A', action='CREATE'):
    entry = record_set.add_change(action, hostname, record_type)
    entry.add_value(value)

    # We want to retry a few times with a backoff in between
    # Let's start with 3 retries and a 5 * retrycount sleep in between
    retrycount = 4
    for i in range(1, retrycount):
        sleeptime = i * 5
        try:
            change_set = record_set.commit()
            return change_set
        except Exception, e:
            log.error('route53: ERROR - commit for {}: {}'.format(hostname, e))
            log.info('route53: sleeping for {} seconds:'.format(sleeptime))
            time.sleep(sleeptime)


def create_records(route53_conn, hostname, private_ip, public_ip, log):
    # set up the reverse DNS info for the private zone if needed.
    private_octets = private_ip.split('.')
    private_octets.reverse()
    rdns_name = None 
    priv_name = None 
    if private_octets[2:] == _RDNS_ZONE['name'].split('.')[:2]:
        rdns_name = '.'.join(private_octets) + '.in-addr.arpa.'

    for zone in _ZONES:
        try:
            ip_address = None
            record_set = load_zone(route53_conn, zone['id'])
            zone_hostname = '.'.join([hostname, zone['name']]) + '.'
            if all((zone['private'] is True, is_ip_address(private_ip))):
                ip_address = private_ip
                priv_name = zone_hostname
            if all((zone['private'] is False, is_ip_address(public_ip))):
                ip_address = public_ip
            if ip_address:
                log.info('route53: Zone {}: Adding entry {} with ip address {}'.format(zone['name'], zone_hostname, ip_address))
                add_entry(log, record_set, zone_hostname, ip_address)
        except Exception, e:
            log.error('route53: ERROR - Exception adding entries to zone {}: {}'.format(zone, e))
            continue

    if rdns_name is not None and priv_name is not None:
        log.info('route53: Zone {}: Adding {} for hostname {} ({})'.format(_RDNS_ZONE['name'], rdns_name, priv_name, private_ip))
        changeset = load_zone(route53_conn, _RDNS_ZONE['id'])
        # Pass in 'UPSERT' so that the reverse dns will always be updated to this ipaddress
        add_entry(log, changeset, rdns_name, priv_name, 'PTR', 'UPSERT')


def main():
    route53_conn = boto.connect_route53()


if __name__ == '__main__':
    main()
