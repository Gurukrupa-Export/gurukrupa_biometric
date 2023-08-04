frappe.listview_settings['Employee Checkin'] = {
    onload: function(listview) {
        frappe.call({
            method: 'gurukrupa_biometric.gurukrupa_biometric.doc_events.employee_checkin.fetch_and_save_biometric_data',
        });
        frappe.call({
            method: 'gurukrupa_biometric.gurukrupa_biometric.doc_events.employee_checkin.set_unique_id',
        });


        listview.page.add_menu_item(__("Validate Data"), function() {
            frappe.call({
                method:'gurukrupa_biometric.gurukrupa_biometric.doc_events.employee_checkin.validate_data',
            });
        });
        
    },
};