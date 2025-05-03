import unittest
from unittest.mock import patch
from utils import patient_utils
from utils import query_helpers
import json
import re
import os

# Sample mock data for FHIR API responses
MOCK_CONDITIONS_DATA = {
    'entry': [
        {
            'resource': {
                'subject': {'reference': 'Patient/123'},
                'code': {
                    'coding': [{'display': 'Hyperglycemia'}],
                    'text': 'Hyperglycemia'
                }
            }
        }
    ]
}

MOCK_PATIENT_DATA = {
    'id': '123',
    'name': [{'given': ['John'], 'family': 'Doe'}],
    'birthDate': '1920-01-01',
    'telecom': [{'system': 'email', 'value': 'john.doe@example.com'}],
    'identifier': [{'type': {'text': 'Medical Record Number'}, 'value': 'MRN123'}],
    'address': [{'postalCode': '12345'}],
    'maritalStatus': {'text': 'Married'}
}

class TestPatientUtils(unittest.TestCase):
    @patch('utils.patient_utils.FHIRQueryHelper.make_request')
    def test_get_patients_between_ages_and_condition(self, mock_make_request):
        # Mock the sequence of API calls
        def side_effect(endpoint, params=None):
            if endpoint.startswith('Condition'):
                return MOCK_CONDITIONS_DATA
            elif endpoint.startswith('Patient/'):
                return MOCK_PATIENT_DATA
            else:
                return {}
        mock_make_request.side_effect = side_effect

        # Run the refactored function
        result = patient_utils.get_patients_between_ages_and_condition(100, 105, 'Hyperglycemia')
        # Check the output structure and values
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        patient = result[0]
        self.assertEqual(patient['full_name'], 'John Doe')
        self.assertEqual(patient['contact']['email'], 'john.doe@example.com')
        self.assertEqual(patient['condition']['display'], 'Hyperglycemia')
        self.assertEqual(patient['identifiers']['mrn'], 'MRN123')
        self.assertEqual(patient['contact']['address']['postal_code'], '12345')

class TestQueryHelpers(unittest.TestCase):
    def test_import_and_usage(self):
        # Test that FHIRQueryHelper class is importable and callable
        helper = query_helpers.FHIRQueryHelper
        self.assertTrue(callable(helper.parse_patient_name))
        self.assertTrue(callable(helper.parse_patient_contact))
        self.assertTrue(callable(helper.parse_patient_identifiers))
        self.assertTrue(callable(helper.calculate_age))
        self.assertTrue(callable(helper.parse_condition))
        self.assertTrue(callable(helper.build_patient_summary))

        # Test that openrouter_chat is importable and callable
        self.assertTrue(callable(query_helpers.openrouter_chat))

class TestFHIRPatientData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join("data", "patients.json"), "r") as f:
            cls.data = json.load(f)

    def test_fhir_bundle_structure(self):
        # Test 3.1: Validate FHIR-like schema
        self.assertEqual(self.data["resourceType"], "Bundle")
        self.assertEqual(self.data["type"], "searchset")
        self.assertIn("entry", self.data)
        self.assertIsInstance(self.data["entry"], list)

    def test_patient_fields(self):
        # Test 3.2: Check required fields for each patient
        for entry in self.data["entry"]:
            resource = entry["resource"]
            if resource["resourceType"] != "Patient":
                continue
            # Name
            self.assertIn("name", resource)
            self.assertIsInstance(resource["name"], list)
            self.assertTrue(resource["name"][0]["given"])  # At least one given name
            self.assertTrue(resource["name"][0]["family"])  # Family name present
            # Age (birthDate)
            self.assertIn("birthDate", resource)
            self.assertRegex(resource["birthDate"], r"\d{4}-\d{2}-\d{2}")
            # Blood pressure (in extension)
            bp = [ext for ext in resource.get("extension", []) if "blood-pressure" in ext["url"]]
            self.assertTrue(bp)
            self.assertRegex(bp[0]["valueString"], r"\d{2,3}/\d{2,3}")
            # Chronic conditions (in extension)
            cc = [ext for ext in resource.get("extension", []) if "chronic-conditions" in ext["url"]]
            self.assertTrue(cc)
            self.assertIsInstance(cc[0]["valueString"], str)
            # Last visit (in extension)
            lv = [ext for ext in resource.get("extension", []) if "last-visit" in ext["url"]]
            self.assertTrue(lv)
            self.assertRegex(lv[0]["valueDate"], r"\d{4}-\d{2}-\d{2}")

if __name__ == '__main__':
    unittest.main() 