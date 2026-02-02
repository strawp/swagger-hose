#!/usr/bin/env python3

import argparse, json, requests, glob, os, urllib3, yaml
urllib3.disable_warnings()

class ServiceDefinition( object ):

  requiredonly = False
  params = {}
  variables = {}
  definition = {}
  title = ''
  defaults = {
    "string": "asdf",
    "integer": 1,
    "boolean": True,
    "date-time":'2000-01-01 00:00:00',
    "array":[]
  }
  requiredonly = False
  norequests = False
  allowedmethods = None
  headers = []
  proxies = None
  debug = False

  def __init__( self, filename ):
    with open( filename ) as f:
      data = f.read()
      
    if filename.endswith( '.json' ):
      self.definition = json.loads(data)
    else:
      self.definition = yaml.safe_load(data)
      
    if 'info' in self.definition and 'title' in self.definition['info']:
      self.title = self.definition['info']['title']


  def get_definition( self, ref ):
    if self.debug: print('Getting definition of ', ref )
    schema = self.definition
    for r in ref.replace('#','').split('/'):
      if len(r) == 0: continue
      if r in schema:
        schema = schema[r]
    if self.debug: print( schema )
    return schema

  def get_example( self, ref ):
    if self.debug: print( 'Getting example for ', ref )
    dfn = self.get_definition( ref )
    if 'example' in dfn:
      if self.debug: print('Actual example found: ', dfn['example'])
      return dfn['example']
    rtn = {}
    required = None
    if 'required' in dfn:
      required = dfn['required']
    newdfn = {}
    for k,v in dfn.items():
      newdfn[k.lower()] = v
    dfn = newdfn
    if 'properties' in dfn:
      for name,p in dfn['properties'].items():
        if self.requiredonly and required and name not in required: continue
        rtn[name] = self.get_default_value( name, p )
    if self.debug: print( 'Constructed object: ', rtn )
    return rtn


  def get_default_value( self, name, p ):
    if self.debug: print( 'Get default value for: ', name, p )
    if name in self.params:
      v = self.params[name]
    elif 'type' not in p:
      if 'schema' in p:
        p = p['schema']
      if "$ref" in p:
        ref = p["$ref"]
        v = self.get_example(ref) 
      else:
        v = self.get_default_value( 'object', p )
    elif 'items' in p:
      if '$ref' in p['items']:
        v = json.dumps([self.get_example(p['items']['$ref'])])
      else:
        v = json.dumps([self.get_default_value('object',p['items'])])
    elif p['type'] in self.defaults:
      
      v = self.defaults[p['type']]
    else:
      v = 1
    return v

  def do_requests( self ):
    

    baseurls = []
    if 'openapi' in self.definition and int(self.definition['openapi'].split('.')[0]) >= 3:
      
      # OpenAPI 3+
      for server in self.definition.get('servers'):
        for k,v in server.get('variables',{}).items():
          if not k in self.variables:
            self.variables[k] = v.get('default')

        print('Variables:')
        for k,v in self.variables.items():
          print(k + ':', v )


        url = server.get('url')
        for k,v in self.variables.items():
          url = url.replace('{'+k+'}',v)
        
        baseurls.append( url )

    else:
      
      # Swagger 2
      if 'schemes' in self.definition: 
        schemes = self.definition['schemes']
      else: 
        schemes = ['https']
        for scheme in schemes:
          baseurl = scheme + '://' + self.definition['host'] + self.definition['basePath']
          baseurls.append( baseurl )

    for baseurl in baseurls:
      for path, methods in self.definition['paths'].items():
        for method, req in methods.items():
          url = baseurl + path
          usejson = False
          headers = self.headers
          if self.allowedmethods and method.lower() not in self.allowedmethods: continue
          print('')
          print( method.upper(), url )
          if 'summary' in req: print('Summary: ',req['summary'])
          if 'consumes' in req and len(req['consumes'])>0: 
            headers['Content-Type'] = req['consumes'][0]
          if 'Content-Type' in headers and 'json' in headers['Content-Type']: usejson = True
          query = {}
          body = {}
          print('Parameters:')
          if 'parameters' in req and req['parameters'] is not None:
            for p in req['parameters']:
              if self.requiredonly and 'required' in p and not p['required']: continue
              try:
                if '$ref' in p:
                  p = self.get_definition( p['$ref'] )
                v = self.get_default_value( p['name'], p )
              except Exception as e:
                print( e )
                print( p )
                continue

              if p['in'] == 'query':
                query[p['name']] = str(v)
              elif p['in'] == 'path':
                url = url.replace('{'+p['name']+'}',str(v))
              else:
                body[p['name']] = v
              print( ' - ', p['name'], v )
          if usejson: body = json.dumps(body)
          if self.debug: print(method, url, headers, query, body, self.proxies) 
          if not self.norequests:
            req = requests.request( method, url, headers=headers, params=query, data=body, proxies=self.proxies, verify=False )


def main():
  parser = argparse.ArgumentParser(description="A command line tool for squirting a bunch of requests into an API")
  parser.add_argument("--parameter","-p", nargs=2, action="append", help="Parameter to set")
  parser.add_argument("--variable","-v", nargs=2, action="append", help="Variable to set")
  parser.add_argument("--header","-H", nargs=2, action="append", type=str,  help="HTTP request header to set")
  parser.add_argument("--proxy", help="URL of proxy to send requests through")
  parser.add_argument("--allowedmethods", "-m", help="Comma-separated list of methods allowed. Default: all")
  parser.add_argument("--requiredonly", "-r", action="store_true", help="Only add in parameters that are required")
  parser.add_argument("--norequests", "-n", action="store_true", help="Don't actually make the requests")
  parser.add_argument("--debug", action="store_true", help="Turn on debug output")
  parser.add_argument("swaggerfile", type=str, help="Swagger JSON file")
  args = parser.parse_args()

  files = glob.glob( os.path.expanduser( args.swaggerfile ) )

  params = {}

  if args.parameter:
    print(args.parameter)
    for p in args.parameter:
      params[p[0]] = p[1]
  
  variables = {}
  if args.variable:
    print(args.variable)
    for p in args.variable:
      variables[p[0]] = p[1]
 
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
    service = ServiceDefinition( doc )
    service.params = params
    service.variables = variables
    service.headers = headers
    service.allowedmethods = allowedmethods
    service.requiredonly = args.requiredonly
    service.norequests = args.norequests
    service.proxies = proxies
    service.debug = args.debug
    print('\n\n'+service.title)
    service.do_requests()

if __name__ == "__main__":
  main()
