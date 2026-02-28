"""
AVP Agent Lambda — Proxy hacia Anthropic API
El browser llama a este Lambda, el Lambda llama a Anthropic.
Así la API Key nunca se expone en el frontend.
"""

import json
import os
import boto3
import urllib.request
import urllib.error
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

avp_client = boto3.client("verifiedpermissions")
POLICY_STORE_ID = os.environ["POLICY_STORE_ID"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

HEADERS = {
    "Content-Type":                "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers":"Content-Type",
    "Access-Control-Allow-Methods":"POST,OPTIONS",
}

# ─── Usuarios y recursos demo ─────────────────────────────
DEMO_USERS = {
    "alice": {"name":"Alice Garcia",  "department":"Finance", "clearance_level":2, "role":"Analyst", "avatar":"👩‍💼"},
    "bob":   {"name":"Bob Torres",    "department":"Finance", "clearance_level":3, "role":"Admin",   "avatar":"👨‍💻"},
    "carol": {"name":"Carol Mendez",  "department":"HR",      "clearance_level":1, "role":"Auditor", "avatar":"👩‍🔬"},
}
DEMO_RESOURCES = {
    "Q4-Report-2024":  {"department":"Finance", "classification":"confidential"},
    "HR-Payroll-2024": {"department":"HR",      "classification":"restricted"},
    "Sales-Dashboard": {"department":"Sales",   "classification":"internal"},
}

# ─── Tool: check_avp_access ───────────────────────────────
def check_avp_access(user_id, action_id, resource_id):
    if user_id not in DEMO_USERS:
        return {"error": f"Usuario '{user_id}' no existe"}
    if resource_id not in DEMO_RESOURCES:
        return {"error": f"Recurso '{resource_id}' no existe"}

    user     = DEMO_USERS[user_id]
    resource = DEMO_RESOURCES[resource_id]

    try:
        response = avp_client.is_authorized(
            policyStoreId=POLICY_STORE_ID,
            principal={"entityType":"FinancialApp::User","entityId":user_id},
            action={"actionType":"FinancialApp::Action","actionId":action_id},
            resource={"entityType":"FinancialApp::Document","entityId":resource_id},
            entities={"entityList":[
                {
                    "identifier":{"entityType":"FinancialApp::User","entityId":user_id},
                    "attributes":{
                        "department":      {"string": user["department"]},
                        "clearance_level": {"long":   user["clearance_level"]},
                    },
                    "parents":[{"entityType":"FinancialApp::Role","entityId":user["role"]}]
                },
                {
                    "identifier":{"entityType":"FinancialApp::Document","entityId":resource_id},
                    "attributes":{
                        "department":     {"string": resource["department"]},
                        "classification": {"string": resource["classification"]},
                    },
                    "parents":[]
                }
            ]}
        )
        decision = response["decision"]
        return {
            "decision": decision,
            "allowed":  decision == "ALLOW",
            "user":     {**user, "id": user_id},
            "action":   action_id,
            "resource": resource_id,
            "resource_info": resource,
            "message": (
                f"✅ ACCESO PERMITIDO: {user['name']} puede {action_id} en {resource_id}"
                if decision == "ALLOW" else
                f"🚫 ACCESO DENEGADO: {user['name']} no tiene permisos para {action_id} en {resource_id}"
            )
        }
    except Exception as e:
        return {"error": str(e)}


# ─── Agentic loop ─────────────────────────────────────────
def run_agent(messages):
    """
    Ejecuta el loop agentico:
    1. Llama a Claude con tools disponibles
    2. Si Claude quiere usar una tool → ejecútala → devuelve resultado
    3. Repite hasta end_turn
    """

    tools = [{
        "name": "check_avp_access",
        "description": (
            "Verifica en AWS Verified Permissions si un usuario puede ejecutar "
            "una acción sobre un recurso. "
            "Usuarios: alice (Analyst/Finance), bob (Admin/Finance), carol (Auditor/HR). "
            "Acciones: Read, Edit, Delete. "
            "Recursos: Q4-Report-2024, HR-Payroll-2024, Sales-Dashboard."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "user":     {"type":"string","description":"alice, bob, o carol"},
                "action":   {"type":"string","description":"Read, Edit, o Delete"},
                "resource": {"type":"string","description":"Q4-Report-2024, HR-Payroll-2024, o Sales-Dashboard"}
            },
            "required": ["user","action","resource"]
        }
    }]

    system = (
        "Eres un agente de seguridad experto en AWS Verified Permissions. "
        "Responde preguntas sobre permisos usando la herramienta check_avp_access. "
        "NUNCA asumas el resultado — siempre verifica con la herramienta. "
        "Si preguntan por múltiples usuarios o recursos, verifica cada combinación. "
        "Explica brevemente por qué AVP tomó esa decisión (RBAC/ABAC/Cedar). "
        "Sé conciso. Responde siempre en español."
    )

    current_messages = list(messages)

    for _ in range(10):  # max 10 iteraciones
        payload = json.dumps({
            "model":      "claude-haiku-4-5-20251001",
            "max_tokens": 1000,
            "system":     system,
            "tools":      tools,
            "messages":   current_messages
        }).encode()

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type":      "application/json",
                "x-api-key":         ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
            },
            method="POST"
        )

        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())

        current_messages.append({"role":"assistant","content": data["content"]})

        # Respuesta final
        if data["stop_reason"] == "end_turn":
            text = " ".join(b["text"] for b in data["content"] if b["type"] == "text")
            return {"response": text, "messages": current_messages}

        # Tool use
        if data["stop_reason"] == "tool_use":
            tool_results = []
            for block in data["content"]:
                if block["type"] != "tool_use":
                    continue
                inp = block["input"]
                logger.info(f"Tool call: {block['name']}({inp})")
                result = check_avp_access(inp["user"], inp["action"], inp["resource"])
                tool_results.append({
                    "type":        "tool_result",
                    "tool_use_id": block["id"],
                    "content":     json.dumps(result)
                })
            current_messages.append({"role":"user","content": tool_results})

    return {"response": "No pude completar la consulta. Intenta de nuevo.", "messages": current_messages}


# ─── Handler ──────────────────────────────────────────────
def lambda_handler(event, context):
    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode":200,"headers":HEADERS,"body":""}

    try:
        body     = json.loads(event.get("body","{}"))
        messages = body.get("messages", [])
        if not messages:
            raise ValueError("Campo 'messages' requerido")
    except Exception as e:
        return {"statusCode":400,"headers":HEADERS,"body":json.dumps({"error":str(e)})}

    try:
        result = run_agent(messages)
        return {"statusCode":200,"headers":HEADERS,"body":json.dumps(result)}
    except urllib.error.HTTPError as e:
        err = json.loads(e.read())
        logger.error(f"Anthropic API error: {err}")
        return {"statusCode":500,"headers":HEADERS,"body":json.dumps({"error": err.get("error",{}).get("message","Error en Anthropic API")})}
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {"statusCode":500,"headers":HEADERS,"body":json.dumps({"error":str(e)})}
