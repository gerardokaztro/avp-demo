# 🔐 AWS Verified Permissions — Live Demo
### AWS Student Community Day Perú 🇵🇪
**Speaker:** Gerardo Castro, AWS Security Hero

> Demo en vivo de AWS Verified Permissions: autorización centralizada con políticas Cedar, sin VPN, con Zero Trust nativo. Incluye un agente de IA que consulta AVP en lenguaje natural.

---

## 🗂 Estructura del Proyecto

```
avp-demo/
├── template.yaml          ← SAM Template (Lambda + API Gateway)
├── lambda/
│   ├── app.py             ← Lambda: verifica acceso con AVP (IsAuthorized)
│   ├── users.py           ← Lambda: lista usuarios y recursos para la UI
│   └── agent.py           ← Lambda: agente IA — proxy seguro hacia Anthropic
└── frontend/
    ├── index.html         ← Web App del lab principal
    ├── avp-agent.html     ← Agente IA con lenguaje natural + AVP
    └── avp-level3-concept.html ← Concepto nivel 3: lenguaje natural → Cedar
```

---

## 💰 Costos — Lee esto antes de deployar

| Componente | Costo | Requerido para |
|---|---|---|
| AWS Lambda | Gratis (Free Tier: 1M req/mes) | Todo |
| API Gateway | Gratis (Free Tier: 1M calls/mes) | Todo |
| AVP | ~$0.00015 por 1,000 requests | Todo |
| Anthropic API | ~$0.25 por 1M tokens (Haiku) | Solo agente IA |
| **Lab principal** | **≈ $0.00** | `index.html` |
| **Lab completo con agente** | **≈ $0.01 - $0.05 por sesión** | `avp-agent.html` |

> ⚠️ **La Anthropic API tiene costo por uso.** Para el agente de IA necesitas una cuenta en [console.anthropic.com](https://console.anthropic.com) con créditos cargados (mínimo $5). Si solo quieres el lab principal de AVP, puedes dejar el parámetro `AnthropicApiKey` con el valor `placeholder` — el `index.html` no lo usa.

---

## ⚙️ Pre-requisitos

```bash
aws --version        # AWS CLI v2+
sam --version        # SAM CLI v1.130+  →  brew install aws-sam-cli
python3 --version    # Python 3.11+

# Verifica que tu CLI esté autenticado
aws sts get-caller-identity
```

---

## 🚀 PASO A PASO: Deploy Completo

### PASO 1 — Crear el Policy Store en AVP

1. Ve a la consola AWS → busca **"Verified Permissions"**
2. Clic en **"Create policy store"**
3. Selecciona **"Empty policy store"** ← importante, NO usar Guided Setup
4. Dale un nombre: `FinancialDocsStore`
5. Clic en **"Create"**
6. **Copia el Policy Store ID** que aparece en el dashboard ← lo necesitas para el Paso 3

---

### PASO 2 — Crear el Schema

Dentro de tu Policy Store → **Schema → Edit** → borra todo y pega este JSON:

```json
{
    "FinancialApp": {
        "entityTypes": {
            "User": {
                "shape": {
                    "type": "Record",
                    "attributes": {
                        "department": {
                            "type": "String",
                            "required": true
                        },
                        "clearance_level": {
                            "type": "Long",
                            "required": true
                        }
                    }
                },
                "memberOfTypes": ["Role"]
            },
            "Document": {
                "shape": {
                    "type": "Record",
                    "attributes": {
                        "classification": {
                            "type": "String",
                            "required": true
                        },
                        "department": {
                            "type": "String",
                            "required": true
                        }
                    }
                }
            },
            "Role": {
                "memberOfTypes": []
            }
        },
        "actions": {
            "Read": {
                "appliesTo": {
                    "principalTypes": ["User"],
                    "resourceTypes": ["Document"]
                }
            },
            "Edit": {
                "appliesTo": {
                    "principalTypes": ["User"],
                    "resourceTypes": ["Document"]
                }
            },
            "Delete": {
                "appliesTo": {
                    "principalTypes": ["User"],
                    "resourceTypes": ["Document"]
                }
            }
        }
    }
}
```

> ⚠️ El campo `"memberOfTypes": ["Role"]` dentro de `User` es crítico — le dice a AVP que un User puede pertenecer a un Role, necesario para que Cedar evalúe `principal in Role::"Analyst"`.

Clic en **"Save changes"** ✅

---

### PASO 3 — Build & Deploy con SAM

```bash
cd avp-demo/
sam build
sam deploy --guided
```

**Responde las preguntas así:**

| Pregunta | Respuesta |
|---|---|
| Stack Name | `avp-demo` |
| AWS Region | `us-west-2` (o tu región) |
| Parameter PolicyStoreId | ← pega el ID del Paso 1 |
| Parameter AnthropicApiKey | ← tu `sk-ant-...` (o `placeholder` si no usarás el agente) |
| Confirm changes before deploy | `y` |
| Allow SAM CLI to create IAM roles | `y` |
| Disable rollback | `n` |
| CheckAccessFunction has no authentication. Is this okay? | `y` |
| GetUsersFunction has no authentication. Is this okay? | `y` |
| AgentFunction has no authentication. Is this okay? | `y` |
| Save arguments to configuration file | `y` |
| SAM configuration file [samconfig.toml] | ← solo presiona ENTER |
| SAM configuration environment [default] | ← solo presiona ENTER |
| Deploy this changeset? | `y` |

Al finalizar verás:
```
Outputs
-------
ApiUrl        = https://XXXXXXXX.execute-api.us-west-2.amazonaws.com/prod
AgentEndpoint = https://XXXXXXXX.execute-api.us-west-2.amazonaws.com/prod/agent
```

**Copia la `ApiUrl`** ← la necesitas para el Paso 4.

---

### PASO 4 — Configurar el Frontend

Abre **ambos** archivos en tu editor y actualiza la URL:

**`frontend/index.html`** — línea ~837:
```javascript
const API_BASE_URL = "https://XXXXXXXX.execute-api.us-west-2.amazonaws.com/prod";
```

**`frontend/avp-agent.html`** — línea ~237:
```javascript
const API_BASE = "https://XXXXXXXX.execute-api.us-west-2.amazonaws.com/prod";
```

> ⚠️ La URL debe terminar en `/prod` — sin agregar paths adicionales.

---

### PASO 5 — Levantar servidor local

```bash
cd avp-demo/frontend
python3 -m http.server 8000
```

Abre en tu browser:

| URL | Descripción |
|---|---|
| `http://localhost:8000/index.html` | Lab principal AVP |
| `http://localhost:8000/avp-agent.html` | Agente IA con lenguaje natural |
| `http://localhost:8000/avp-level3-concept.html` | Concepto nivel 3 (requiere Anthropic API Key en UI) |

> ⚠️ No abras los archivos con `file://` — el browser bloqueará las llamadas al API por CORS. Siempre usa `http://localhost:8000`.

---

## 🎬 FLUJO DE LA DEMO EN VIVO

> Antes de empezar: asegúrate de que tu Policy Store **no tenga ninguna política creada**.

### ACT 1 — Zero Trust: Deny por defecto ❌
1. Ingresa tu Policy Store ID en el campo de configuración
2. Selecciona **Alice Garcia** (Analyst, Finance)
3. Selecciona **Q4-Report-2024** → Acción **Read**
4. Resultado: 🚫 **DENY**

> *"Alice tiene credenciales válidas pero AVP dice DENY. Esto es Zero Trust: deny por defecto."*

---

### ACT 2 — Política Cedar activa en tiempo real ✅
Consola AVP → **Policies → Create → Static policy**

Nombre: `AllowAnalystReadOwnDepartment`
```cedar
permit (
  principal in FinancialApp::Role::"Analyst",
  action == FinancialApp::Action::"Read",
  resource
)
when {
  principal.department == resource.department
};
```

Repite la solicitud de Alice → ✅ **ALLOW**

> *"¿Cambié el código? No. ¿Redeployé? No. Solo agregué una política Cedar."*

---

### ACT 3 — ABAC: atributos que controlan el acceso
1. Selecciona **Carol Mendez** (Auditor, **HR**)
2. Selecciona **Q4-Report-2024** (departamento: **Finance**)
3. Acción **Read** → 🚫 **DENY**

Crea esta política:
```cedar
permit (
  principal in FinancialApp::Role::"Auditor",
  action == FinancialApp::Action::"Read",
  resource
);
```
Repite → ✅ **ALLOW**

---

### ACT 4 — forbid tiene precedencia sobre permit
Crea esta política para Carol:
```cedar
forbid (
  principal in FinancialApp::Role::"Auditor",
  action in [FinancialApp::Action::"Edit", FinancialApp::Action::"Delete"],
  resource
);
```

Carol intenta **Edit** → 🚫 **DENY**

> *"forbid siempre gana sobre permit — sin excepciones."*

---

### ACT 5 (Bonus) — Agente IA con lenguaje natural 🤖
Abre `http://localhost:8000/avp-agent.html` y escribe:

> *"Verifica acceso de todos los usuarios al Q4-Report-2024"*

El agente razona, hace múltiples llamadas a AVP y responde con contexto — todo sin que le digas cómo hacerlo.

---

## 📋 Resumen de la Demo

| Act | Usuario | Acción | Recurso | Resultado | Concepto |
|---|---|---|---|---|---|
| 1 | Alice (Analyst) | Read | Q4-Report-2024 | 🚫 DENY | Zero Trust: deny por defecto |
| 2 | Alice (Analyst) | Read | Q4-Report-2024 | ✅ ALLOW | Política Cedar en tiempo real |
| 3 | Carol (Auditor/HR) | Read | Q4-Report-2024 (Finance) | 🚫→✅ | ABAC: atributos del contexto |
| 4 | Carol (Auditor) | Edit | Q4-Report-2024 | 🚫 DENY | forbid > permit |
| 5 | Todos | Múltiples | Múltiples | Varía | Agente IA + AVP |

---

## 🤖 Agente IA — Arquitectura segura

```
Browser
  ↓
API Gateway → Lambda /agent   ← API Key de Anthropic vive aquí (segura)
                  ↓
            Anthropic API (Claude Haiku)
                  ↓
            check_avp_access() tool
                  ↓
            Lambda /check-access → AVP → ALLOW/DENY
```

> ✅ La API Key de Anthropic **nunca se expone en el frontend** — vive encriptada como variable de entorno en el Lambda.

---

## 🧹 Cleanup

```bash
# Elimina toda la infraestructura AWS
sam delete --stack-name avp-demo

# Elimina el Policy Store desde la consola AVP
```

---

## 📚 Recursos para seguir aprendiendo

- [AVP Documentación oficial](https://docs.aws.amazon.com/verifiedpermissions/)
- [Cedar Playground](https://www.cedarpolicy.com/en/playground) ← practica Cedar sin AWS
- [AVP Workshop oficial AWS](https://catalog.workshops.aws/verified-permissions)
- [Cedar en GitHub](https://github.com/cedar-policy/cedar)
- [Anthropic API Docs](https://docs.anthropic.com) ← para el agente IA
- [console.anthropic.com](https://console.anthropic.com) ← obtén tu API Key
