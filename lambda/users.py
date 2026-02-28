"""
Helper Lambda: retorna la lista de usuarios demo
para poblar la UI del frontend.
"""

import json

DEMO_USERS = [
    {
        "id":         "alice",
        "name":       "Alice Garcia",
        "role":       "Analyst",
        "department": "Finance",
        "clearance":  2,
        "avatar":     "👩‍💼",
        "description":"Analista Financiera - SIN politica inicial en AVP"
    },
    {
        "id":         "bob",
        "name":       "Bob Torres",
        "role":       "Admin",
        "department": "Finance",
        "clearance":  3,
        "avatar":     "👨‍💻",
        "description":"Administrador - Tiene politica RBAC Admin en AVP"
    },
    {
        "id":         "carol",
        "name":       "Carol Mendez",
        "role":       "Auditor",
        "department": "HR",
        "clearance":  1,
        "avatar":     "👩‍🔬",
        "description":"Auditora HR - Solo puede leer, no editar ni borrar"
    },
]

DEMO_RESOURCES = [
    {"id": "Q4-Report-2024",  "label": "📊 Q4 Report 2024",  "department": "Finance", "classification": "confidential"},
    {"id": "HR-Payroll-2024", "label": "💰 HR Payroll 2024", "department": "HR",      "classification": "restricted"},
    {"id": "Sales-Dashboard", "label": "📈 Sales Dashboard", "department": "Sales",   "classification": "internal"},
]

DEMO_ACTIONS = ["Read", "Edit", "Delete"]


def lambda_handler(event, context):
    headers = {
        "Content-Type":                "application/json",
        "Access-Control-Allow-Origin": "*",
    }
    return {
        "statusCode": 200,
        "headers":    headers,
        "body": json.dumps({
            "users":     DEMO_USERS,
            "resources": DEMO_RESOURCES,
            "actions":   DEMO_ACTIONS,
        })
    }
