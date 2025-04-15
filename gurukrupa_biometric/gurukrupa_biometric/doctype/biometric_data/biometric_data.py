
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
	def fetch_and_save_biometric_data(self):
		# now = datetime.now()
		# today_date = now.strftime("%Y-%m-%d")
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
		# frappe.throw(f"{exist_emp_name}")
		
		api_url = frappe.db.get_value('Biometric Settings','Biometric Settings','biometric_api')

		url = f"{api_url};date-range={formatted_from_date}-{formatted_to_date}"
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
				dummy = []
				# Parse the response JSON
				data = response.json()["event-ta"]
				# frappe.throw(f"{len(data)}")

				# Iterate over the logs and save them to "Biometric Data" DocType
				for log in data:
					skip = validate_time_threshold(log)
				# frappe.throw(f"{len(data)}")
					if skip:
						continue
						
					employee_code = log['userid']
					serial_number = log['device_name']
					original_datetime = datetime.strptime(log['edatetime_e'], "%d/%m/%Y %H:%M")

					# Convert datetime object to desired format
					log_date = original_datetime.strftime("%Y-%m-%d %H:%M")
					final_log_date = original_datetime.strftime("%Y-%m-%d %H:%M")
					# log_date = log['eventdatetime']
					unique_id = log['indexno']

					employee_name = frappe.db.get_value('Employee',{'attendance_device_id':employee_code,'status':'Active'},'status')
					# dummy.append(employee_code)
					
					if employee_name == None:
						# frappe.log_error(f'Employee Not Found for this punch ID {employee_code}')
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

					# emp_data = frappe.get_doc({
					# 	"doctype": "Employee Checkin",
					# 	"employee": employee_name,
					# 	"time":str(final_log_date),
					# 	"device_id":f"{serial_number}",
					# 	"source":"Biometric",
					# 	"log_type": log_type,
					# 	"custom_unique_id": unique_id
					# })
					# emp_data.insert()

					emp_data = frappe.new_doc("Employee Checkin")
					emp_data.employee = employee_name
					emp_data.time = str(final_log_date)
					emp_data.device_id = f"{serial_number}"
					emp_data.source = "Biometric"
					emp_data.log_type =  log_type
					emp_data.custom_unique_id =  unique_id
					emp_data.save()
				# frappe.throw(f"{dummy}")	
				return 'ok'
			else:
				frappe.log_error(frappe.get_traceback(),f"Response code is: {response.status_code}. Check URL")
		except requests.exceptions.RequestException as e:
			frappe.log_error(frappe.get_traceback(),e)

def validate_time_threshold(log):
	time_threshold = frappe.db.get_value('Biometric Settings','Biometric Settings','time_threshold')
	employee = frappe.db.get_value("Employee",{"attendance_device_id":log["userid"]},"name")
	last_punch = frappe.db.get_list("Employee Checkin",filters={"employee":employee},fields=["time"],order_by='time desc')
	if last_punch:
		date_object = datetime.strptime(log['edatetime_e'], "%d/%m/%Y %H:%M")
		diff = date_object - last_punch[0]['time']

		if diff.total_seconds()<=float(time_threshold):
			return 1

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


