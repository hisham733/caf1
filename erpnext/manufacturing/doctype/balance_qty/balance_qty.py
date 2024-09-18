# -*- coding: utf-8 -*-
# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import logging
import time
import frappe
from frappe.model.document import Document

class BalanceQTY(Document):

    def on_submit(self):
        try:
            # Check if the items table is not empty
            if self.items:
                last_item = self.items[-2]  # Fetch the last item in the table

                # Create a new Stock Entry (Material Receipt)
                stock_entry = frappe.new_doc("Stock Entry")
                stock_entry.stock_entry_type = "Material Receipt"
                stock_entry.purpose = "Material Receipt"
                stock_entry.to_warehouse = self.target_warehouse
            #     stock_entry.reference_doctype = "Balance Qty"
                stock_entry.balance = self.name  # Reference name for linking

                # Set the target warehouse as the source warehouse for Stock Entry
                stock_entry.set('items', [{
                    'item_code': last_item.item_code,
                    'qty': self.balance,  # Quantity is the balance in Balance Qty
                    's_warehouse': self.target_warehouse,  # Use target warehouse as source
                    't_warehouse': None  # Set target warehouse if needed
                }])

                # Save and submit the Stock Entry
                stock_entry.insert()
                stock_entry.submit()

                # Show success message to user
                frappe.msgprint(f"Stock Entry {stock_entry.name} created successfully.")

            else:
                frappe.throw("No items found to process in Balance Qty.", title="No Items Found")

        except frappe.ValidationError as e:
            # Handle validation issues in Frappe framework
            frappe.throw(f"Validation Error: {e}", title="Validation Error")

        except Exception as e:
            # General error handling for any other issues
            frappe.throw(f"An error occurred: {e}", title="Stock Entry Creation Error")
            frappe.log_error(message=frappe.get_traceback(), title="Stock Entry Creation Error")


# # custom_app/custom_app/api.py


logger = logging.getLogger(__name__)

def get_outgoing_cost(trak_id):
    try:
        # Fetch stock entries based on trak_id and production_items like 'Recipe%'
        stock_entries = frappe.get_all('Stock Entry', filters={
            'id': trak_id,
            'docstatus': 1,
            'production_items': ['like', 'Recipe%'],  # Fetch production_items starting with 'Recipe'
        }, fields=['name', 'production_items'])  # Added 'production_items' to fields

        if not stock_entries:
            error_message = f"No stock entries found for the given trak_id: {trak_id}"
            frappe.throw(error_message)  # Stop execution if no stock entries found
            return 0, 0, 0, None, None

        stock_entry_names = [entry.name for entry in stock_entries]
        production_items = stock_entries[0].get('production_items')  # Get the production_items from Stock Entry

        # Fetch stock entry details (optional, in case you need item_name for other logic)
        stock_entry_details = frappe.get_all('Stock Entry Detail', filters={
            'parent': ['in', stock_entry_names],
            'item_name': ['like', 'Recipe%']
        }, fields=['item_name', 'qty'], order_by='creation desc')

        if not stock_entry_details:
            error_message = f"No stock entry details found for stock entries: {stock_entry_names}"
            frappe.throw(error_message)  # Stop execution if no stock entry details found
            return 0, 0, 0, stock_entry_names[0], production_items  # Return production_items

        # Get the quantity from the last row where item_name starts with 'Recipe'
        last_item = stock_entry_details[0]
        cost_qty = last_item.qty

        if cost_qty == 0:
            error_message = "Quantity is zero, division not possible."
            frappe.throw(error_message)  # Stop execution if quantity is zero
            return 0, 0, 0, stock_entry_names[0], production_items  # Return production_items

        # Fetch total outgoing value
        stock_entries_with_recipe = frappe.get_all('Stock Entry', filters={
            'name': ['in', stock_entry_names]
        }, fields=['total_outgoing_value'])

        if not stock_entries_with_recipe:
            error_message = f"No stock entries found with total outgoing value for: {stock_entry_names}"
            frappe.throw(error_message)  # Stop execution if no total outgoing value found
            return 0, 0, 0, stock_entry_names[0], production_items  # Return production_items

        total_outgoing_value = stock_entries_with_recipe[0].get('total_outgoing_value')

        # Fetch balance field from Balance QTY doctype
        balance_qty_doc = frappe.get_all('Balance QTY', filters={'trak_id': trak_id}, fields=['balance'])
        
        if not balance_qty_doc:
            error_message = f"Balance QTY document with trak_id {trak_id} not found."
            frappe.throw(error_message)  # Stop execution if no Balance QTY document found

        balance = balance_qty_doc[0].get('balance')

        # Ensure balance is not zero to avoid division errors
        if balance == 0:
            error_message = "Balance is zero, division not possible."
            frappe.throw(error_message)  # Stop execution if balance is zero

        cost_after_division = (total_outgoing_value / cost_qty) * balance

        # Returning stock entry ID (first in list) and production items
        return total_outgoing_value, cost_qty, cost_after_division, stock_entry_names[0], production_items

    except Exception as e:
        # Log error and throw it to stop execution
        frappe.log_error(message=str(e), title="Error in get_outgoing_cost")
        frappe.throw(f"Error in get_outgoing_cost: {str(e)}")  # Throwing the error to stop execution


@frappe.whitelist()
def update_cost_for_balance_qty(trak_id):
    try:
        # Call the function to get the outgoing cost data
        total_outgoing_value, cost_qty, cost_after_division, stock_entry_production, production_name = get_outgoing_cost(trak_id)
        
        # Retry mechanism for concurrency issues
        retry_count = 3
        for attempt in range(retry_count):
            try:
                # Fetch Balance QTY document
                balance_qty_docs = frappe.get_all('Balance QTY', filters={'trak_id': trak_id})
                
                if not balance_qty_docs:
                    error_message = f"Balance QTY document with trak_id {trak_id} not found."
                    frappe.throw(error_message)  # Stop execution if no Balance QTY document found

                # Get the first Balance QTY document
                balance_qty_doc = frappe.get_doc('Balance QTY', balance_qty_docs[0].name)

                # Update the fields
                balance_qty_doc.cost = total_outgoing_value
                balance_qty_doc.cost_qty = cost_qty
                balance_qty_doc.cost_after_division = cost_after_division
                balance_qty_doc.stock_entry_production = stock_entry_production
                balance_qty_doc.production_name = production_name  # Update production_name with production_items
                balance_qty_doc.save()

                # Return the updated values
                return {
                    "cost": total_outgoing_value,
                    "cost_qty": cost_qty,
                    "cost_after_division": cost_after_division,
                    "stock_entry_production": stock_entry_production,
                    "production_name": production_name  # Returning updated production_name
                }

            except frappe.ValidationError as e:
                # Handle document modification errors
                if "Document has been modified after you have opened it" in str(e):
                    if attempt < retry_count - 1:
                        # Retry after a short delay
                        time.sleep(1)
                        continue  # Retry fetching and saving the document
                raise  # Reraise exception if retry attempts are exhausted

    except frappe.DoesNotExistError:
        error_message = f"Balance QTY document with trak_id {trak_id} not found."
        frappe.log_error(message=error_message, title="Balance QTY Document Not Found")
        frappe.throw(error_message)  # Stop execution and throw error

    except Exception as e:
        # Log and throw any other unexpected error
        frappe.log_error(message=str(e), title="Error in update_cost_for_balance_qty")
        frappe.throw(f"Error in update_cost_for_balance_qty: {str(e)}")
