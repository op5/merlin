import os, sys
import time
import subprocess as sp


def cmd_generate(args):
	"""
	Generates a secure key for encrypting Merlin communication

	This command saves a encryption key to /opt/monitor/op5/merlin/key.
	This key can be used to encrypt communication with Merlin.
	"""

        if os.path.isfile('/opt/monitor/op5/merlin/key'):
            print 'File already exists. Key will not be generated.'
	    sys.exit(1)


	p = sp.Popen(['/usr/lib64/merlin/keygen'], stdout=sp.PIPE, stderr=sp.PIPE)
	if p.returncode != 0:
		printf 'Key generation failed'
		sys.exit(1)
	else:
		printf 'Key generated and saved at /op5/monitor/op5/merlin/key'
