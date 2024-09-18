# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import throw, _
from frappe.utils import cstr
from erpnext.accounts.party import validate_party_accounts
from frappe.contacts.address_and_contact import load_address_and_contact, delete_contact_and_address
from frappe.desk.reportview import build_match_conditions, get_filters_cond

class HealthcarePractitioner(Document):
	def onload(self):
		load_address_and_contact(self)

	def autoname(self):
		# practitioner first_name and last_name
		self.name = " ".join(filter(None,
			[cstr(self.get(f)).strip() for f in ["first_name","middle_name","last_name"]]))

	def validate(self):
		validate_party_accounts(self)
		if self.inpatient_visit_charge_item:
			validate_service_item(self.inpatient_visit_charge_item, "Configure a service Item for Inpatient Visit Charge Item")
		if self.op_consulting_charge_item:
			validate_service_item(self.op_consulting_charge_item, "Configure a service Item for Out Patient Consulting Charge Item")

		if self.user_id:
			self.validate_for_enabled_user_id()
			self.validate_duplicate_user_id()
			existing_user_id = frappe.db.get_value("Healthcare Practitioner", self.name, "user_id")
			if self.user_id != existing_user_id:
				frappe.permissions.remove_user_permission(
					"Healthcare Practitioner", self.name, existing_user_id)

		else:
			existing_user_id = frappe.db.get_value("Healthcare Practitioner", self.name, "user_id")
			if existing_user_id:
				frappe.permissions.remove_user_permission(
					"Healthcare Practitioner", self.name, existing_user_id)

	def on_update(self):
		if self.user_id:
			frappe.permissions.add_user_permission("Healthcare Practitioner", self.name, self.user_id)


	def validate_for_enabled_user_id(self):
		enabled = frappe.db.get_value("User", self.user_id, "enabled")
		if enabled is None:
			frappe.throw(_("User {0} does not exist").format(self.user_id))
		if enabled == 0:
			frappe.throw(_("User {0} is disabled").format(self.user_id))

	def validate_duplicate_user_id(self):
		practitioner = frappe.db.sql_list("""select name from `tabHealthcare Practitioner` where
			user_id=%s and name!=%s""", (self.user_id, self.name))
		if practitioner:
			throw(_("User {0} is already assigned to Healthcare Practitioner {1}").format(
				self.user_id, practitioner[0]), frappe.DuplicateEntryError)

	def on_trash(self):
		delete_contact_and_address('Healthcare Practitioner', self.name)

def validate_service_item(item, msg):
	if frappe.db.get_value("Item", item, "is_stock_item") == 1:
		frappe.throw(_(msg))

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_practitioner_list(doctype, txt, searchfield, start, page_len, filters=None):
	fields = ["name", "first_name", "mobile_phone"]

	filters = {
		'name': ("like", "%%%s%%" % txt)
	}

	return frappe.get_all("Healthcare Practitioner", fields = fields,
		filters = filters, start=start, page_length=page_len, order_by="name, first_name", as_list=1)
