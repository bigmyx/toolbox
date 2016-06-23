#!/usr/bin/env python

import subprocess
import argparse
import sys
from itertools import izip_longest

# Nagios exit codes:
WARNING = 1
CRITICAL = 2
UNKNOWN = 3
OK = 0


def check_stats(stats):
    result = "UNKNOWN"
    try:
        if float(stats[args.metric.upper()]) >= args.warning:
            result = "WARNING"
        elif float(stats[args.metric.upper()]) >= args.crit:
            result = "CRITICAL"
        else:
            result = "OK"
    except KeyError:
        pass
    return result


def get_stats(pid):
    stats_raw = subprocess.check_output(['jstat', '-gccapacity', pid])
    keys = stats_raw.splitlines()[0].split()
    vals = stats_raw.splitlines()[1].split()
    return dict(zip(keys, vals))


def main(args):
    java_processes = {}
    app_pids = []
    jps_out, err = subprocess.Popen(['jps'], stdout=subprocess.PIPE).communicate()

    for line in jps_out.splitlines():
        java_processes.update(dict(izip_longest(*[iter(line.split())] * 2, fillvalue="")))

    for pid, name in java_processes.iteritems():
        if name == args.app:
            app_pids.append(pid)
    if not app_pids:
        print "app `{}' not found!".format(args.app)
        return(WARNING)
    elif len(app_pids) > 1:
        print "there are more than 1 process for {}".format(args.app)
        return(WARNING)

    stats = get_stats(app_pids.pop())

    if args.debug:
        print "DEBUG: ", stats

    result = check_stats(stats)
    print '{}: {}={}, app: {}'.format(result, args.metric, stats[args.metric.upper()], args.app)

    sys.exit(globals()[result])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--app',     help='application name   ', required=True)
    parser.add_argument('-m', '--metric',  help='JVM metric to check', required=True)
    parser.add_argument('-w', '--warning', help='Warning threashold ', required=True, type=float)
    parser.add_argument('-c', '--crit',    help='Critical threashold', required=True, type=float)
    parser.add_argument('-d', '--debug',   default=False, action='store_true')
    args = parser.parse_args()
    sys.exit(main(args))
