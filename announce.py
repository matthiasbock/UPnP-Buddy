#!/usr/bin/python

#
# main server functions
#

import bobo

@bobo.query('/brother.xml', content_type='text/xml')
def brother():
	return open('xml').read()
