# Copyright (c) 2023, Gurukrupa Export and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

class DemoforPunch(Document):
	pass


# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from hrms.hr.doctype.shift_assignment.shift_assignment import get_employee_shift_timings
from frappe.utils import cint, add_to_date, get_datetime, get_datetime_str
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_datetime
import requests
from datetime import datetime,timedelta


@frappe.whitelist()
def fetch_and_save_biometric_data():
	# now = datetime.now()
	# today_date = now.strftime("%Y-%m-%d")
	today_date = datetime.now().date()
	exist_emp_name = []
	for k in frappe.db.get_list('Employee Checkin',fields=['employee','time']):
		exist_emp_name.append(f'{k["employee"]}/{k["time"]}')
	
	
	api_url = "http://" + frappe.db.get_value('Biometric Settings','Biometric Settings','biometric_api')

	api_key = frappe.db.get_value('Biometric Settings','Biometric Settings','biometric_api_key')
	
	# Prepare request parameters
	params = {
		"APIKey": api_key,
		"FromDate": today_date - timedelta(days=10),
		"ToDate": today_date,
	}
	
	# frappe.db.get_list('Holiday','holiday_date')
	# frappe.throw('hold')
	try:
		# Send GET request to the API
		response = requests.get(api_url, params=params)

		# Check if the request was successful (status code 200)
		if response.status_code == 200:
			# Parse the response JSON
			data = response.json()
			# Iterate over the logs and save them to "Biometric Data" DocType
			
			for log in data[:]:
				employee_code = log['EmployeeCode']
				serial_number = log['SerialNumber']
				log_date = log['LogDate']
				frappe.msgprint('Document updated successfully')
				
				
				employee_name = frappe.db.get_value('Employee',{'attendance_device_id':employee_code},'name')
				if employee_name == None:
					frappe.log_error(f'Employee Not Found for this punch ID {employee_code}')
					continue
				if f'{employee_name}/{log_date}' in exist_emp_name:
					continue

				
				
				shift_det = get_employee_shift_timings(employee_name, get_datetime(log_date), True)[1]

				if get_datetime(log_date) > shift_det.actual_start and get_datetime(log_date) < shift_det.actual_end:
					if frappe.db.sql(f"""select log_type  from `tabEmployee Checkin` tec where employee = '{employee_name}' and DATE(time)='{log_date.split(' ')[0]}'""",as_dict=1) == []:
						log_type = 'IN'
					else:
						employee_chekin_data = frappe.db.sql(
						f"""SELECT log_type  from `tabEmployee Checkin` tec where employee ='{employee_name}' and time < '{log_date}' ORDER BY time DESC """
						,as_dict=1)


						if len(employee_chekin_data) == 0: log_type = 'IN'
						else:
							if employee_chekin_data[0]['log_type'] == 'IN':
								log_type = 'OUT'
							else:
								log_type = 'IN'
				else:
					log_type = 'IN'

				emp_data = frappe.get_doc({
					"doctype": "Employee Checkin",
					"employee": employee_name,
					"time":str(log_date),
					"device_id":f"{serial_number}",
					"source":"Biometric",
					"log_type": log_type
				})
				emp_data.insert()
			return 'ok'
		else:
			frappe.log_error(frappe.get_traceback(),f"Response code is: {response.status_code}. Check URL")
	except requests.exceptions.RequestException as e:
		frappe.log_error(frappe.get_traceback(),e)
	

@frappe.whitelist()
def set_unique_id():
	session = requests.Session()
	aws_api = frappe.db.get_value('Biometric Settings','Biometric Settings','aws_api')
	response = session.get(f'http://{aws_api}')
	data_list = response.json()
	for i in data_list:
		try:
			
			employee_name = frappe.db.get_value('Employee',{'attendance_device_id':i['punch_id']},'name')
			datetime_obj = datetime.strptime(i['log_time'],'%a, %d %b %Y %H:%M:%S GMT')

			if frappe.db.get_value('Employee Checkin',{'time':datetime.strftime(datetime_obj,"%Y-%m-%d %H:%M:%S"),'employee':employee_name},'custom_unique_id'): 
				continue

			emp_record = frappe.db.get_value('Employee Checkin',{'time':datetime.strftime(datetime_obj,"%Y-%m-%d %H:%M:%S"),'employee':employee_name},'name')
			frappe.db.set_value('Employee Checkin',emp_record,'custom_unique_id',i['id'])
		except:
			continue


@frappe.whitelist()
def validate_data():
	checkin_emp_data = []
	
	checkin_data = frappe.db.get_list('Employee Checkin',fields=['employee','time'])
	for i in checkin_data:
		checkin_emp_data.append(f'{i["employee"]}/{i["time"]}')
	
	session = requests.Session()
	aws_api = frappe.db.get_value('Biometric Settings','Biometric Settings','aws_api')
	response = session.get(f'http://{aws_api}')
	data_list = response.json()

	for j in data_list[:]:
		employee_name = frappe.db.get_value('Employee',{'attendance_device_id':j['punch_id']},'name')
		datetime_obj = datetime.strptime(j['log_time'],'%a, %d %b %Y %H:%M:%S GMT')

		if employee_name == None:
			frappe.log_error(f'Employee Not Found for this punch ID {j["punch_id"]}')
			continue
		
		if f'{employee_name}/{datetime.strftime(datetime_obj,"%Y-%m-%d %H:%M:%S")}' not in checkin_emp_data:
			frappe.log_error(f'Missing Data for {employee_name} of this time {datetime.strftime(datetime_obj,"%Y-%m-%d %H:%M:%S")}')