import os
import time

from bottle import route, run, template, request, abort, post, static_file, response
from passlib.hash import sha256_crypt
import boto.ec2
import pygeoip

# NOTE(joshk): must specify AWS_ACCESS_KEY_ID
# NOTE(joshk): must specify AWS_SECRET_ACCESS_KEY

# There are more valid regions than this but we only care about these four
# for our hosting solution.
VALID_REGIONS = ['us-west-1', 'eu-west-1', 'ap-southeast-1']
# NOTE(joshk): must specify PASSWD as a hash of user -> sha256_crypt password

STATE_STOPPED = 'stopped'
STATE_RUNNING = 'running'

GEOIP = pygeoip.Database('GeoIP.dat')

class EC2Wrapper(object):
   def __init__(self):
      self.connections = {}

   def getConnection(self, region):
      if region not in VALID_REGIONS:
         raise Exception('Invalid region: %s' % region)
      elif region in self.connections:
         return self.connections[region]
      else:
         conn = EC2Connection(boto.ec2.connect_to_region(region,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY))
         self.connections[region] = conn
         return conn

class EC2Connection(object):
   def __init__(self, conn):
      self.conn = conn
      self.instanceCache = None

   def getInstanceForUser(self, username):
      userFilter = {
         'tag-key': 'user',
         'tag-value': username,
      }
      return self.conn.get_all_instances(filters=userFilter)[0].instances[0]

   def getStatusForInstance(self, instance):
      return self.conn.get_all_instance_status(instance_ids=instance.id)

EC2 = EC2Wrapper()

def desktopValidateArgs(explicit_args):
   if request.json:
      args = dict(explicit_args, **request.json)
   else:
      args = explicit_args

   if 'username' not in args:
      abort(400, 'No username provided')
   if 'password' not in args:
      abort(400, 'No password provided')
   if 'region' not in args:
      abort(400, 'No region provided')
   if not args['username'] in PASSWD or \
      not sha256_crypt.verify(args['password'], PASSWD[args['username']]):
      abort(401, 'Wrong username or password')
   if args['region'] not in VALID_REGIONS:
      abort(400, 'Not a valid region')

   return args

@route('/desktop/closest')
def desktopClosest():
   ai = GEOIP.lookup(request.remote_addr)
   # TODO(joshk): finish me
   return 'us-west-1'

@post('/desktop/enable')
def desktopEnable(**kwargs):
   args = desktopValidateArgs(kwargs)
   conn = EC2.getConnection(args['region'])
   instance = conn.getInstanceForUser(args['username'])
   if not instance:
      abort(500, 'No such instance or user')
   if instance.state == STATE_RUNNING:
      return
   while instance.state != STATE_STOPPED:
      print 'Waiting for old shutdown to complete before powering on.'
      time.sleep(2)
   instance.start()

@post('/desktop/disable')
def desktopDisable(**kwargs):
   args = desktopValidateArgs(kwargs)
   conn = EC2.getConnection(args['region'])
   instance = conn.getInstanceForUser(args['username'])
   if not instance:
      abort(500, 'No such instance or user')
   if instance.state == STATE_STOPPED:
      return
   while instance.state != STATE_RUNNING:
      print 'Waiting for old power-on to complete before shutting down'
      time.sleep(2)
   instance.stop()

@post('/desktop/ip')
def desktopIp(**kwargs):
   args = desktopValidateArgs(kwargs)
   conn = EC2.getConnection(args['region'])
   instance = conn.getInstanceForUser(args['username'])

   first = True
   while instance.state != STATE_RUNNING:
      if first:
         print '(1) Instance is powering on.'
         first = False
      time.sleep(2)
      instance = conn.getInstanceForUser(args['username'])

   first = True
   while not instance.ip_address:
      if first:
         print '(2) Waiting for instance to get an IP address.'
         first = False
      time.sleep(2)
      instance = conn.getInstanceForUser(args['username'])

   instanceStatus = conn.getStatusForInstance(instance)
   first = True
   while len(instanceStatus) == 0 or instanceStatus[0].instance_status.status != 'ok':
      if first:
         print '(3) Waiting for instance to pass instance status check'
         first = False
      time.sleep(2)
      instanceStatus = conn.getStatusForInstance(instance)
   return instance.ip_address

@route('/desktop/rdp/:user/:ip.rdp')
def desktopRdp(user, ip):
   response.set_header('Content-Type', 'application/x-rdp')
   return '''
full address:s:%s
server port:i:3389
username:s:%s
audiomode:i:0
save:i:0

ServerName:s:%s
AudioRedirectionMode:i:0
''' % (ip, user, ip)

@route('/<filename:path>')
def serveStatic(filename):
   return static_file(filename, root='.')

if __name__ == '__main__':
   run(host='0.0.0.0', port=8080)
