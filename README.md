# swagger-hose

*sWHARRGARBL*

Squirt a bunch of swagger requests into an API just to get some base requests to start from.

This is designed for those times when you've unearthed a large amount of API documentation and you want to quickly triage to something that you can authenticate with, and provide some basic default input on. e.g.

```
python swagger-hose.py -p orgid pentest -H X-Requested-By swagger-hose -m get,post --proxy http://localhost:8080 -p employeeKey user1 "~/working/data/swagger/*.json"
```

The above command will take all JSON files in `~/working/data/swagger/` and for each one pick out all the `GET` and `POST` requests, assign the parameters `orgid` with the value `pentest` and `employeeKey` with `user1` for anywhere these occur, add in the request header `X-Requested-By: swagger-hose` and then proxy it through Burp on my own machine.

Then in Burp I'll pick out any responses that aren't `40*` and have a further poke.

## TODO

 - [ ] Default values for variable types
 - [ ] yaml support
 - [ ] Test with something other than the swagger v2.0 files that I had on this one pentest I wrote this for

