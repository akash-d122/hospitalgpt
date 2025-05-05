import requests
import json
import os
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from dateutil.relativedelta import relativedelta

class FHIRQueryHelper:
    """A helper class for working with FHIR medical data.
    
    This class helps us:
    - Connect to FHIR medical databases
    - Get patient information
    - Parse medical records
    - Calculate important health metrics
    """
    
    # The main FHIR server we're connecting to
    BASE_URL = "https://hapi.fhir.org/baseR4"
    
    @staticmethod
    def make_request(endpoint: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Get information from the FHIR server.
        
        This is how we talk to the medical database to get:
        - Patient records
        - Health conditions
        - Test results
        - Other medical information
        
        Args:
            endpoint: What kind of information we want (e.g., 'Patient', 'Condition')
            params: Any filters or search terms we want to use
            
        Returns:
            The medical data we asked for
        """
        url = f"{FHIRQueryHelper.BASE_URL}/{endpoint}"
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    @staticmethod
    def parse_patient_name(patient: Dict[str, Any]) -> str:
        """Get a patient's full name from their medical record.
        
        FHIR stores names in a special format, so we need to:
        1. Get their first name
        2. Get their last name
        3. Put them together properly
        
        Args:
            patient: The patient's medical record
            
        Returns:
            Their full name in a readable format
        """
        if 'name' not in patient or not patient['name']:
            return ""
        name = patient['name'][0]
        given = name.get('given', [''])[0]
        family = name.get('family', '')
        return f"{given} {family}".strip()
    
    @staticmethod
    def parse_patient_contact(patient: Dict[str, Any]) -> Dict[str, Optional[str]]:
        """Get a patient's contact information.
        
        We look for:
        - Email address
        - Phone number
        - Home address
        
        This helps us reach out to patients when needed.
        
        Args:
            patient: The patient's medical record
            
        Returns:
            All their contact information in one place
        """
        contact_info = {
            'email': None,
            'phone': None,
            'address': None
        }
        
        if 'telecom' in patient:
            for telecom in patient['telecom']:
                if telecom.get('system') == 'email':
                    contact_info['email'] = telecom.get('value')
                elif telecom.get('system') == 'phone':
                    contact_info['phone'] = telecom.get('value')
        
        if 'address' in patient and patient['address']:
            address = patient['address'][0]
            contact_info['address'] = {
                'postal_code': address.get('postalCode'),
                'city': address.get('city'),
                'state': address.get('state')
            }
            
        return contact_info
    
    @staticmethod
    def parse_patient_identifiers(patient: Dict[str, Any]) -> Dict[str, Optional[str]]:
        """Get a patient's medical record numbers and IDs.
        
        Every patient has:
        - A Medical Record Number (MRN)
        - Other IDs used by different healthcare systems
        
        This helps us make sure we're looking at the right patient.
        
        Args:
            patient: The patient's medical record
            
        Returns:
            All their medical IDs in one place
        """
        identifiers = {
            'mrn': None,
            'other_ids': []
        }
        
        if 'identifier' in patient:
            for identifier in patient['identifier']:
                if ('type' in identifier and 
                    identifier['type'].get('text') == 'Medical Record Number'):
                    identifiers['mrn'] = identifier.get('value')
                else:
                    identifiers['other_ids'].append({
                        'system': identifier.get('system'),
                        'value': identifier.get('value')
                    })
                    
        return identifiers
    
    @staticmethod
    def calculate_age(birthdate: str) -> int:
        """Figure out how old a patient is.
        
        We need to:
        1. Take their birthdate
        2. Compare it to today's date
        3. Calculate their age in years
        
        Args:
            birthdate: When the patient was born (YYYY-MM-DD)
            
        Returns:
            How old they are in years
        """
        birth_date = datetime.strptime(birthdate, '%Y-%m-%d')
        return relativedelta(datetime.now(), birth_date).years
    
    @staticmethod
    def parse_condition(condition: Dict[str, Any]) -> Dict[str, Any]:
        """Get information about a patient's health condition.
        
        We look for:
        - What the condition is
        - When it started
        - How serious it is
        - Any special codes doctors use for it
        
        Args:
            condition: The medical record of their condition
            
        Returns:
            All the important details about their condition
        """
        if 'code' not in condition or 'coding' not in condition['code']:
            return {}
            
        coding = condition['code']['coding'][0]
        return {
            'code': coding.get('code'),
            'display': coding.get('display'),
            'system': coding.get('system'),
            'onset_date': condition.get('onsetDateTime'),
            'severity': condition.get('severity', {}).get('text')
        }
    
    @staticmethod
    def build_patient_summary(patient: Dict[str, Any], condition: Dict[str, Any]) -> Dict[str, Any]:
        """Create a complete summary of a patient's health.
        
        We put together:
        - Their basic information
        - Contact details
        - Medical IDs
        - Health conditions
        - Links to their full records
        
        Args:
            patient: Their basic medical record
            condition: Information about their health condition
            
        Returns:
            A complete summary of their health situation
        """
        contact_info = FHIRQueryHelper.parse_patient_contact(patient)
        identifiers = FHIRQueryHelper.parse_patient_identifiers(patient)
        condition_info = FHIRQueryHelper.parse_condition(condition)
        
        return {
            'full_name': FHIRQueryHelper.parse_patient_name(patient),
            'age': FHIRQueryHelper.calculate_age(patient['birthDate']),
            'contact': contact_info,
            'identifiers': identifiers,
            'condition': condition_info,
            'patient_url': f"{FHIRQueryHelper.BASE_URL}/Patient/{patient['id']}?_pretty=true"
        }

def openrouter_chat(messages: List[Dict[str, str]], model: str = "deepseek/deepseek-r1:free") -> str:
    """Use AI to help write messages to patients.
    
    This function:
    1. Connects to the OpenRouter AI service
    2. Sends our message instructions
    3. Gets back a well-written response
    4. Makes sure the text is easy to read
    
    Args:
        messages: What we want the AI to write about
        model: Which AI model to use for writing
        
    Returns:
        A well-written message ready to send to patients
    """
    try:
        # Get our AI service key
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("We need an OpenRouter API key to write messages")
        
        # Make sure the key looks right
        if not api_key.startswith("sk-or-v1-"):
            raise ValueError("This API key doesn't look right")
        
        # Connect to the AI service
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "http://localhost:8501",
                "X-Title": "HospitalGPT"
            },
            json={
                "model": model,
                "messages": messages
            },
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        
        # Make sure we got a good response
        if 'choices' not in result or not result['choices']:
            return "Sorry, we couldn't generate a message right now. Please try again later."
        
        response_text = result['choices'][0]['message']['content']
        
        # Make sure special characters show up right
        replacements = {
            '\u2264': '<=',  # less than or equal to
            '\u2265': '>=',  # greater than or equal to
            '\u2013': '-',   # en dash
            '\u2014': '--',  # em dash
            '\u2018': "'",   # left single quote
            '\u2019': "'",   # right single quote
            '\u201c': '"',   # left double quote
            '\u201d': '"'    # right double quote
        }
        
        for unicode_char, replacement in replacements.items():
            response_text = response_text.replace(unicode_char, replacement)
            
        return response_text
        
    except Exception as e:
        return f"Sorry, we had trouble writing the message: {str(e)}" 