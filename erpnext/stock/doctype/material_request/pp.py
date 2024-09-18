
from __future__ import unicode_literals
import time
import frappe
from frappe.model.document import Document


@frappe.whitelist()
def create_production_plans(material_request):
    # Fetch the Material Request document
    material_request_doc = frappe.get_doc('Material Request', material_request)
    
    if not material_request_doc:
        frappe.throw(("Material Request not found"))

    # Initialize dictionaries to hold items for each Production Plan
    test_items = []
    other_items = []
    
    # Separate items based on item_code
    for item in material_request_doc.items:
        if item.item_code.startswith("Recipe"):
            test_items.append(item)
        else:
            other_items.append(item)
    
    # Function to create a Production Plan
    def create_production_plan(items, pp_name_suffix):
        # Create a new Production Plan document
        production_plan = frappe.new_doc('Production Plan')
        production_plan.naming_series = 'MFG-PP-.YYYY.-'  # Adjust naming series if needed
        production_plan.company = material_request_doc.company  # Set the company from the Material Request
        production_plan.get_items_from = 'Material Request'
        production_plan.material_request = material_request_doc.name
        production_plan.new_doc = material_request_doc.new_doc
        production_plan.lookup_item = material_request_doc.lookup_item
        production_plan.schedule_date = material_request_doc.schedule_date
        production_plan.posting_date = frappe.utils.nowdate()

        # Add entries to the Material Requests table in the Production Plan
        production_plan.append('material_requests', {
            'material_request': material_request_doc.name,  # Link field
            'id': material_request_doc.name,  # Data field (assuming name or ID field)
            'material_request_date': material_request_doc.schedule_date  # Date field
        })

        # Add items from Material Request to Production Plan
        for item in items:
            production_plan.append('po_items', {
                'item_code': item.item_code,
                'bom_no': item.bom_no,
                'planned_qty': item.qty,
                'pending_qty': item.qty,
                'description': item.description,
                'stock_uom': item.uom,
                'warehouse': item.warehouse,
                'make_work_order_for_sub_assembly_items': item.make_work_order_for_sub_assembly_items,
                'wip_warehouse': item.wip_warehouse,
                'workstation': item.workstation,
            })
        

        # Save and submit the Production Plan
        production_plan.save()
        # time.sleep(4)
        production_plan.submit()

        return production_plan.name

    # Create Production Plans for test items and other items
    if test_items:
        test_pp_name = create_production_plan(test_items, "Recipe")
        # Link the Production Plan for test items to the Material Request
        material_request_doc.test_production_plan = test_pp_name

    if other_items:
        other_pp_name = create_production_plan(other_items, "other")
        # Link the Production Plan for other items to the Material Request
        material_request_doc.other_production_plan = other_pp_name

    # Save changes to the Material Request
    # material_request_doc.save()

    return {
        'test_production_plan': material_request_doc.test_production_plan,
        'other_production_plan': material_request_doc.other_production_plan
    }





