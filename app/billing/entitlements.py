from dataclasses import dataclass


@dataclass(frozen=True)
class ModuleDefinition:
    key: str
    label: str
    description: str


MODULE_CATALOG = [
    ModuleDefinition('frameworks', 'Frameworks', 'ISO, PCI, NIST and control assessment workflows'),
    ModuleDefinition('risk', 'Risk Management', 'Risk register, treatment plans and action tracking'),
    ModuleDefinition('vendors', 'Third-Party Management', 'Vendor inventory, reviews, tasks and follow-up dates'),
    ModuleDefinition('policies', 'Policies', 'Policy, standard and procedure library and acknowledgements'),
    ModuleDefinition('training', 'Training', 'Security awareness campaigns and training material'),
    ModuleDefinition('assets', 'Asset Management', 'Information asset register and ownership reviews'),
    ModuleDefinition('analytics', 'Analytics', 'Product, compliance and executive dashboards'),
    ModuleDefinition('exports', 'Exports', 'Tenant data, reports and downloadable artefacts'),
    ModuleDefinition('calendar', 'Calendar', 'Cross-module dates, events and reminders'),
    ModuleDefinition('vulnerability_scanning', 'Vulnerability Scanning', 'Scanner integration and vulnerability reporting'),
]

ALL_MODULE_KEYS = tuple(module.key for module in MODULE_CATALOG)
MODULE_BY_KEY = {module.key: module for module in MODULE_CATALOG}

DEFAULT_PLAN_MODULES = {
    'free': ('frameworks',),
    'basic': ('frameworks', 'risk', 'vendors', 'policies', 'assets', 'exports'),
    'enterprise': ALL_MODULE_KEYS,
}

MODULE_PATH_PREFIXES = (
    ('/api/catalogs/', 'frameworks'),
    ('/api/risk/', 'risk'),
    ('/api/vendors/', 'vendors'),
    ('/api/policies/', 'policies'),
    ('/api/training/', 'training'),
    ('/api/assets/', 'assets'),
    ('/api/calendar/', 'calendar'),
    ('/api/analytics/', 'analytics'),
    ('/api/exports/', 'exports'),
    ('/api/vuln/', 'vulnerability_scanning'),
)


def normalise_modules(modules):
    seen = set()
    normalised = []
    for module in modules or []:
        key = str(module or '').strip()
        if key in MODULE_BY_KEY and key not in seen:
            seen.add(key)
            normalised.append(key)
    return normalised


def get_default_modules_for_plan(plan_slug):
    return list(DEFAULT_PLAN_MODULES.get(plan_slug, ()))


def get_module_catalog(enabled_modules=None):
    enabled = set(enabled_modules or [])
    return [
        {
            'key': module.key,
            'label': module.label,
            'description': module.description,
            'enabled': module.key in enabled,
        }
        for module in MODULE_CATALOG
    ]


def get_module_for_path(path):
    for prefix, module_key in MODULE_PATH_PREFIXES:
        if path.startswith(prefix):
            return module_key
    return None
