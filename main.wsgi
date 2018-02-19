# Change working directory so relative paths (and template lookup) work again
import os
import sys
dname = os.path.dirname(__file__)
os.chdir(dname)
sys.path.append(dname)

import bottle
import main
application = bottle.default_app()
