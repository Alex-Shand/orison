import os
import sys

import orison
from orison import command, sh

if os.geteuid() == 0:
    command.run(orison)
else:
    sh.run("sudo", *sys.argv, check=False, capture=False)
