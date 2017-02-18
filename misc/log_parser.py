#!/usr/bin/env python
import logging
import argparse
import datetime
import boto3
import psycopg2

METRIC_DELTA = 15 #minutes
METRIC_NAME = 'StatusCheckFailed_System'
METRIC_PERIOD = 60 #seconds
INSTANCE_ID = 'i-xxxxxxx'
DB_HOST = 'localhost'
DB_USER = 'test'
DB_NAME = 'test'
PARSE_LOG_FILE = 'install.log'
PARSE_POS_FILE = 'position'
PARSE_ERR_LIMIT = 10 #occurances


def _record_pos(f):
    with open(PARSE_POS_FILE, 'w') as pos:
        pos.write(str(f.tell()))

def _get_size(f):
    f.seek(0, 2)
    return f.tell()

def _get_pos(f):
    try:
        with open(PARSE_POS_FILE, 'r') as pos:
            position = int(pos.read())
    except IOError:
        logging.debug("first time run, starting from zero!")
        position = 0
    if position > _get_size(f):
        logging.debug('file rotated, starting from zero!')
        position = 0
    return position

def parse_log():
    pattern = 'error'
    count = 0
    with open(PARSE_LOG_FILE, 'r') as input_f:
        position = _get_pos(input_f)
        input_f.seek(position)
        for line in input_f:
            if pattern in line.lower():
                count += 1
        _record_pos(input_f)
        logging.debug("%d occurances", count)
        if count >= PARSE_ERR_LIMIT:
            logging.warn("%d is above current limit (%d)", count, PARSE_ERR_LIMIT)

def update_db(status):
    try:
        conn = psycopg2.connect("dbname=test user=test")
        cur = conn.cursor()
        sql = "UPDATE healthcheck SET healthy = %(status)s WHERE name = 'zhopa'"
        cur.execute(sql, {'status': status})
        conn.commit()
    finally:
        cur.close()
        conn.close()

def health_check():
    client = boto3.client('cloudwatch')
    begin = (datetime.datetime.now() - datetime.timedelta(minutes=METRIC_DELTA)).isoformat()
    end = datetime.datetime.utcnow().isoformat()
    occurances = 0

    data = client.get_metric_statistics(
        Namespace='AWS/EC2',
        MetricName=METRIC_NAME,
        Dimensions=[
            {
                'Name': 'InstanceId',
                'Value': INSTANCE_ID
            },
        ],
        StartTime=begin,
        EndTime=end,
        Period=METRIC_PERIOD,
        Statistics=['SampleCount']
    )

    for dpoint in data['Datapoints']:
        if int(dpoint['SampleCount']) > 1:
            occurances += 1
        else:
            occurances = 0

    if occurances > 10:
        logging.debug("%d healthcheck errors in a raw occured!", occurances)
        return False
    logging.debug("metrics appear healthy: %d unhealthy occurances", occurances)
    return True

def main():
    # update_db(health_check())
    parse_log()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="verbose mode", action="store_true")
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    main()
