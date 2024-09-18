// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Balance QTY', {
    onload: function(frm) {
        frm.set_query('stock_entry', function() {
            return {
                filters: {
                    docstatus: 1 // Filters only submitted entries (docstatus=1)
                },
                order_by: 'creation desc', // Orders by the latest creation date
                limit_page_length: 1 // Only show the latest entry
            };
        });
    }
});


frappe.ui.form.on('Balance QTY', {
    after_save: function(frm) {
        // Ensure that trak_id is present before making the call
        if (frm.doc.trak_id) {
            frappe.call({
                method: 'erpnext.manufacturing.doctype.balance_qty.balance_qty.update_cost_for_balance_qty',  // Replace with the actual path to your method
                args: {
                    trak_id: frm.doc.trak_id
                },
                freeze: true,  // Optionally freeze the UI while processing
                callback: function(r) {
                    if (!r.exc) {
                        // If the server-side function succeeded
                        frappe.msgprint(__('Cost updated successfully.'));
                        frm.reload_doc();  // Refresh the form to show updated values
                    } else {
                        // If an error occurred
                        frappe.msgprint(__('Error updating cost: ' + r.exc));
                    }
                }
            });
        } else {
            frappe.msgprint(__('TRAK ID is not set. Please save the document with a valid TRAK ID.'));
        }
    }
});

