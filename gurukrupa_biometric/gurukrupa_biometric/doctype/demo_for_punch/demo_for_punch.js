// Copyright (c) 2023, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.ui.form.on('Demo for Punch', {
	onload: function(frm) {
		frappe.call({
			method: 'gurukrupa_biometric.gurukrupa_biometric.doctype.demo_for_punch.demo_for_punch.fetch_and_save_biometric_data',
			callback: function(r) {
				if (!r.exc) {
					// code snippet
				}
			}
		});
	}
});
