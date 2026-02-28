# 🔐 AWS Verified Permissions — Live Demo
### AWS Student Community Day Perú 🇵🇪
**Speaker:** Gerardo Castro, AWS Security Hero

> Demo en vivo de AWS Verified Permissions: autorización centralizada con políticas Cedar, sin VPN, con Zero Trust nativo.

---

## 🗂 Estructura del Proyecto

```
avp-demo/
├── template.yaml          ← SAM Template (Lambda + API Gateway)
├── lambda/
│   ├── app.py             ← Lambda principal (llama a AVP IsAuthorized)
│   └── users.py           ← Lambda helper (lista usuarios y recursos para la UI)
└── frontend/
    └── index.html         ← Web App (se abre directo en el browser)
```

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

# Build
sam build

# Deploy guiado
sam deploy --guided
```

**Responde las preguntas así:**

| Pregunta | Respuesta |
|---|---|
| Stack Name | `avp-demo` |
| AWS Region | `us-west-2` (o tu región) |
| Parameter PolicyStoreId | ← pega el ID del Paso 1 |
| Confirm changes before deploy | `y` |
| Allow SAM CLI to create IAM roles | `y` |
| Disable rollback | `n` |
| CheckAccessFunction has no authentication. Is this okay? | `y` |
| GetUsersFunction has no authentication. Is this okay? | `y` |
| Save arguments to configuration file | `y` |
| SAM configuration file [samconfig.toml] | ← solo presiona ENTER |
| SAM configuration environment [default] | ← solo presiona ENTER |
| Deploy this changeset? | `y` |

Al finalizar verás:
```
Outputs
-------
ApiUrl = https://XXXXXXXX.execute-api.us-west-2.amazonaws.com/prod
```

**Copia esa URL** ← la necesitas para el Paso 4.

---

### PASO 4 — Configurar el Frontend

Abre `frontend/index.html` en tu editor y busca la línea ~837:

```javascript
// ANTES:
const API_BASE_URL = "https://TU_API_ID.execute-api.us-east-1.amazonaws.com/prod";

// DESPUÉS — pega tu URL del Paso 3 (sin slash al final, sin /check-access):
const API_BASE_URL = "https://XXXXXXXX.execute-api.us-west-2.amazonaws.com/prod";
```

> ⚠️ La URL debe terminar en `/prod` — sin agregar `/check-access` ni ningún path adicional.

---

### PASO 5 — Levantar servidor local y probar

```bash
cd avp-demo/frontend
python3 -m http.server 8000
```

Abre en tu browser:
```
http://localhost:8000/index.html
```

> ⚠️ No abras el archivo directo con `file://` — el browser bloqueará las llamadas al API por CORS. Siempre usa `http://localhost:8000`.

---

## 🎬 FLUJO DE LA DEMO EN VIVO

> Antes de empezar: asegúrate de que tu Policy Store **no tenga ninguna política creada**.

---

### ACT 1 — Zero Trust: Deny por defecto ❌
1. Ingresa tu Policy Store ID en el campo de configuración de la app
2. Selecciona **Alice Garcia** (Analyst, Finance)
3. Selecciona **Q4-Report-2024**
4. Acción: **Read**
5. Clic en **"Verificar con AVP"**
6. Resultado: 🚫 **DENY**

**Mensaje para la audiencia:**
> *"Alice tiene credenciales válidas y está autenticada. Pero AVP dice DENY. ¿Por qué? Porque no existe ninguna política Cedar que lo permita. Esto es Zero Trust: deny por defecto, sin excepciones."*

---

### ACT 2 — Política Cedar activa en tiempo real ✅
Ve a la consola AVP → **Policies → Create policy → Static policy**

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

Vuelve a la app — **sin recargar, sin redeployar** — y repite la misma solicitud de Alice.

Resultado: ✅ **ALLOW**

**Mensaje para la audiencia:**
> *"¿Cambié el código? No. ¿Redeployé el Lambda? No. Solo agregué una política Cedar. La autorización vive fuera de la aplicación — eso es AVP."*

---

### ACT 3 — ABAC: atributos que controlan el acceso 🚫
1. Selecciona **Carol Mendez** (Auditor, **HR**)
2. Selecciona **Q4-Report-2024** (departamento: **Finance**)
3. Acción: **Read**
4. Resultado: 🚫 **DENY**

**Mensaje para la audiencia:**
> *"Carol está autenticada y tiene rol Auditor. Pero el documento es de Finance y Carol es de HR. AVP comparó los atributos de ambos y dijo DENY. Eso es ABAC — el acceso depende de los atributos, no solo del rol."*

Crea esta política:

```cedar
permit (
  principal in FinancialApp::Role::"Auditor",
  action == FinancialApp::Action::"Read",
  resource
);
```

Repite la solicitud → ✅ **ALLOW**

---

### ACT 4 — forbid tiene precedencia sobre permit 🚫
Crea esta segunda política para Carol:

```cedar
forbid (
  principal in FinancialApp::Role::"Auditor",
  action in [FinancialApp::Action::"Edit", FinancialApp::Action::"Delete"],
  resource
);
```

En la app:
1. Selecciona **Carol Mendez**
2. Selecciona **Q4-Report-2024**
3. Acción: **Edit**
4. Resultado: 🚫 **DENY**

**Mensaje para la audiencia:**
> *"Carol tiene permit para Read pero forbid para Edit y Delete. En Cedar, forbid siempre gana sobre permit — sin excepciones. Puedes dar acceso amplio y restringir quirúrgicamente acciones específicas."*

---

## 📋 Resumen de la Demo

| Act | Usuario | Acción | Recurso | Resultado | Concepto |
|---|---|---|---|---|---|
| 1 | Alice (Analyst) | Read | Q4-Report-2024 | 🚫 DENY | Zero Trust: deny por defecto |
| 2 | Alice (Analyst) | Read | Q4-Report-2024 | ✅ ALLOW | Política Cedar en tiempo real |
| 3 | Carol (Auditor/HR) | Read | Q4-Report-2024 (Finance) | 🚫 DENY → ✅ ALLOW | ABAC: atributos del usuario vs recurso |
| 4 | Carol (Auditor) | Edit | Q4-Report-2024 | 🚫 DENY | forbid > permit |

---

## 🧹 Cleanup

```bash
# Elimina toda la infraestructura AWS
sam delete --stack-name avp-demo

# Elimina el Policy Store desde la consola AVP
```

---

## 💰 Costos estimados de la demo

| Servicio | Costo |
|---|---|
| Lambda | Gratis (Free Tier: 1M requests/mes) |
| API Gateway | Gratis (Free Tier: 1M calls/mes) |
| AVP | ~$0.00015 por cada 1,000 requests |
| **Demo completa** | **≈ $0.00** |

---

## 📚 Recursos para seguir aprendiendo

- [AVP Documentación oficial](https://docs.aws.amazon.com/verifiedpermissions/)
- [Cedar Playground](https://www.cedarpolicy.com/en/playground) ← practica Cedar sin AWS
- [AVP Workshop oficial AWS](https://catalog.workshops.aws/verified-permissions)
- [Cedar en GitHub](https://github.com/cedar-policy/cedar) ← open source
