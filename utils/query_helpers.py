import requests
import json
import os
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from dateutil.relativedelta import relativedelta

class FHIRQueryHelper:
    """Helper class for FHIR API queries and data parsing."""
    
    BASE_URL = "https://hapi.fhir.org/baseR4"
    
    @staticmethod
    def make_request(endpoint: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Make a request to the FHIR API.
        
        Args:
            endpoint (str): API endpoint to query
            params (Optional[Dict[str, str]]): Query parameters
            
        Returns:
            Dict[str, Any]: JSON response from the API
        """
        url = f"{FHIRQueryHelper.BASE_URL}/{endpoint}"
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    @staticmethod
    def parse_patient_name(patient: Dict[str, Any]) -> str:
        """
        Parse patient's full name from FHIR patient resource.
        
        Args:
            patient (Dict[str, Any]): Patient resource from FHIR API
            
        Returns:
            str: Patient's full name
        """
        if 'name' not in patient or not patient['name']:
            return ""
        name = patient['name'][0]
        given = name.get('given', [''])[0]
        family = name.get('family', '')
        return f"{given} {family}".strip()
    
    @staticmethod
    def parse_patient_contact(patient: Dict[str, Any]) -> Dict[str, Optional[str]]:
        """
        Parse patient's contact information from FHIR patient resource.
        
        Args:
            patient (Dict[str, Any]): Patient resource from FHIR API
            
        Returns:
            Dict[str, Optional[str]]: Dictionary containing email and other contact info
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
        """
        Parse patient's identifiers from FHIR patient resource.
        
        Args:
            patient (Dict[str, Any]): Patient resource from FHIR API
            
        Returns:
            Dict[str, Optional[str]]: Dictionary containing MRN and other identifiers
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
        """
        Calculate age from birthdate.
        
        Args:
            birthdate (str): Birthdate in YYYY-MM-DD format
            
        Returns:
            int: Age in years
        """
        birth_date = datetime.strptime(birthdate, '%Y-%m-%d')
        return relativedelta(datetime.now(), birth_date).years
    
    @staticmethod
    def parse_condition(condition: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse condition information from FHIR condition resource.
        
        Args:
            condition (Dict[str, Any]): Condition resource from FHIR API
            
        Returns:
            Dict[str, Any]: Parsed condition information
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
        """
        Build a comprehensive patient summary from patient and condition data.
        
        Args:
            patient (Dict[str, Any]): Patient resource from FHIR API
            condition (Dict[str, Any]): Condition resource from FHIR API
            
        Returns:
            Dict[str, Any]: Comprehensive patient summary
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

def openrouter_chat(messages: List[Dict[str, str]], model: str = "qwen/qwen3-235b-a22b:free") -> str:
    """
    Make a direct API call to OpenRouter chat completions.
    
    Args:
        messages: List of message dictionaries with 'role' and 'content'
        model: The model to use for completion
        
    Returns:
        The generated response text
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable not set")
    
    # Validate API key format
    if not api_key.startswith("sk-or-v1-"):
        raise ValueError("Invalid OpenRouter API key format")
    
    # Log first 10 characters of API key for debugging
    print(f"[DEBUG] Using OpenRouter API key starting with: {api_key[:10]}...")
        
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model,
        "messages": messages
    }
    
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=30)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"] 