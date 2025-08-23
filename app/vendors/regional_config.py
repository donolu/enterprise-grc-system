"""
Regional Configuration System for Vendor Due Diligence

Provides flexible configuration for region-specific due diligence requirements,
compliance standards, and custom fields based on geographical location.
"""

import json


# Predefined Regional Configurations
REGIONAL_CONFIGS = {
    "US": {
        "region_name": "United States",
        "description": "US-specific vendor due diligence requirements",
        "required_fields": {
            "tax_id": True,
            "duns_number": True,
            "annual_spend": True,
            "security_assessment_completed": True
        },
        "custom_fields": [
            {
                "field_name": "ein_number",
                "field_type": "text",
                "label": "Employer Identification Number (EIN)",
                "required": True,
                "validation": {"pattern": r"^\d{2}-\d{7}$", "message": "EIN must be in format XX-XXXXXXX"}
            },
            {
                "field_name": "minority_owned",
                "field_type": "boolean",
                "label": "Minority-Owned Business Enterprise (MBE)",
                "required": False
            },
            {
                "field_name": "woman_owned",
                "field_type": "boolean", 
                "label": "Woman-Owned Small Business (WOSB)",
                "required": False
            }
        ],
        "compliance_standards": [
            "SOX", "HIPAA", "PCI-DSS", "FERPA", "GLBA", "CCPA"
        ],
        "data_processing_requirements": {
            "cross_border_transfer_allowed": False,
            "data_residency_required": True,
            "privacy_framework": "CCPA/CPRA"
        }
    },
    "EU": {
        "region_name": "European Union",
        "description": "EU-specific vendor due diligence requirements including GDPR compliance",
        "required_fields": {
            "data_processing_agreement": True,
            "security_assessment_completed": True,
            "tax_id": True
        },
        "custom_fields": [
            {
                "field_name": "vat_number",
                "field_type": "text",
                "label": "VAT Number",
                "required": True,
                "validation": {"pattern": r"^[A-Z]{2}[0-9A-Z]+$", "message": "Invalid VAT number format"}
            },
            {
                "field_name": "gdpr_representative",
                "field_type": "text",
                "label": "GDPR Representative",
                "required": True
            },
            {
                "field_name": "data_protection_officer",
                "field_type": "text",
                "label": "Data Protection Officer Contact",
                "required": False
            }
        ],
        "compliance_standards": [
            "GDPR", "ISO 27001", "SOC 2", "NIS2", "DGA", "DSA"
        ],
        "data_processing_requirements": {
            "gdpr_compliance_required": True,
            "lawful_basis_documented": True,
            "data_transfer_mechanism": "Standard Contractual Clauses",
            "privacy_framework": "GDPR"
        }
    },
    "UK": {
        "region_name": "United Kingdom",
        "description": "UK-specific vendor due diligence requirements post-Brexit",
        "required_fields": {
            "data_processing_agreement": True,
            "security_assessment_completed": True,
            "tax_id": True
        },
        "custom_fields": [
            {
                "field_name": "companies_house_number",
                "field_type": "text",
                "label": "Companies House Number",
                "required": True,
                "validation": {"pattern": r"^[0-9]{8}$", "message": "Companies House number must be 8 digits"}
            },
            {
                "field_name": "uk_gdpr_compliant",
                "field_type": "boolean",
                "label": "UK GDPR Compliant",
                "required": True
            }
        ],
        "compliance_standards": [
            "UK GDPR", "ISO 27001", "Cyber Essentials", "SOC 2"
        ],
        "data_processing_requirements": {
            "uk_gdpr_compliance_required": True,
            "adequacy_decision_status": "Self-Assessment Required",
            "privacy_framework": "UK GDPR"
        }
    },
    "CA": {
        "region_name": "Canada",
        "description": "Canadian vendor due diligence requirements",
        "required_fields": {
            "tax_id": True,
            "security_assessment_completed": True
        },
        "custom_fields": [
            {
                "field_name": "business_number",
                "field_type": "text",
                "label": "Canada Business Number (BN)",
                "required": True,
                "validation": {"pattern": r"^\d{9}[A-Z]{2}\d{4}$", "message": "Invalid Canadian Business Number format"}
            },
            {
                "field_name": "pipeda_compliant",
                "field_type": "boolean",
                "label": "PIPEDA Compliant",
                "required": True
            }
        ],
        "compliance_standards": [
            "PIPEDA", "ISO 27001", "SOC 2", "Provincial Privacy Laws"
        ],
        "data_processing_requirements": {
            "pipeda_compliance_required": True,
            "cross_border_disclosure": "Consent or Legal Authority Required",
            "privacy_framework": "PIPEDA"
        }
    },
    "APAC": {
        "region_name": "Asia Pacific",
        "description": "Asia Pacific region vendor requirements",
        "required_fields": {
            "security_assessment_completed": True
        },
        "custom_fields": [
            {
                "field_name": "local_registration_number",
                "field_type": "text",
                "label": "Local Business Registration Number", 
                "required": True
            },
            {
                "field_name": "data_localization_compliant",
                "field_type": "boolean",
                "label": "Data Localization Compliant",
                "required": True
            },
            {
                "field_name": "country_specific_requirements",
                "field_type": "textarea",
                "label": "Country-Specific Compliance Requirements",
                "required": False
            }
        ],
        "compliance_standards": [
            "ISO 27001", "SOC 2", "Local Privacy Laws", "Data Localization Requirements"
        ],
        "data_processing_requirements": {
            "data_localization_required": True,
            "cross_border_restrictions": "Country-Specific",
            "privacy_framework": "Country-Specific"
        }
    }
}


def get_regional_config(region_code):
    """Get regional configuration for a specific region."""
    from .models import RegionalConfig
    try:
        return RegionalConfig.objects.get(region_code=region_code, is_active=True)
    except RegionalConfig.DoesNotExist:
        return None


def get_required_fields_for_region(region_code):
    """Get list of required fields for a specific region."""
    config = get_regional_config(region_code)
    if config:
        return config.required_fields
    return {}


def get_custom_fields_for_region(region_code):
    """Get list of custom fields for a specific region."""
    config = get_regional_config(region_code)
    if config:
        return config.custom_fields
    return []


def validate_vendor_for_region(vendor_data, region_code):
    """Validate vendor data against regional requirements."""
    config = get_regional_config(region_code)
    if not config:
        return True, []
    
    errors = []
    
    # Check required standard fields
    for field_name, required in config.required_fields.items():
        if required and not vendor_data.get(field_name):
            errors.append(f"{field_name} is required for region {region_code}")
    
    # Check custom field requirements
    for custom_field in config.custom_fields:
        field_name = custom_field['field_name']
        if custom_field.get('required', False):
            if not vendor_data.get(field_name):
                errors.append(f"{custom_field['label']} is required for region {region_code}")
        
        # Validate field format if data is provided
        if vendor_data.get(field_name) and 'validation' in custom_field:
            import re
            pattern = custom_field['validation']['pattern']
            if not re.match(pattern, str(vendor_data[field_name])):
                errors.append(custom_field['validation']['message'])
    
    return len(errors) == 0, errors


def setup_default_regional_configs():
    """Set up default regional configurations."""
    from .models import RegionalConfig
    for region_code, config_data in REGIONAL_CONFIGS.items():
        region_config, created = RegionalConfig.objects.get_or_create(
            region_code=region_code,
            defaults=config_data
        )
        if created:
            print(f"Created regional config for {region_code}")
        else:
            print(f"Regional config for {region_code} already exists")