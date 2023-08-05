frappe.ui.form.on('Biometric Settings', {
	validate_employee_checkin: function(frm) {
		frappe.call({
			method:'gurukrupa_biometric.gurukrupa_biometric.doc_events.employee_checkin.validate_data',
		});
	}
});
