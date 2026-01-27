from enum import Enum
from itertools import product

class DocType(Enum):
    TYPE_1 = 1
    TYPE_2 = 2
    TYPE_3 = 3
    TYPE_4 = 4
    TYPE_5 = 5
    UNDEFINED = -1

BAN_STRING = "BAN"
EMBG_EDB_STRING = "EMBG_EDB"
CONTRACT_DATE_STRING = "contract_date"
RESIDENT_CUSTOMER_STRING = "customer_type_resident"
BUSINESS_CUSTOMER_STRING = "customer_type_business"

def generate_all_date_regex_combinations() -> list[tuple[str]]:
    denumerators = [".", ",", "-"]
    size = 2
    date_regexes = []
    cartesian_product = list(product(denumerators, repeat=size))
    # print(f"{cartesian_product=}")
    for prod in cartesian_product:
        date_regexes.append("\\d{2}" + f"\\{prod[0]}" + "\\d{2}" + f"\\{prod[1]}" + "\\d{2,4}")
    return date_regexes

DATE_REGEXES = generate_all_date_regex_combinations()

DOCUMENT_REGEXES = {
    DocType.TYPE_1: 
    {
        BAN_STRING: "комуникациски услуги бр\\.\\s(\\d{9})",
        CONTRACT_DATE_STRING: DATE_REGEXES,
        "customer_type": "(?<=ПРЕТПЛАТНИК).*?(?=Име и презиме)",
        EMBG_EDB_STRING: "ЕМБГ\\:\\s(\\d{13})"
    },
    DocType.TYPE_2: 
    {
        BAN_STRING: "комуникациски услуги бр\\.\\s(\\d{9})",
        CONTRACT_DATE_STRING: DATE_REGEXES,
        "customer_type": {
            "preceding": "КОРИСНИК",
            "delimiter": " ",
            "unchanged": "[^\\s]+\\s([^\\s]+\\s[^\\s]+)"
        },
        EMBG_EDB_STRING: {
            "preceding": "ЕМБГ\\:Адреса\\:",
            "delimiter": " ",
            "unchanged": "(\\d{13})"
        }
    },
    DocType.TYPE_3: 
    {
        BAN_STRING: "комуникациски услуги бр\\.\\s(\\d{9})",
        CONTRACT_DATE_STRING: DATE_REGEXES,
        "customer_type": "(?<=ПРЕТПЛАТНИК).*?(?=Име и презиме)",
        EMBG_EDB_STRING: "ЕМБГ\\:\\s(\\d{13})"
    },
    DocType.TYPE_4: 
    {
        BAN_STRING: "BAN (\\d{9})",
        CONTRACT_DATE_STRING: DATE_REGEXES,
        "customer_type": "(?<=ПРЕТПЛАТНИК).*?(?=Име и презиме)",
        EMBG_EDB_STRING: {
            "preceding": "ЕМБГ:",
            "delimiter": " ",
            "unchanged": "(\\d{13})"
        }
    },
    DocType.TYPE_4: 
    {
        BAN_STRING: "BAN (\\d{9})",
        CONTRACT_DATE_STRING: DATE_REGEXES,
        "customer_type": "(?<=ПРЕТПЛАТНИК).*?(?=Име и презиме)",
        EMBG_EDB_STRING: {
            "preceding": "ЕМБГ:",
            "delimiter": " ",
            "unchanged": "(\\d{13})"
        }
    }
}

CONFIG = {
    DocType.TYPE_1: 
    {
        "has_table_bounds": True,
        "has_checkbox": True,
        "ambiguous_embg": False
    },
    DocType.TYPE_2: 
    {
        "has_table_bounds": False,
        "has_checkbox": False,
        "ambiguous_embg": True
    },
    DocType.TYPE_3: 
    {
        "has_table_bounds": True,
        "has_checkbox": True,
        "ambiguous_embg": False
    },
    DocType.TYPE_4: 
    {
        "has_table_bounds": False,
        "has_checkbox": False,
        "ambiguous_embg": False
    },
    DocType.TYPE_5: 
    {
        "has_table_bounds": True,
        "has_checkbox": True,
        "ambiguous_embg": False
    }
}

DOCUMENT_LAYOUT = {
    DocType.TYPE_1:
    {
        'bounds':
        [
            {
                'table': [

                ],
                'checbox': [

                ]
            }
        ]
    },
    DocType.TYPE_2:
    {
        'bounds':
        [
            {
                'table': [
                    (0.075, 0.185),
                    (0.925, 0.265)
                ]
            },
            {
                'checkbox': [
                    (0.225, 0.175),
                    (0.6, 0.225)
                ]
            }
        ]
    },
    DocType.TYPE_3: 
    {
        'table': 
        [
            (0.075, 0.195),
            (0.925, 0.275)
        ],
        'checkbox': 
        [
            (0.225, 0.175),
            (0.6, 0.225)
        ]
    },
    DocType.TYPE_4: 
    {
        'bounds': 
        [
            {
                'table': [
                    (0.075, 0.185),
                    (0.925, 0.265)
                ]
            },
            {
                'checkbox': [
                    (0.225, 0.175),
                    (0.6, 0.21)
                ]
            }
        ]
    },
    DocType.TYPE_5: 
    {
        'bounds': 
        [
            {
                'table': [
                    
                ]
            },
            {
                'checkbox': [
                    (0.225, 0.15),
                    (0.6, 0.2)
                ]
            }
        ]
    }
}