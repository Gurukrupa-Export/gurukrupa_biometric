import frappe
import requests


def before_save(self, method):
    if self.attendance_device_id:
        skip = check_user(self)
        if skip != 1:
            url = frappe.db.get_value("Biometric Settings","Biometric Settings","api_for_adding_user_in_matrix")
            api_url = url + f"id={self.attendance_device_id};name={self.employee_name}"

            # Prepare request parameters
            api_key = frappe.db.get_value('Biometric Settings','Biometric Settings','biometric_api_key')
            payload = {}
            headers = {
            'Authorization': api_key,
            'Cookie': 'ASP.NET_SessionId=chmrqcseothydlrcnw0g1iag'
            }

            response = requests.request("GET", api_url, headers=headers, data=payload)
            if response.status_code == 200:
                frappe.msgprint("Employee added successfully")
            else:
                frappe.log_error(frappe.get_traceback(),response)
    

def check_user(self):

    url = frappe.db.get_value("Biometric Settings","Biometric Settings","api_for_searching_user_in_matrix")

    api_url = url + f"search-criteria=1;search-string={self.attendance_device_id}"
    api_key = frappe.db.get_value('Biometric Settings','Biometric Settings','biometric_api_key')

    payload = {}
    headers = {
    'Authorization': api_key,
    'Cookie': 'ASP.NET_SessionId=chmrqcseothydlrcnw0g1iag'
    }

    response = requests.request("GET", api_url, headers=headers, data=payload)
    if "No records found" not in response.text:
        return 1