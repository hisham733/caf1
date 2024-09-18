import frappe

def fetch_delete_data(doc, method):
    if doc.new_doc:
        # Fetch the linked record from the 'New' DocType
        new_doc = frappe.get_doc('New', doc.new_doc)

        if new_doc:
            # Clear the existing rows in the delete table in Production Plan
            doc.delet = []

            # Loop through the delete table in the New DocType and add rows to the delete table in Production Plan
            for row in new_doc.delet:
                doc.append('delet', {
                    'item_name': row.item_name,  # Replace with actual field names
                    'description': row.description  # Replace with actual field names
                    # Add more fields as required
                })
