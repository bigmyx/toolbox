#!/usr/bin/env python
import subprocess
import optparse
import requests
import sys

# CONSTANTS
TIMEOUT = 5


def validate_snapshot(master, snapshot):
    """ Validate that the snapshot is successfull, and
    not corrupt. """
    html = None
    uri = 'http://{}:60010/snapshot.jsp?name={}'.format(master, snapshot)
    print 'QUERY: {}'.format(uri)
    try:
        r = requests.get(uri, timeout=TIMEOUT)
        if r.status_code == 200:
            html = r.text
    except Exception, e:
        print 'EXCEPTION Verify: {}'.format(e)
        return False
    if html:
        if 'does not exist' in html:
            print 'NOTFOUND Snapshot: {}'.format(snapshot)
            return False
        if 'CORRUPTED' in html:
            print 'CORRUPTED Snapshot: {}'.format(snapshot)
            return False
        if not 'ok' in html:
            print 'UNHEALTHY Snapshot: {}'.format(snapshot)
            return False
    else:
        return False
    return True


def main():
    #_ Vars
    snapshot = []

    #_ Parse Options
    parser = optparse.OptionParser()
    parser.add_option('-t', '--tables', type='string', dest='tables',  help='Tables to backup')
    parser.add_option('-z', '--zookeeper', type='string', dest='zookeeper',  help='ZooKeeper cluster')
    parser.add_option('-m', '--master', type='string', dest='master',  help='HBase Master')
    parser.add_option('-c', '--copyto', type='string', dest='copy',  help='HDFS Target Cluster')
    parser.add_option('-s', '--secondarymaster', type='string', dest='target',  help='HBase Master Target Cluster')
    (opts, args) = parser.parse_args()

    #_ Get dfsadmin report
    try:
        print 'CREATE Snapshots'
        output = subprocess.check_output('export HADOOP_CLASSPATH=$HADOOP_CLASSPATH:/usr/lib/hbase/*:/usr/lib/hbase/lib/*;hadoop jar ./hbase-tools-0.1-SNAPSHOT.jar com.hbase.tools.Backup -tables {} -zookeeper {} 2>/dev/null'.format(opts.tables,  opts.zookeeper), shell=True)
        snapshot = [x for x in output.strip().split(',') if x]
    except subprocess.CalledProcessError, e:
        print 'Exception: {}'.format(e)

    #_ Distcp
    for s in snapshot:
        print 'VALIDATE Snapshot: {}'.format(s)
        valid_snapshot = validate_snapshot(opts.master, s)
        if valid_snapshot:
            try:
                print 'COPY Snapshot: {}'.format(s)
                output = subprocess.check_output('hbase org.apache.hadoop.hbase.snapshot.ExportSnapshot -snapshot {} -copy-to hdfs://{}/hbase -mappers 4'.format(s, opts.copy), shell=True)
                if validate_snapshot(opts.target, s):
                    print 'Snapshot verified on target cluster: {}'.format(s)
                else:
                    print 'Snapshot failed on target cluster: {}'.format(s)
            except subprocess.CalledProcessError, e:
                print 'Exception: {}'.format(e)
        else:
            print 'FAILED: {} is not valid'.format(s)


if __name__ == '__main__':
    main()

