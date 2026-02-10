# # Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# # For license information, please see license.txt

from hrms.hr.doctype.shift_assignment.shift_assignment import get_employee_shift_timings
from frappe.utils import cint, add_to_date, get_datetime, get_datetime_str
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_datetime
import requests
from datetime import datetime,timedelta
from itertools import groupby

@frappe.whitelist()
def fetch_and_save_biometric_data():
	# now = datetime.now()
	# today_date = now.strftime("%Y-%m-%d")
	today_date = datetime.now().date()
	settings = frappe.get_cached_doc("Biometric Settings", "Biometric Settings")

	if cint(settings.manual):
		from_date = settings.from_date
		to_date =  settings.to_date
		formatted_from_date = frappe.utils.formatdate(from_date, "ddMMyyyy")
		formatted_to_date = frappe.utils.formatdate(to_date, "ddMMyyyy")
	else:
		old_date = today_date - timedelta(days=cint(settings.day_threshold))
		from_date = today_date - timedelta(days=cint(settings.day_threshold))
		to_date = today_date

		formatted_from_date = old_date.strftime("%d%m%Y")
		formatted_to_date = today_date.strftime("%d%m%Y")
		
	# check employee checkin for given date
	exist_emp_name = []
	checkin_from_date = frappe.utils.formatdate(from_date, "yyyy-mm-dd")
	checkin_to_date = frappe.utils.formatdate(to_date, "yyyy-mm-dd")

	checkin_doc = frappe.db.sql(f""" SELECT employee,time FROM `tabEmployee Checkin`
					WHERE DATE(time) between '{checkin_from_date}' and '{checkin_to_date}' """,as_dict=1) 
	if checkin_doc:
		for k in checkin_doc:
			exist_emp_name.append(f'{k["employee"]}/{k["time"]}')
	
	# fetch api url and api key from Biometric Settings
	url = f"{settings.biometric_api};date-range={formatted_from_date}-{formatted_to_date}"
		
	api_key = frappe.db.get_value('Biometric Settings','Biometric Settings','biometric_api_key')
	
	# Prepare request parameters
	payload = {}
	headers = {
		'Authorization': api_key,
		'Cookie': 'ASP.NET_SessionId=4t2hfqzatrgd4akbdje2xjr4'
	}
	
	try:
		# Send GET request to the API
		response = requests.request("GET", url, headers=headers, data=payload)
	
		# Check if the request was successful (status code 200)
		if response.status_code == 200:
			# Parse the response JSON
			data = response.json()["event-ta"]
			# data = response.json()["event-ta"]
			# Iterate over the logs and save them to "Biometric Data" DocType
			
			for log in data:
				skip = validate_time_threshold(log, checkin_from_date, checkin_to_date)
				if skip:
					continue
					
				employee_code = log['userid']
				serial_number = log['device_name']
				original_datetime = datetime.strptime(log['edatetime_e'], "%d/%m/%Y %H:%M")
				
				# Convert datetime object to desired format
				log_date = original_datetime.strftime("%Y-%m-%d %H:%M")
				final_log_date = original_datetime.strftime("%Y-%m-%d %H:%M")
				unique_id = log['indexno']				
				
				employee_name = frappe.db.get_value('Employee',{'attendance_device_id':employee_code,'status':'Active'},'name')
				if employee_name == None:
					continue

				if exist_emp_name:
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
					"time":str(final_log_date),
					"device_id":f"{serial_number}",
					"source":"Biometric",
					"log_type": log_type,
					"custom_unique_id": unique_id
				})
				emp_data.insert()
			return 'ok'
		else:
			frappe.log_error(frappe.get_traceback(),f"Response code is: {response.status_code}. Check URL")
	except requests.exceptions.RequestException as e:
		frappe.log_error(frappe.get_traceback(),e)
	

# @frappe.whitelist()
# def set_unique_id():
# 	session = requests.Session()
# 	aws_api = frappe.db.get_value('Biometric Settings','Biometric Settings','aws_api')
# 	response = session.get(f'http://{aws_api}')
# 	data_list = response.json()
# 	for i in data_list:
# 		try:
			
# 			employee_name = frappe.db.get_value('Employee',{'attendance_device_id':i['punch_id']},'name')
# 			datetime_obj = datetime.strptime(i['log_time'],'%a, %d %b %Y %H:%M:%S GMT')

# 			if frappe.db.get_value('Employee Checkin',{'time':datetime.strftime(datetime_obj,"%Y-%m-%d %H:%M"),'employee':employee_name},'custom_unique_id'): 
# 				continue

# 			emp_record = frappe.db.get_value('Employee Checkin',{'time':datetime.strftime(datetime_obj,"%Y-%m-%d %H:%M"),'employee':employee_name},'name')
# 			frappe.db.set_value('Employee Checkin',emp_record,'custom_unique_id',i['id'])
# 		except:
# 			continue


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
		
		if f'{employee_name}/{datetime.strftime(datetime_obj,"%Y-%m-%d %H:%M")}' not in checkin_emp_data:
			frappe.log_error(f'Missing Data for {employee_name} of this time {datetime.strftime(datetime_obj,"%Y-%m-%d %H:%M")}')


def validate_time_threshold(log, checkin_from_date, checkin_to_date):
	time_threshold = frappe.db.get_value('Biometric Settings','Biometric Settings','time_threshold')
	employee = frappe.db.get_value("Employee",{"attendance_device_id":log["userid"],"status": "Active"},"name")
	if employee:
		last_punch = frappe.db.sql(f""" SELECT time FROM `tabEmployee Checkin`
                        WHERE employee = '{employee}'
							  and DATE(time) between '{checkin_from_date}' and '{checkin_to_date}'
						order by time desc
						""",as_dict=1)
	
		if last_punch:
			try:
				date_object = datetime.strptime(log['edatetime_e'], "%d/%m/%Y %H:%M")
				diff = date_object - last_punch[0]['time']

				if diff.total_seconds()<=float(time_threshold):
					return True
			except Exception as e:
				frappe.log_error(frappe.get_traceback(), f"Error in validate_time_threshold: {e}")
				return True  # Safer to skip if any error occurs

		return False
		
@frappe.whitelist()
def set_skip_attendance():
	today_date = datetime.now().date()
	manual = int(frappe.db.get_value("Biometric Settings","Biometric Settings","manual"))
	if manual:
		from_date = frappe.db.get_value("Biometric Settings","Biometric Settings","from_date")
		to_date = frappe.db.get_value("Biometric Settings","Biometric Settings","to_date")
		formatted_from_date = frappe.utils.formatdate(from_date, "yyyy-MM-dd")
		formatted_to_date = frappe.utils.formatdate(to_date, "yyyy-MM-dd")
	else:
		day_threshold = int(frappe.db.get_value("Biometric Settings","Biometric Settings","day_threshold"))
		today_date = datetime.now().date()
		formatted_to_date = today_date.strftime("%Y-%m-%d")
		old_date = today_date - timedelta(days=day_threshold)
		formatted_from_date = old_date.strftime("%Y-%m-%d")

	logs = get_employee_checkins(formatted_from_date,formatted_to_date)

	group_key = lambda x: (x["employee"], x["time"], x["name"])  # noqa
	for key, group in groupby(sorted(logs, key=group_key), key=group_key):
		emp_checkin = key[2]
		attendance_date = key[1].date()
		employee = key[0]
		
		attendance = get_marked_attendance_dates_between(employee, attendance_date)

		if emp_checkin and attendance:
			frappe.db.set_value("Employee Checkin",emp_checkin,"skip_auto_attendance",0)
			frappe.db.set_value("Attendance",attendance,"docstatus", 2)

@frappe.whitelist()
def set_skip_attendance_check():
	settings = frappe.db.get_value(
		"Biometric Settings",
		"Biometric Settings",
		["manual", "from_date", "to_date", "day_threshold"],
		as_dict=True
	)

	today = datetime.now().date()

	# Determine from/to date range
	if int(settings.manual):
		from_date = settings.from_date
		to_date = settings.to_date
	else:
		day_threshold = int(settings.day_threshold)
		to_date = today
		from_date = today - timedelta(days=day_threshold)

	# Fetch checkins within range
	logs = get_employee_checkins(from_date, to_date)

	for log in logs:
		emp_checkin = log.name
		employee = log.employee
		attendance_date = log.time.date()

		attendance = get_marked_attendance_dates_between(employee, attendance_date)
		
		if attendance:
			frappe.db.set_value("Attendance", attendance, "docstatus", 2) # Cancel attendance
		if emp_checkin:
			frappe.db.set_value("Employee Checkin", emp_checkin, "skip_auto_attendance", 0) # Reset skip
			frappe.db.set_value("Employee Checkin", emp_checkin, "attendance", "") # Reset attendance

	frappe.db.commit()

def get_employee_checkins(from_date,to_date):
	employee_checkins = frappe.get_all("Employee Checkin",
			fields=[
				"name","employee",
				"log_type","time",
				"shift","skip_auto_attendance"
			],
			filters={
				"skip_auto_attendance": 1,
				# "attendance": ("is", "not set"),
				"attendance": ["is", "not set"],
				"time": ("between", [from_date, to_date]),
			},
			order_by="employee,time",
		)
	
	return employee_checkins

def get_marked_attendance_dates_between(employee, date):
	attendance = frappe.db.get_value("Attendance", 
			# {'employee': employee, 'attendance_date': date, 'docstatus': ('<', 2)},
			{"employee": employee, "attendance_date": date, "docstatus": ("<", 2)},
			"name"
		)

	return attendance
