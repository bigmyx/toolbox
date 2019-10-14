## Create a Silence in Prometheus AlertManager

The scripts creates and expires a Silence based on rules described in `config.json`

### Usage

#### Create Silence
```
$ python  shutup.py create-silence  --endpoint alertmgr.example.com
200
{"status":"success","data":{"silenceId":"30b36ae4-9e0a-4cd2-80da-f7e7fd747067"}}
```

#### Expire Silence
```
$ python  shutup.py clear-silence  --endpoint alertmgr.example.com
200
{"status":"success"}
```
