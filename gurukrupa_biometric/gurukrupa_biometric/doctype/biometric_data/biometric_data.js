frappe.ui.form.on('Biometric Data', {
	onload: function(frm) {
		if (cur_frm.doc.docstatus ==0){
			cur_frm.clear_table('employee_log');
			frappe.call({
				method: 'gurukrupa_biometric.gurukrupa_biometric.doctype.biometric_data.biometric_data.fetch_and_save_biometric_data',
				callback: function(response) {
					if(response.message){
						cur_frm.set_value('date_time',response.message[1])
						var arrayLength = response.message[0].length;
						console.log(response.message[0])
						for (var i = 0; i < arrayLength; i++) {
							let row = frm.add_child('employee_log', {
								employee:response.message[0][i].EmployeeCode,
								device_serial_no:response.message[0][i].SerialNumber,
								time:response.message[0][i].LogDate,
								device_location_floor:response.message[0][i].DeviceFloor,
								device_location_state:response.message[0][i].DeviceState,
								device_id:response.message[0][i].DeviceID,
								device_location_city:response.message[0][i].DeviceCity,
							});
						}
						frm.refresh_field('employee_log');
					}
				}
			});
		}
    },
});

