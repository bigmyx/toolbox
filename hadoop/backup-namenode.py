#!/usr/bin/env python

"""
Backup Hadoop HDFS Namenode machine data to S3
"""

from boto.s3.key import Key
import xml.etree.ElementTree as ET
import boto
import boto.s3
import os
import socket
import subprocess
import sys
import time

AWS_ACCESS_KEY_ID = 'XXXX'
AWS_SECRET_ACCESS_KEY = 'XXXXXX'
S3_BUCKET = 'bicket-name'
EPOCH = int(time.time())
HOSTNAME = socket.gethostname()
BACKUP_BUCKET = '%s/namenode-%s' % (HOSTNAME, EPOCH)

#_ Fucntions
def percent_cb(complete, total):
    """ Pretty prints percentage uploaded. """
    sys.stdout.write('.')
    sys.stdout.flush()


def listdir_fullpath(d):
    """ Return full paths for listing a dir. """
    return [os.path.join(d, f) for f in os.listdir(d)]


def get_namenode_dirs():
    """ Returns path of the namenode files. """
    dirs = []
    #_ Hacky as hell. But a lot better than python XML parsing
    output = subprocess.check_output('cat /etc/hadoop/conf/hdfs-site.xml |grep -A1 dfs.name.dir|grep value|cut -f2 -d">"|cut -f1 -d"<"', shell=True)
    dirs = list(output.rstrip().split(','))
    return dirs


if __name__ == '__main__':
    #_ Connect to Boto
    conn = boto.connect_s3(AWS_ACCESS_KEY_ID,
            AWS_SECRET_ACCESS_KEY)

    #_ Get NN Dirs
    paths = get_namenode_dirs()

    #_ Connect to the S3 bucket
    bucket = conn.get_bucket(S3_BUCKET)

    #_ Prepare to upload files to this new bucket
    k = Key(bucket)
    for path in paths:
        print "Backup up path: %s" % (path)
        for f in listdir_fullpath(path + '/current'):
            print "  Backing up file: %s" % (f)
            #_ Set upload filename to prefix + filename
            k.key = "%s/%s" % (BACKUP_BUCKET, f)
            #_ Upload contents from file.
            k.set_contents_from_filename(f,
                cb=percent_cb, num_cb=10)
