import datetime
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Union, Any
from .query_helpers import FHIRQueryHelper

def calculate_birthdate_range(min_age: int, max_age: int) -> tuple[str, str]:
    """
    Calculate the birthdate range for filtering patients based on age criteria.
    
    Args:
        min_age (int): Minimum age (inclusive)
        max_age (int): Maximum age (inclusive)
        
    Returns:
        tuple[str, str]: A tuple containing (min_birthdate, max_birthdate) in YYYY-MM-DD format
    """
    today = datetime.date.today()
    max_birthdate = today - relativedelta(years=min_age)
    min_birthdate = today - relativedelta(years=max_age + 1)
    return min_birthdate.strftime('%Y-%m-%d'), max_birthdate.strftime('%Y-%m-%d')

def fetch_conditions(min_birthdate: str, max_birthdate: str) -> Dict[str, Any]:
    """
    Fetch conditions from FHIR API based on birthdate range.
    
    Args:
        min_birthdate (str): Minimum birthdate in YYYY-MM-DD format
        max_birthdate (str): Maximum birthdate in YYYY-MM-DD format
        
    Returns:
        Dict[str, Any]: JSON response from FHIR API
    """
    params = {
        '_pretty': 'true',
        'subject.birthdate': f'le{max_birthdate}',
        'subject.birthdate': f'gt{min_birthdate}'
    }
    return FHIRQueryHelper.make_request('Condition', params)

def filter_conditions_by_name(conditions: Dict[str, Any], condition_name: str) -> List[Dict[str, Any]]:
    """
    Filter conditions by condition name.
    
    Args:
        conditions (Dict[str, Any]): Conditions data from FHIR API
        condition_name (str): Name of condition to filter by
        
    Returns:
        List[Dict[str, Any]]: Filtered list of conditions
    """
    if 'entry' not in conditions or not conditions['entry']:
        return []
    
    entries = [entry for entry in conditions['entry'] if 'code' in entry['resource']]
    return [entry for entry in entries
            if any(condition_name.lower() in cond['display'].lower() 
                  for cond in entry['resource']['code']['coding'])]

def fetch_patient_data(patient_id: str) -> Dict[str, Any]:
    """
    Fetch patient data from FHIR API.
    
    Args:
        patient_id (str): Patient ID
        
    Returns:
        Dict[str, Any]: Patient data from FHIR API
    """
    return FHIRQueryHelper.make_request(f'Patient/{patient_id}')

def extract_patient_info(patient: Dict[str, Any], condition: Dict[str, Any]) -> Dict[str, Union[str, int, None]]:
    """
    Extract relevant information from patient and condition data.
    
    Args:
        patient (Dict[str, Any]): Patient data
        condition (Dict[str, Any]): Condition data
        
    Returns:
        Dict[str, Union[str, int, None]]: Extracted patient information
    """
    patient_id = condition['resource']['subject']['reference'].split('/')[1]
    
    if 'telecom' not in patient or 'maritalStatus' not in patient:
        return {}
    
    full_name = patient['name'][0]['given'][0] + " " + patient['name'][0]['family']
    email = next((t['value'] for t in patient['telecom'] if t['system'] == 'email'), None)
    mrn = next((i['value'] for i in patient['identifier'] 
                if 'type' in i and i['type']['text'] == 'Medical Record Number'), None)
    
    patient_age = relativedelta(
        datetime.datetime.now(), 
        datetime.datetime.strptime(patient['birthDate'], '%Y-%m-%d')
    ).years
    
    patient_condition = condition['resource']['code']['coding'][0]['display']
    postal_code = patient['address'][0]['postalCode'] if 'address' in patient and patient['address'] else None
    
    return {
        'patient_url': f"https://hapi.fhir.org/baseR4/Patient/{patient_id}?_pretty=true",
        'full_name': full_name,
        'age': patient_age,
        'postal_code': postal_code,
        'MRN': mrn,
        'email': email,
        'condition': patient_condition
    }

def get_patients_between_ages_and_condition(min_age: int, max_age: int, condition: str) -> List[Dict[str, Union[str, int, None]]]:
    """
    Fetches and returns a list of patients from a specified FHIR R4 API endpoint based on the patients' age range and condition.
    
    Args:
        min_age (int): The minimum age to filter patients by (inclusive)
        max_age (int): The maximum age to filter patients by (inclusive)
        condition (str): The specific health condition to filter patients by
        
    Returns:
        List[Dict[str, Union[str, int, None]]]: List of patient dictionaries containing relevant information
    """
    min_birthdate, max_birthdate = calculate_birthdate_range(min_age, max_age)
    conditions_data = fetch_conditions(min_birthdate, max_birthdate)
    filtered_conditions = filter_conditions_by_name(conditions_data, condition)
    
    if not filtered_conditions:
        return []
    
    patients = []
    for cond in filtered_conditions:
        patient_id = cond['resource']['subject']['reference'].split('/')[1]
        patient_data = fetch_patient_data(patient_id)
        patient_summary = FHIRQueryHelper.build_patient_summary(patient_data, cond['resource'])
        if patient_summary:
            patients.append(patient_summary)
    
    return patients 