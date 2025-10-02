from typing import List, Dict, Any
import json


def create_function_tools() -> List[Dict[str, Any]]:
    """Define OpenAI function tools for the agent."""
    
    return [
        {
            "type": "function",
            "function": {
                "name": "verify_business_license",
                "description": "Verify customer's business license with state authorities. Call this after collecting the license number from the customer.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "license_number": {
                            "type": "string",
                            "description": "The business license number provided by the customer"
                        }
                    },
                    "required": ["license_number"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_available_equipment",
                "description": "Search for available equipment based on customer needs. Use natural language from customer request.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "search_query": {
                            "type": "string",
                            "description": "Natural language search query from customer (e.g., 'excavator for foundation work', 'forklift under $400')"
                        }
                    },
                    "required": ["search_query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "select_equipment",
                "description": "Select specific equipment by ID after customer chooses.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "equipment_id": {
                            "type": "string",
                            "description": "The equipment ID (e.g., EQ001)"
                        }
                    },
                    "required": ["equipment_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "verify_site_safety",
                "description": "Verify job site can safely accommodate selected equipment.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "job_address": {
                            "type": "string",
                            "description": "The job site address provided by customer"
                        }
                    },
                    "required": ["job_address"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "propose_price",
                "description": "Propose a negotiated price for the equipment rental.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "proposed_daily_rate": {
                            "type": "number",
                            "description": "The proposed daily rental rate"
                        },
                        "rental_days": {
                            "type": "integer",
                            "description": "Number of days for rental"
                        }
                    },
                    "required": ["proposed_daily_rate"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "accept_price",
                "description": "Accept the agreed price and move to operator verification.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "confirmed_daily_rate": {
                            "type": "number",
                            "description": "The confirmed daily rental rate"
                        }
                    },
                    "required": ["confirmed_daily_rate"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "verify_operator_credentials",
                "description": "Verify operator has proper certifications for selected equipment.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "operator_name": {
                            "type": "string",
                            "description": "Name of the equipment operator"
                        },
                        "operator_license": {
                            "type": "string",
                            "description": "Operator's license/certification number"
                        },
                        "operator_phone": {
                            "type": "string",
                            "description": "Operator's contact phone number"
                        }
                    },
                    "required": ["operator_name", "operator_license", "operator_phone"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "verify_insurance_coverage",
                "description": "Verify customer's insurance meets minimum requirements for selected equipment.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "policy_number": {
                            "type": "string",
                            "description": "Insurance policy number"
                        }
                    },
                    "required": ["policy_number"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "complete_booking",
                "description": "Finalize the rental booking and update inventory.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "end_call",
                "description": "End the call gracefully with a reason.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "description": "Reason for ending the call (e.g., 'completed', 'failed_verification', 'no_equipment')"
                        }
                    },
                    "required": ["reason"]
                }
            }
        }
    ]


def format_equipment_for_context(equipment_list: List[Dict]) -> str:
    """Format equipment list for LLM context."""
    if not equipment_list:
        return "No equipment available."
    
    formatted = "Available Equipment:\n\n"
    for eq in equipment_list:
        formatted += f"ID: {eq['Equipment ID']}\n"
        formatted += f"Name: {eq['Equipment Name']}\n"
        formatted += f"Category: {eq['Category']}\n"
        formatted += f"Daily Rate: ${eq['Daily Rate']}\n"
        formatted += f"Max Rate: ${eq['Max Rate']}\n"
        formatted += f"Weight Class: {eq['Weight Class']}\n"
        formatted += f"Location: {eq['Storage Location']}\n"
        formatted += f"Required Cert: {eq['Operator Cert Required']}\n"
        formatted += f"Min Insurance: ${eq['Min Insurance']}\n"
        formatted += "---\n"
    
    return formatted

