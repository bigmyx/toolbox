import requests
import json
import time
import click
from os import path
from datetime import datetime, timezone, timedelta

import requests.packages.urllib3
requests.packages.urllib3.disable_warnings()

NAME = "shutup-script"
DESC = "alert by shutup-script"
CONFIG = json.load(open(path.join(path.dirname(__file__), "config.json")))

@click.group()
def cli():
    pass

@click.command()
@click.option("--duration", default=2, help="silence diration")
@click.option("--endpoint", required=True, help="ingress name for alertmanager")
def create_silence(endpoint, duration):
    api = f"https://{endpoint}/alertmanager/api/v1/silences"
    # import pdb; pdb.set_trace()
    utc_offset_sec = time.altzone if time.localtime().tm_isdst else time.timezone
    utc_offset = timedelta(seconds=-utc_offset_sec)

    starts = datetime.now().replace(tzinfo=timezone(offset=utc_offset)).isoformat()
    ends = (datetime.now() + timedelta(hours=duration)).replace(
        tzinfo=timezone(offset=utc_offset)).isoformat()

    template = {"id":"",
                "createdBy": NAME,
                "comment": DESC,
                "startsAt": starts,
                "endsAt": ends,
                "matchers": CONFIG["cassandra"]}
    r = requests.post(api, json=template, verify=False)

    click.echo(f"{r.status_code}\n{r.text}")

@click.command()
@click.option("--silid", required=True, help="silence ID")
@click.option("--endpoint", required=True, help="ingress name for alertmanager")
def clear_silence(endpoint, silid):
    r = requests.delete(f"https://{endpoint}/alertmanager/api/v1/silence/{silid}", verify=False)
    click.echo(f"{r.status_code}\n{r.text}")


if __name__ == '__main__':
    cli.add_command(create_silence)
    cli.add_command(clear_silence)
    cli()