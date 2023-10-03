import frappe
from frappe.model.document import Document
import requests
from frappe.utils import now
from datetime import datetime


class BiometricData(Document):
    pass

@frappe.whitelist()
def fetch_and_save_biometric_data():
	today_date = frappe.utils.nowdate()
	# API endpoint URL
	api_url = "http://" + frappe.db.get_value('Biometric Settings','Biometric Settings','biometric_api')
	
	# API parameters
	api_key = frappe.db.get_value('Biometric Settings','Biometric Settings','biometric_api_key')
	
	# Prepare request parameters
	params = {
		"APIKey": api_key,
		"FromDate": today_date,
		"ToDate": today_date
	}
	now = datetime.now()
	today_date_time = now.strftime("%d-%m-%Y %H:%M:%S")
	try:
		# Send GET request to the API
		response = requests.get(api_url, params=params)
		
		# Check if the request was successful (status code 200)
		if response.status_code == 200:
			# Parse the response JSON
			data = response.json()
		
			data_list = []
			# Iterate over the logs and save them to "Biometric Data" DocType
			for log in data:
				employee_code = log['EmployeeCode']
				serial_number = log['SerialNumber']
				log_date = datetime.strptime(log['LogDate'],"%Y-%m-%d %H:%M:%S")
				
				db_data = frappe.db.sql(
					f"""
					SELECT device_id,device_location_floor,device_location_state,device_location_city FROM `tabBiometric Device Master` where name = '{serial_number}';
					"""
				,as_dict=1)
			
				employee_name = frappe.db.get_value('Employee',{'attendance_device_id':employee_code},'name')
				json_data = {'EmployeeCode':employee_name,'SerialNumber':serial_number,'LogDate':log_date,'DeviceFloor':db_data[0]['device_location_floor'],'DeviceState':db_data[0]['device_location_state'],'DeviceID':db_data[0]['device_id'],'DeviceCity':db_data[0]['device_location_city']}
				data_list.append(json_data)

			return data_list,today_date_time.split('.')[0]
		else:
			frappe.msgprint(("Failed to fetch biometric data."))
			frappe.log_error("Failed to fetch biometric data.")
	except requests.exceptions.RequestException as e:
		# Handle connection or request error
		frappe.log_error(frappe.get_traceback(),e)
