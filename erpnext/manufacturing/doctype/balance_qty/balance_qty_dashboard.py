from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'balance',
		'transactions': [
			{
				'label': _('Related Stock Entries'),
				'items': ['Stock Entry']
			},

			
		]
	}

      