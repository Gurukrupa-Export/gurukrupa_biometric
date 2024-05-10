
from hrms.hr.doctype.shift_assignment.shift_assignment import get_employee_shift_timings
from frappe.utils import cint, add_to_date, get_datetime, get_datetime_str
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_datetime
import requests
from datetime import datetime,timedelta
import frappe
from frappe.model.document import Document
import requests
from frappe.utils import now
from datetime import datetime

class BiometricData(Document):
    pass

@frappe.whitelist()
def fetch_and_save_biometric_data():
    
	today_date = datetime.now().date()
	formatted_today_date = today_date.strftime("%d%m%Y")
	old_date = today_date - timedelta(days=7)
	formatted_old_date = old_date.strftime("%d%m%Y")

	api_url = frappe.db.get_value('Biometric Settings','Biometric Settings','biometric_api')
	
	# API parameters
	api_key = frappe.db.get_value('Biometric Settings','Biometric Settings','biometric_api_key')

	# url = f"{api_url};date-range={formatted_old_date}-{formatted_today_date}"
	url = "http://3.6.177.5/cosec/api.svc/v2/event-ta?action=get;field-name=indexno,userid,username,eventdatetime,entryexittype,mastercontrollerid,device_name;format=json;date-range=26032024-26032024"

	payload = {}
	headers = {
	'Authorization': api_key,
	'Cookie': 'ASP.NET_SessionId=4t2hfqzatrgd4akbdje2xjr4'
	}

	response = requests.request("GET", url, headers=headers, data=payload)
	data = response.json()["event-ta"]
	data_list = []
	for log in data:
		skip = validate_time_threshold(log)
		if skip:
			continue
		
		# employee_code = log['EmployeeCode']
		employee_code = log['userid']

		# serial_number = log['SerialNumber']
		serial_number = log['device_name']

		# log_date = log['LogDate']
		log_date = log['eventdatetime']
		

		parsed_date = datetime.strptime(log_date, "%d/%m/%Y %H:%M:%S")
		formatted_date = parsed_date.strftime("%Y-%m-%d %H:%M")
		employee = frappe.db.get_value("Employee",{"attendance_device_id":employee_code},'name')
		if employee:
			employee_full_name = frappe.db.get_value("Employee",{"attendance_device_id":employee_code},'employee_name')
			d = {"EmployeeCode":employee,"Full_name":employee_full_name,"SerialNumber":serial_number,"LogDate":formatted_date}
			data_list.append(d)
	return data_list

def validate_time_threshold(log):
	time_threshold = frappe.db.get_value('Biometric Settings','Biometric Settings','time_threshold')
	employee = frappe.db.get_value("Employee",{"attendance_device_id":log["userid"]},"name")
	last_punch = frappe.db.get_list("Employee Checkin",filters={"employee":employee},fields=["time"],order_by='time desc')
	if last_punch:
		date_object = datetime.strptime(log['eventdatetime'], "%d/%m/%Y %H:%M:%S")
		diff = date_object - last_punch[0]['time']

		if diff.total_seconds()<=float(time_threshold):
			return 1