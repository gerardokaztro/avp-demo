"""
AVP Demo - Lambda Handler
AWS Student Community Day Peru
Speaker: Gerardo Castro, AWS Security Hero

Este Lambda recibe una solicitud de acceso y consulta
AWS Verified Permissions para tomar la decision de AuthZ.
"""

import json
import os
import boto3
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

avp_client = boto3.client("verifiedpermissions")
POLICY_STORE_ID = os.environ["POLICY_STORE_ID"]

# ─────────────────────────────────────────────────────────
#  Datos demo: usuarios con sus atributos y roles
#  En produccion estos vendrian de Cognito / tu IdP
# ─────────────────────────────────────────────────────────
DEMO_USERS = {
    "alice": {
        "name": "Alice Garcia",
        "department": "Finance",
        "clearance_level": 2,
        "role": "Analyst",          # <-- empieza SIN politica, luego la agregas
        "avatar": "👩‍💼"
    },
    "bob": {
        "name": "Bob Torres",
        "department": "Finance",
        "clearance_level": 3,
        "role": "Admin",
        "avatar": "👨‍💻"
    },
    "carol": {
        "name": "Carol Mendez",
        "department": "HR",
        "clearance_level": 1,
        "role": "Auditor",
        "avatar": "👩‍🔬"
    },
}

# Recursos demo disponibles
DEMO_RESOURCES = {
    "Q4-Report-2024": {"department": "Finance", "classification": "confidential"},
    "HR-Payroll-2024": {"department": "HR",      "classification": "restricted"},
    "Sales-Dashboard": {"department": "Sales",   "classification": "internal"},
}


def build_entity_list(user_id: str, resource_id: str) -> list:
    """
    Construye la lista de entidades que AVP necesita para evaluar la politica.
    Incluye el usuario con sus atributos, su rol, y el recurso.
    """
    user = DEMO_USERS[user_id]
    resource = DEMO_RESOURCES[resource_id]

    entities = [
        # Entidad: el usuario con sus atributos
        {
            "identifier": {
                "entityType": "FinancialApp::User",
                "entityId": user_id
            },
            "attributes": {
                "department":      {"string": user["department"]},
                "clearance_level": {"long":   user["clearance_level"]},
            },
            # El usuario es miembro del rol (RBAC via groups)
            "parents": [
                {
                    "entityType": "FinancialApp::Role",
                    "entityId": user["role"]
                }
            ]
        },
        # Entidad: el recurso con sus atributos
        {
            "identifier": {
                "entityType": "FinancialApp::Document",
                "entityId": resource_id
            },
            "attributes": {
                "department":      {"string": resource["department"]},
                "classification":  {"string": resource["classification"]},
            },
            "parents": []
        }
    ]
    return entities


def lambda_handler(event, context):
    """
    Endpoint principal: POST /check-access
    
    Body esperado:
    {
        "user":     "alice",
        "action":   "Read",
        "resource": "Q4-Report-2024"
    }
    """

    # ── CORS headers ──────────────────────────────────────
    headers = {
        "Content-Type":                "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers":"Content-Type",
        "Access-Control-Allow-Methods":"POST,OPTIONS",
    }

    # Manejar preflight OPTIONS
    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": headers, "body": ""}

    # ── Parsear body ──────────────────────────────────────
    try:
        body = json.loads(event.get("body", "{}"))
        user_id     = body["user"]
        action_id   = body["action"]
        resource_id = body["resource"]
    except (KeyError, json.JSONDecodeError) as e:
        return {
            "statusCode": 400,
            "headers": headers,
            "body": json.dumps({
                "error": f"Body invalido: {str(e)}",
                "expected": {"user": "alice", "action": "Read", "resource": "Q4-Report-2024"}
            })
        }

    # Validar que el usuario y recurso existan en el demo
    if user_id not in DEMO_USERS:
        return {
            "statusCode": 400,
            "headers": headers,
            "body": json.dumps({"error": f"Usuario '{user_id}' no existe. Opciones: {list(DEMO_USERS.keys())}"})
        }
    if resource_id not in DEMO_RESOURCES:
        return {
            "statusCode": 400,
            "headers": headers,
            "body": json.dumps({"error": f"Recurso '{resource_id}' no existe. Opciones: {list(DEMO_RESOURCES.keys())}"})
        }

    user = DEMO_USERS[user_id]

    # ── Llamar a AWS Verified Permissions ─────────────────
    logger.info(f"AVP Check: {user_id} -> {action_id} -> {resource_id}")

    try:
        avp_response = avp_client.is_authorized(
            policyStoreId=POLICY_STORE_ID,
            principal={
                "entityType": "FinancialApp::User",
                "entityId":    user_id
            },
            action={
                "actionType": "FinancialApp::Action",
                "actionId":    action_id
            },
            resource={
                "entityType": "FinancialApp::Document",
                "entityId":    resource_id
            },
            entities={
                "entityList": build_entity_list(user_id, resource_id)
            }
        )

        decision         = avp_response["decision"]           # "ALLOW" o "DENY"
        determining_policies = avp_response.get("determiningPolicies", [])
        errors           = avp_response.get("errors", [])

        logger.info(f"Decision AVP: {decision} | Policies: {determining_policies}")

        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({
                "decision":             decision,
                "allowed":              decision == "ALLOW",
                "user": {
                    "id":         user_id,
                    "name":       user["name"],
                    "role":       user["role"],
                    "department": user["department"],
                    "avatar":     user["avatar"],
                },
                "action":               action_id,
                "resource":             resource_id,
                "resource_info":        DEMO_RESOURCES[resource_id],
                "determining_policies": determining_policies,
                "errors":               errors,
                "message": (
                    f"✅ ACCESO PERMITIDO: {user['name']} puede {action_id} en {resource_id}"
                    if decision == "ALLOW" else
                    f"🚫 ACCESO DENEGADO: {user['name']} no tiene permisos para {action_id} en {resource_id}"
                )
            })
        }

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_msg  = e.response["Error"]["Message"]
        logger.error(f"ClientError AVP: {error_code} - {error_msg}")
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({
                "error":      f"Error en AVP: {error_code}",
                "details":    error_msg,
                "tip":        "Verifica que el POLICY_STORE_ID sea correcto y que el Lambda tenga permisos verifiedpermissions:IsAuthorized"
            })
        }

    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({"error": "Error interno", "details": str(e)})
        }
