import datetime
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Union, Any
from .query_helpers import FHIRQueryHelper

def calculate_birthdate_range(min_age: int, max_age: int) -> tuple[str, str]:
    """Figure out what birthdates to look for when searching for patients.
    
    When we want to find patients of a certain age, we need to:
    1. Take today's date
    2. Subtract the minimum age to get the oldest birthdate
    3. Subtract the maximum age to get the youngest birthdate
    
    Args:
        min_age: The youngest age we want to find
        max_age: The oldest age we want to find
        
    Returns:
        Two dates in YYYY-MM-DD format:
        - The oldest birthdate to look for
        - The youngest birthdate to look for
    """
    today = datetime.date.today()
    max_birthdate = today - relativedelta(years=min_age)
    min_birthdate = today - relativedelta(years=max_age + 1)
    return min_birthdate.strftime('%Y-%m-%d'), max_birthdate.strftime('%Y-%m-%d')

def fetch_conditions(min_birthdate: str, max_birthdate: str) -> Dict[str, Any]:
    """Get health conditions for patients in a certain age range.
    
    We use the FHIR database to find:
    - What conditions patients have
    - How serious they are
    - When they started
    
    Args:
        min_birthdate: The oldest birthdate to look for
        max_birthdate: The youngest birthdate to look for
        
    Returns:
        All the health conditions we found
    """
    params = {
        '_pretty': 'true',
        'subject.birthdate': f'le{max_birthdate}',
        'subject.birthdate': f'gt{min_birthdate}'
    }
    return FHIRQueryHelper.make_request('Condition', params)

def filter_conditions_by_name(conditions: Dict[str, Any], condition_name: str) -> List[Dict[str, Any]]:
    """Find patients with a specific health condition.
    
    We look through all the conditions to find:
    - Exact matches for the condition name
    - Similar conditions that might be related
    - Different ways doctors might have written it
    
    Args:
        conditions: All the health conditions we found
        condition_name: The specific condition we're looking for
        
    Returns:
        A list of matching conditions
    """
    if 'entry' not in conditions or not conditions['entry']:
        return []
    
    entries = [entry for entry in conditions['entry'] if 'code' in entry['resource']]
    return [entry for entry in entries
            if any(condition_name.lower() in cond['display'].lower() 
                  for cond in entry['resource']['code']['coding'])]

def fetch_patient_data(patient_id: str) -> Dict[str, Any]:
    """Get all the information we have about a specific patient.
    
    This includes:
    - Their basic information
    - Medical history
    - Test results
    - Contact details
    
    Args:
        patient_id: The patient's unique ID number
        
    Returns:
        Everything we know about this patient
    """
    return FHIRQueryHelper.make_request(f'Patient/{patient_id}')

def extract_patient_info(patient: Dict[str, Any], condition: Dict[str, Any]) -> Dict[str, Union[str, int, None]]:
    """Pull out the most important information about a patient.
    
    We focus on:
    - Their name and age
    - Where they live
    - Their medical record number
    - How to contact them
    - Their health condition
    
    Args:
        patient: All their medical records
        condition: Information about their health condition
        
    Returns:
        The key information we need to help them
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
    """Find patients who:
    1. Are between certain ages
    2. Have a specific health condition
    
    This helps us:
    - Identify at-risk patients
    - Plan outreach programs
    - Track health trends
    
    Args:
        min_age: The youngest age to look for
        max_age: The oldest age to look for
        condition: The health condition to look for
        
    Returns:
        A list of patients who match our criteria
    """
    # Figure out what birthdates to look for
    min_birthdate, max_birthdate = calculate_birthdate_range(min_age, max_age)
    
    # Get all conditions in that age range
    conditions_data = fetch_conditions(min_birthdate, max_birthdate)
    
    # Find the specific condition we're looking for
    filtered_conditions = filter_conditions_by_name(conditions_data, condition)
    
    if not filtered_conditions:
        return []
    
    # Get information about each matching patient
    patients = []
    for cond in filtered_conditions:
        patient_id = cond['resource']['subject']['reference'].split('/')[1]
        patient_data = fetch_patient_data(patient_id)
        patient_summary = FHIRQueryHelper.build_patient_summary(patient_data, cond['resource'])
        if patient_summary:
            patients.append(patient_summary)
    
    return patients 