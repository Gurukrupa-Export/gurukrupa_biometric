
from hrms.hr.doctype.shift_assignment.shift_assignment import get_employee_shift_timings
from frappe.utils import cint, add_to_date, get_datetime, get_datetime_str,now
from datetime import datetime,timedelta
import frappe
from frappe import _
from frappe.model.document import Document
import requests

class BiometricData(Document):	
	def fetch_and_save_biometric_data(self):
		today_date = datetime.now().date()
		settings = frappe.get_cached_doc("Biometric Settings", "Biometric Settings")

		if cint(settings.manual):
			from_date = settings.from_date
			to_date =  settings.to_date
			formatted_from_date = frappe.utils.formatdate(from_date, "ddMMyyyy")
			formatted_to_date = frappe.utils.formatdate(to_date, "ddMMyyyy")
		else:
			old_date = today_date - timedelta(days=cint(settings.day_threshold))
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
		
		# Prepare request parameters
		payload = {}		
		headers = {
		'Authorization': settings.biometric_api_key,
		'Cookie': 'ASP.NET_SessionId=4t2hfqzatrgd4akbdje2xjr4'
		}
		
		try:
			# Send GET request to the API
			response = requests.request("GET", url, headers=headers, data=payload)	

			# Check if the request was successful (status code 200)
			if response.status_code == 200:
				# Parse the response JSON
				data = response.json()["event-ta"]
					
				# Iterate over the logs and save them to "Biometric Data" DocType
				abc = [] 
				for log in data:
					if log['userid'] != self.punch_id:
						continue
						
					skip = validate_time_threshold(log, checkin_from_date, checkin_to_date)
					abc.append(log)
					if skip:
						continue
						
					employee_code = log['userid']
					serial_number = log['device_name']
					
					# Convert datetime object to desired format
					original_datetime = datetime.strptime(log['edatetime_e'], "%d/%m/%Y %H:%M")
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
					# frappe.throw(f" {shift_det} \\\ {shift_det.shift_type.name}")
					
					if get_datetime(log_date) > shift_det.actual_start and get_datetime(log_date) < shift_det.actual_end:
						log_detail = frappe.db.sql(f"""select log_type from `tabEmployee Checkin` tec 
								 							where employee = '{employee_name}' 
					   										and DATE(time)='{log_date.split(' ')[0]}'
													""",as_dict=1)
						
						if log_detail == []:
							log_type = 'IN'
						else:
							employee_chekin_data = frappe.db.sql(f"""SELECT log_type from `tabEmployee Checkin` tec 
																		where employee ='{employee_name}' 
																			and time < '{log_date}' ORDER BY time DESC LIMIT 1"""
																	,as_dict=1)
							
							if len(employee_chekin_data) == 0: 
								log_type = 'IN'
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
						"time": str(final_log_date),
						"device_id":f"{serial_number}",
						"source":"Biometric",
						"log_type": log_type,
						"custom_unique_id": unique_id
					})
					
					emp_data.insert(ignore_permissions=True)
				# frappe.throw(f"{abc}")
				return 'ok'
			else:
				frappe.log_error(frappe.get_traceback(),f"Response code is: {response.status_code}. Check URL")
		except requests.exceptions.RequestException as e:
			frappe.log_error(frappe.get_traceback(),e)

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
				
				# frappe.throw(f"last_punch {last_punch} ||  date_object {date_object} || diff {diff} ||  time_threshold {time_threshold}")
				
				if diff.total_seconds()<=float(time_threshold):
					return True
			except Exception as e:
				frappe.log_error(frappe.get_traceback(), f"Error in validate_time_threshold: {e}")
				# frappe.msgprint(f"here")
				return True  # Safer to skip if any error occurs

		return False
	# frappe.db.get_list("Employee Checkin",filters={"employee":employee},fields=["time"],order_by='time desc')
		# if last_punch:
		# 	date_object = datetime.strptime(log['edatetime_e'], "%d/%m/%Y %H:%M")
		# 	frappe.throw(f"{date_object}")
		# 	diff = date_object - last_punch[0]['time']

		# 	if diff.total_seconds()<=float(time_threshold):
		# 		return 1

@frappe.whitelist()
def fetch_and_save_data(docname):
    doc = frappe.get_doc("Biometric Data", docname)
    return doc.fetch_and_save_biometric_data()

@frappe.whitelist()
def fetch_and_save_biometric_data1():
	today_date = datetime.now().date()
	manual = int(frappe.db.get_value("Biometric Settings","Biometric Settings","manual"))
	if manual:
		from_date = frappe.db.get_value("Biometric Settings","Biometric Settings","from_date")
		to_date = frappe.db.get_value("Biometric Settings","Biometric Settings","to_date")
		formatted_from_date = frappe.utils.formatdate(from_date, "ddMMyyyy")
		formatted_to_date = frappe.utils.formatdate(to_date, "ddMMyyyy")
	else:
		day_threshold = int(frappe.db.get_value("Biometric Settings","Biometric Settings","day_threshold"))
		today_date = datetime.now().date()
		formatted_to_date = today_date.strftime("%d%m%Y")
		old_date = today_date - timedelta(days=day_threshold)
		formatted_from_date = old_date.strftime("%d%m%Y")
		
	# formatted_today_date = today_date.strftime("%d%m%Y")
	# old_date = today_date - timedelta(days=2)
	# formatted_old_date = old_date.strftime("%d%m%Y")
	# today_date = datetime.now().date()
	exist_emp_name = []
	for k in frappe.db.get_list('Employee Checkin',fields=['employee','time']):
		exist_emp_name.append(f'{k["employee"]}/{k["time"]}')
	
	api_url = frappe.db.get_value('Biometric Settings','Biometric Settings','biometric_api')

	url = f"{api_url};date-range={formatted_from_date}-{formatted_to_date}"
	api_key = frappe.db.get_value('Biometric Settings','Biometric Settings','biometric_api_key')
	
	# Prepare request parameters
	payload = {}
	headers = {
	'Authorization': api_key,
	'Cookie': 'ASP.NET_SessionId=4t2hfqzatrgd4akbdje2xjr4'
	}

	response = requests.request("GET", url, headers=headers, data=payload)

	data = response.json()["event-ta"]
	# frappe.throw(f"{data}")

	# Add this block to debug
	# if response.status_code != 200:
	# 	frappe.throw(f"Error {response.status_code}: {response.text}")

	# try:
	# 	data = response.json()["event-ta"]
	# except Exception as e:
	# 	frappe.throw(f"Failed to parse JSON: {str(e)}. Raw response: {response.text}")


	data_list = []
	for log in data:
		# frappe.throw(f"{log}")
		skip = validate_time_threshold(log)
		if skip:
			continue
		
		# employee_code = log['EmployeeCode']
		employee_code = log['userid']

		# serial_number = log['SerialNumber']
		serial_number = log['device_name']

		# log_date = log['LogDate']
		log_date = log['edatetime_e']
		

		parsed_date = datetime.strptime(log_date, "%d/%m/%Y %H:%M")
		formatted_date = parsed_date.strftime("%Y-%m-%d %H:%M")
		employee = frappe.db.get_value("Employee",{"attendance_device_id":employee_code},'name')
		if employee:
			employee_full_name = frappe.db.get_value("Employee",{"attendance_device_id":employee_code},'employee_name')
			d = {"EmployeeCode":employee,"Full_name":employee_full_name,"SerialNumber":serial_number,"LogDate":formatted_date}
			data_list.append(d)
			
	return data_list