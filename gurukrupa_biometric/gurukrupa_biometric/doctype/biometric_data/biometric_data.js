frappe.ui.form.on('Biometric Data', {
	// onload: function(frm) {
	// 		frappe.call({
	// 			method: 'gurukrupa_biometric.gurukrupa_biometric.doctype.biometric_data.biometric_data.fetch_and_save_biometric_data',
	// 			callback: function(response) {
	// 				console.log(response);
					
	// 				if(response.message){
	// 					cur_frm.set_value('date_time',response.message[1])
	// 					var arrayLength = response.message.length;
	// 					console.log(response.message)
	// 					for (var i = 0; i < arrayLength; i++) {
	// 						let row = frm.add_child('employee_log', {
	// 							employee:response.message[i].EmployeeCode,
	// 							device_serial_no:response.message[i].SerialNumber,
	// 							time:response.message[i].LogDate,
	// 							employee_name:response.message[i].Full_name,
	// 							// device_location_floor:response.message[i].DeviceFloor,
	// 							// device_location_state:response.message[i].DeviceState,
	// 							// device_id:response.message[i].DeviceID,
	// 							// device_location_city:response.message[i].DeviceCity,
	// 						});
	// 					}
	// 					frm.refresh_field('employee_log');
	// 				}
	// 			}
	// 		});
    // },
	refresh: function(frm) {
		frm.add_custom_button('Fetch Biometric Logs', function() {
			frappe.call({
				method: 'gurukrupa_biometric.gurukrupa_biometric.doctype.biometric_data.biometric_data.fetch_and_save_data',
				args: {
					docname: frm.doc.name
				},
				callback: function(r) {
					if (!r.exc) {						
						frappe.msgprint("Biometric logs fetched successfully");
						frm.reload_doc();
					}
					else{
						frappe.msgprint("Biometric logs not fetched");
					}
				}
			});
		});
		frm.add_custom_button('Sandwitch Rule', function() {
			frappe.call({ 
				method: 'gke_customization.gke_hrms.utils.check_sadwitch_rule',
				args: {
					docname: frm.doc.name
				},
				callback: function(r) {
					if (!r.exc) {						
						frappe.msgprint("check_sadwitch_rule successfully");
						frm.reload_doc();
					}
					else{
						frappe.msgprint("check_sadwitch_rule not fetched");
					}
				}
			});
		});
	}
});

