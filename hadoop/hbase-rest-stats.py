#!/usr/bin/env python
import base64
import logging
import optparse
import simplejson as json
import sys
import urllib2


# _ CONSTS
TIMEOUT = 5
URI = '/status/cluster'


def get_json(uri):
    """ Request URL, load JSON, exit if error. """
    request = urllib2.Request(uri, headers={'Accept': 'application/json'})
    r = urllib2.urlopen(request, timeout=TIMEOUT)
    json_response = json.load(r)
    return json_response


def is_numeric(obj):
    """ Check to see if a variable is a int or float.
        Also check if value is >= 0. """
    if isinstance(obj, int) or isinstance(obj, float):
        if isinstance(obj, bool):
            return False
        if int(obj) >= 0:
            return True
    return False


def decode_region(b64_string):
    """ Base64 decode region information. Return
    table, region_md5 information. """
    table = 'null'
    region = 'null'
    try:
        b64_decode = base64.b64decode(b64_string)
        if '.META.' in b64_decode:
            table = 'META'
        elif '-ROOT-' in b64_decode:
            table = 'ROOT'
        else:
            table = b64_decode.split(',')[0]
            region = b64_decode.split('.')[-2]
    except Exception, e:
        pass
    return (table, region)


def main():
    #_ Variables
    metrics = []
    output = []

    #_ Setup Logging
    log = logging.getLogger()
    log.setLevel(logging.INFO)
    log.addHandler(logging.StreamHandler())

    #_ Parse Options
    parser = optparse.OptionParser()
    parser.add_option('-s', '--server', type='string', default='localhost',
                      dest='server',  help='HBase REST server to query')
    parser.add_option('-p', '--port', type='int', default=8080, dest='port',
                      help='HBase REST port')
    parser.add_option('-f', '--file', type='string', default=None,
                      dest='file', help='Output CSV file')
    parser.add_option('-v', '--verbose', default=False, dest='verbose',
                      action='store_true', help='Debug logging')
    (opts, args) = parser.parse_args()

    #_ If verbose, then set debug
    if opts.verbose:
        log.setLevel(logging.DEBUG)

    uri = 'http://{}:{}{}'.format(opts.server, opts.port, URI)
    log.debug('Requesting JSON from {}'.format(uri))
    json = get_json(uri)
    if not 'LiveNodes' in json.keys():
        log.error('Could not find per-region stats')
        sys.exit(1)
    log.debug('Iterating over LiveNodes')
    for live_node in json['LiveNodes']:
        log.debug('Processing LiveNode')
        if not 'Region' in live_node.keys():
            continue
        try:
            region_server = live_node['name']
            log.debug('RegionServer: {}'.format(region_server))
            for region in live_node['Region']:
                region_metrics = {}
                region_metrics['server'] = region_server
                log.debug('Processing Region')
                if 'name' in region:
                    log.debug('Decoding region name')
                    table_name, region_name = decode_region(region['name'])
                    log.debug('Decoded Result - Table: {} Region: {}'.format(table_name, region_name))
                    region_metrics['table'] = table_name
                    region_metrics['region'] = region_name
                else:
                    log.debug('No name in region {}, skipping'.format(region))
                    continue
                for metric_key, metric_value in region.iteritems():
                    if is_numeric(metric_value):
                        log.debug('Metric Added: {} = {}'.format(metric_key, metric_value))
                        region_metrics[metric_key] = metric_value
                log.debug('Appending metrics array')
                metrics.append(region_metrics)
        except Exception, e:
            log.debug('Exception processing LiveNode {}: {}'.format(live_node, e))

    # Build default csv structure
    skel = {}
    for row in metrics:
        for k in row.keys():
            if not k in skel:
                log.debug('Adding {} to skeleton'.format(k))
                skel[k] = 'null'

    # Sort skeleton by key, add to list
    log.debug('Sorting skeleton')
    sorted_skel = [key for key in sorted(skel.iterkeys())]
    log.debug('Dictionary Skeleton: {}'.format(sorted_skel))
    # Print CSV Header
    output.append(','.join(sorted_skel))
    for m in metrics:
        log.debug('Merging metric with skeleton')
        merged_skel = dict(skel.items() + m.items())
        log.debug('Result: {}'.format(merged_skel))
        log.debug('Sorted: {}'.format(sorted(merged_skel.iterkeys())))
        sorted_merged = [value for _, value in sorted(merged_skel.iteritems())]
        log.debug('Result values sorted: {}'.format(sorted_merged))
        output.append(','.join([str(x) for x in sorted_merged]))
    if opts.file is not None:
        f = open(opts.file, 'w')
        f.write("\n".join(output))
    else:
        print "\n".join(output)


if __name__ == '__main__':
    main()

