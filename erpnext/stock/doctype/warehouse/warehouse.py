# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe.utils import cint, flt
from frappe import throw, _
from collections import defaultdict
from frappe.utils.nestedset import NestedSet

from erpnext.stock import get_warehouse_account
from frappe.contacts.address_and_contact import load_address_and_contact

class Warehouse(NestedSet):
	nsm_parent_field = 'parent_warehouse'

	def autoname(self):
		if self.company:
			suffix = " - " + frappe.get_cached_value('Company',  self.company,  "abbr")
			if not self.warehouse_name.endswith(suffix):
				self.name = self.warehouse_name + suffix
				return

		self.name = self.warehouse_name

	def onload(self):
		'''load account name for General Ledger Report'''
		if self.company and cint(frappe.db.get_value("Company", self.company, "enable_perpetual_inventory")):
			account = self.account or get_warehouse_account(self)

			if account:
				self.set_onload('account', account)
		load_address_and_contact(self)

	def on_update(self):
		self.update_nsm_model()

	def update_nsm_model(self):
		frappe.utils.nestedset.update_nsm(self)

	def on_trash(self):
		# delete bin
		bins = frappe.db.sql("select * from `tabBin` where warehouse = %s",
			self.name, as_dict=1)
		for d in bins:
			if d['actual_qty'] or d['reserved_qty'] or d['ordered_qty'] or \
					d['indented_qty'] or d['projected_qty'] or d['planned_qty']:
				throw(_("Warehouse {0} can not be deleted as quantity exists for Item {1}").format(self.name, d['item_code']))
			else:
				frappe.db.sql("delete from `tabBin` where name = %s", d['name'])

		if self.check_if_sle_exists():
			throw(_("Warehouse can not be deleted as stock ledger entry exists for this warehouse."))

		if self.check_if_child_exists():
			throw(_("Child warehouse exists for this warehouse. You can not delete this warehouse."))

		self.update_nsm_model()

	def check_if_sle_exists(self):
		return frappe.db.sql("""select name from `tabStock Ledger Entry`
			where warehouse = %s limit 1""", self.name)

	def check_if_child_exists(self):
		return frappe.db.sql("""select name from `tabWarehouse`
			where parent_warehouse = %s limit 1""", self.name)

	def convert_to_group_or_ledger(self):
		if self.is_group:
			self.convert_to_ledger()
		else:
			self.convert_to_group()

	def convert_to_ledger(self):
		if self.check_if_child_exists():
			frappe.throw(_("Warehouses with child nodes cannot be converted to ledger"))
		elif self.check_if_sle_exists():
			throw(_("Warehouses with existing transaction can not be converted to ledger."))
		else:
			self.is_group = 0
			self.save()
			return 1

	def convert_to_group(self):
		if self.check_if_sle_exists():
			throw(_("Warehouses with existing transaction can not be converted to group."))
		else:
			self.is_group = 1
			self.save()
			return 1

@frappe.whitelist()
def get_children(doctype, parent=None, company=None, is_root=False):
	if is_root:
		parent = ""

	fields = ['name as value', 'is_group as expandable']
	filters = [
		['docstatus', '<', '2'],
		['ifnull(`parent_warehouse`, "")', '=', parent],
		['company', 'in', (company, None,'')]
	]

	warehouses = frappe.get_list(doctype, fields=fields, filters=filters, order_by='name')

	company_currency = ''
	if company:
		company_currency = frappe.get_cached_value('Company', company, 'default_currency')

	warehouse_wise_value = get_warehouse_wise_stock_value(company)

	# return warehouses
	for wh in warehouses:
		wh["balance"] = warehouse_wise_value.get(wh.value)
		if company_currency:
			wh["company_currency"] = company_currency
	return warehouses

def get_warehouse_wise_stock_value(company):
	warehouses = frappe.get_all('Warehouse',
		fields = ['name', 'parent_warehouse'], filters = {'company': company})
	parent_warehouse = {d.name : d.parent_warehouse for d in warehouses}

	filters = {'warehouse': ('in', [data.name for data in warehouses])}
	bin_data = frappe.get_all('Bin', fields = ['sum(stock_value) as stock_value', 'warehouse'],
		filters = filters, group_by = 'warehouse')

	warehouse_wise_stock_value = defaultdict(float)
	for row in bin_data:
		if not row.stock_value:
			continue

		warehouse_wise_stock_value[row.warehouse] = row.stock_value
		update_value_in_parent_warehouse(warehouse_wise_stock_value,
			parent_warehouse, row.warehouse, row.stock_value)

	return warehouse_wise_stock_value

def update_value_in_parent_warehouse(warehouse_wise_stock_value, parent_warehouse_dict, warehouse, stock_value):
	parent_warehouse = parent_warehouse_dict.get(warehouse)
	if not parent_warehouse:
		return

	warehouse_wise_stock_value[parent_warehouse] += flt(stock_value)
	update_value_in_parent_warehouse(warehouse_wise_stock_value, parent_warehouse_dict,
		parent_warehouse, stock_value)

@frappe.whitelist()
def add_node():
	from frappe.desk.treeview import make_tree_args
	args = make_tree_args(**frappe.form_dict)

	if cint(args.is_root):
		args.parent_warehouse = None

	frappe.get_doc(args).insert()

@frappe.whitelist()
def convert_to_group_or_ledger():
	args = frappe.form_dict
	return frappe.get_doc("Warehouse", args.docname).convert_to_group_or_ledger()

def get_child_warehouses(warehouse):
	lft, rgt = frappe.get_cached_value("Warehouse", warehouse, ["lft", "rgt"])

	return frappe.db.sql_list("""select name from `tabWarehouse`
		where lft >= %s and rgt <= %s""", (lft, rgt))

def get_warehouses_based_on_account(account, company=None):
	warehouses = []
	for d in frappe.get_all("Warehouse", fields = ["name", "is_group"],
		filters = {"account": account}):
		if d.is_group:
			warehouses.extend(get_child_warehouses(d.name))
		else:
			warehouses.append(d.name)

	if (not warehouses and company and
		frappe.get_cached_value("Company", company, "default_inventory_account") == account):
		warehouses = [d.name for d in frappe.get_all("Warehouse", filters={'is_group': 0})]

	if not warehouses:
		frappe.throw(_("Warehouse not found against the account {0}")
			.format(account))

	return warehouses
