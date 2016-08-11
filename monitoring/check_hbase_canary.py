#!/usr/bin/env python

import subprocess
import sys
import os

# ======Nagios exit codes========
OK = 0
WARNING = 1
CRITICAL = 2
UNKNOWN = 3
# ======Nagios exit codes========

def die(message, code):
    print message
    sys.exit(code)

def main():
    hbase_cmd = "/usr/bin/hbase"
    log_dir = "/var/log/hbase"
    if not os.access(log_dir, os.W_OK):
        die("Directory {} is not writable!".format(log_dir), UNKNOWN)

    try:
        lines = subprocess.Popen([hbase_cmd, "org.apache.hadoop.hbase.tool.Canary"],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[1]
    except:
        die("command failed", UNKNOWN)
    read_regions = {}

    for line in str.splitlines(lines):
        if 'read from region' in line:
            region = line.split(' ')[7].split(',')[0]
            if region in read_regions:
                read_regions[region] += 1
            else:
                read_regions[region] = 1

    report = ""
    for k, v in read_regions.iteritems():
        report += "{}={} ".format(k, v)

    die(report, OK)

if __name__ == "__main__":
    main()
