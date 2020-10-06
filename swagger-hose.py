#!/usr/bin/env python3

import argparse, json, requests, glob, os, urllib3
urllib3.disable_warnings()


def main():
  parser = argparse.ArgumentParser(description="A command line tool for squirting a bunch of requests into an API")
  parser.add_argument("--parameter","-p", nargs=2, action="append", help="Parameter to set")
  parser.add_argument("--header","-H", nargs=2, action="append", type=str,  help="HTTP request header to set")
  parser.add_argument("--proxy", help="URL of proxy to send requests through")
  parser.add_argument("--allowedmethods", "-m", help="Comma-separated list of methods allowed. Default: all")
  parser.add_argument("--requiredonly", "-r", action="store_true", help="Only add in parameters that are required")
  parser.add_argument("swaggerfile", type=str, help="Swagger JSON file")
  args = parser.parse_args()

  files = glob.glob( os.path.expanduser( args.swaggerfile ) )

  params = {}

  if args.parameter:
    print(args.parameter)
    for p in args.parameter:
      params[p[0]] = p[1]
 
  headers = {}
  if args.header:
    for h in args.header:
      headers[h[0]] = h[1]

  proxies = None
  if args.proxy:
    if args.proxy.startswith('http'):
      proxies = {'http':args.proxy,'https':args.proxy}
    else:
      proxies = {'socks':args.proxy}

  allowedmethods = None
  if args.allowedmethods:
    allowedmethods = args.allowedmethods.lower().split(',')

  for doc in files:
    print('\n\n')
    with open( doc ) as f:
      dfn = json.load(f)
    if 'info' in list(dfn.keys()) and 'title' in list(dfn['info'].keys()):
      print('\n\n'+dfn['info']['title'])
    if 'schemes' in list(dfn.keys()): 
      schemes = dfn['schemes']
    else: 
      schemes = ['https']
    for scheme in schemes:
      baseurl = scheme + '://' + dfn['host'] + dfn['basePath']
      for path, methods in dfn['paths'].items():
        url = baseurl + path
        for method, req in methods.items():
          if allowedmethods and method.lower() not in allowedmethods: continue
          if 'summary' in list(req.keys()): print(req['summary'])
          print( method, url )
          query = {}
          body = {}
          if 'parameters' in list(req.keys()):
            for p in req['parameters']:
              if args.requiredonly and 'required' in list(p.keys()) and not p['required']: continue
              if p['name'] in list(params.keys()):
                v = params[p['name']]
              elif 'type' not in list(p.keys()):
                v = 1
              elif p['type'] == 'string':
                v = "asdf"
              elif p['type'] == 'integer':
                v = 1
              elif p['type'] == 'array':
                v = []
              else:
                v = 1
              if p['in'] == 'query':
                query[p['name']] = str(v)
              elif p['in'] == 'path':
                url = url.replace('{'+p['name']+'}',str(v))
              else:
                body[p['name']] = v
              print( ' - ', p['name'], v )
          print(method, url, headers, query, body, proxies) 
          req = requests.request( method, url, headers=headers, params=query, data=body, proxies=proxies, verify=False )


if __name__ == "__main__":
  main()
