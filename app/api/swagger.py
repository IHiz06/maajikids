"""
MaajiKids — Swagger UI Manual
Sirve /api/docs con Swagger UI + /api/spec con OpenAPI 3.0 JSON.

Por qué no usar flask-smorest directamente:
  flask-smorest requiere registrar TODOS los blueprints a través de su objeto Api,
  lo que requeriría anotar cada endpoint con @blp.arguments/@blp.response.
  Para no romper la arquitectura existente, servimos un spec OpenAPI 3.0
  generado automáticamente desde las rutas registradas en Flask.
"""
from flask import Blueprint, jsonify, render_template_string, current_app

bp = Blueprint("swagger", __name__)

SWAGGER_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MaajiKids API v5.0 — Documentación</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.11.0/swagger-ui.min.css">
  <style>
    body { margin: 0; background: #fafafa; }
    .topbar { background: #E91E8C !important; }
    .topbar-wrapper .link { display: none; }
    .swagger-ui .topbar { padding: 8px 0; }
    .info .title { color: #E91E8C !important; }
    h2.title::after { content: " — Centro de Estimulación Temprana"; font-size: 14px; color: #888; }
  </style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.11.0/swagger-ui-bundle.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.11.0/swagger-ui-standalone-preset.min.js"></script>
  <script>
    window.onload = () => {
      SwaggerUIBundle({
        url: "/api/spec",
        dom_id: '#swagger-ui',
        presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
        layout: "StandaloneLayout",
        deepLinking: true,
        persistAuthorization: true,
        displayRequestDuration: true,
        tryItOutEnabled: true,
        filter: true,
      });
    };
  </script>
</body>
</html>"""


OPENAPI_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "MaajiKids Backend API",
        "version": "5.0.0",
        "description": (
            "**Backend completo** del Centro de Estimulación Temprana y Psicoprofilaxis MaajiKids.\n\n"
            "## Autenticación\n"
            "Todos los endpoints protegidos requieren el header:\n"
            "```\nAuthorization: Bearer <access_token>\n```\n"
            "Obtén el token con `POST /autenticacion/iniciar-sesion`.\n\n"
            "## Roles del sistema\n"
            "- **admin**: Control total\n"
            "- **teacher**: Evaluaciones + talleres asignados\n"
            "- **secretary**: Inscripciones + mensajes + DNI\n"
            "- **parent**: Panel propio + carrito + pagos\n\n"
            "## Admin por defecto (desarrollo)\n"
            "Email: `admin@maajikids.com` | Password: `Admin123!`"
        ),
        "contact": {"name": "MaajiKids", "email": "admin@maajikids.com"},
    },
    "servers": [
        {"url": "http://localhost:5000", "description": "Desarrollo local"},
        {"url": "https://maajikids-backend.onrender.com", "description": "Producción (Render)"},
    ],
    "components": {
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "Token obtenido de POST /autenticacion/iniciar-sesion",
            }
        },
        "schemas": {
            "Success": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean", "example": True},
                    "message": {"type": "string"},
                    "data": {"type": "object"},
                },
            },
            "Error": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean", "example": False},
                    "message": {"type": "string"},
                },
            },
            "LoginRequest": {
                "type": "object",
                "required": ["email", "password"],
                "properties": {
                    "email": {"type": "string", "format": "email", "example": "admin@maajikids.com"},
                    "password": {"type": "string", "example": "Admin123!"},
                },
            },
            "RegisterRequest": {
                "type": "object",
                "required": ["email", "password", "first_name", "last_name"],
                "properties": {
                    "email": {"type": "string", "format": "email"},
                    "password": {"type": "string", "minLength": 8},
                    "first_name": {"type": "string"},
                    "last_name": {"type": "string"},
                    "phone": {"type": "string"},
                },
            },
            "WorkshopCreate": {
                "type": "object",
                "required": ["title", "description", "schedule", "age_min", "age_max", "max_capacity", "price"],
                "properties": {
                    "title": {"type": "string", "example": "ESTIMULACIÓN SENSORIAL"},
                    "description": {"type": "string"},
                    "schedule": {"type": "string", "example": "LUNES Y MIÉRCOLES 10:00AM"},
                    "age_min": {"type": "integer", "description": "Edad mínima en meses", "example": 6},
                    "age_max": {"type": "integer", "description": "Edad máxima en meses (max 72)", "example": 36},
                    "max_capacity": {"type": "integer", "example": 15},
                    "price": {"type": "number", "example": 150.00},
                    "teacher_id": {"type": "integer", "nullable": True},
                },
            },
            "ChildCreate": {
                "type": "object",
                "required": ["full_name", "date_of_birth", "gender"],
                "properties": {
                    "full_name": {"type": "string", "example": "SOFIA GARCIA"},
                    "date_of_birth": {"type": "string", "format": "date", "example": "2022-05-10"},
                    "gender": {"type": "string", "enum": ["M", "F", "OTRO"]},
                    "medical_info": {"type": "string", "description": "Se cifra con AES-256"},
                    "allergies": {"type": "string"},
                },
            },
            "OrderCreate": {
                "type": "object",
                "required": ["items"],
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["child_id", "workshop_id"],
                            "properties": {
                                "child_id": {"type": "integer"},
                                "workshop_id": {"type": "integer"},
                            },
                        },
                    }
                },
            },
            "VerifyPayment": {
                "type": "object",
                "required": ["payment_id", "order_id"],
                "properties": {
                    "payment_id": {"type": "string", "description": "ID de pago de MercadoPago", "example": "12345678"},
                    "order_id": {"type": "integer", "description": "ID de orden en el sistema", "example": 1},
                },
            },
            "EvaluationCreate": {
                "type": "object",
                "required": ["child_id", "workshop_id", "eval_date", "score_cognitive", "score_motor", "score_language", "score_social"],
                "properties": {
                    "child_id": {"type": "integer"},
                    "workshop_id": {"type": "integer"},
                    "eval_date": {"type": "string", "format": "date"},
                    "score_cognitive": {"type": "number", "minimum": 0, "maximum": 10},
                    "score_motor": {"type": "number", "minimum": 0, "maximum": 10},
                    "score_language": {"type": "number", "minimum": 0, "maximum": 10},
                    "score_social": {"type": "number", "minimum": 0, "maximum": 10},
                    "observations": {"type": "string"},
                },
            },
        },
    },
    "security": [{"BearerAuth": []}],
    "paths": {
        # ── AUTENTICACIÓN ──────────────────────────────────────────────────
        "/autenticacion/registrar": {
            "post": {
                "tags": ["1. Autenticación"],
                "summary": "Registrar nuevo usuario (parent)",
                "security": [],
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/RegisterRequest"}}}},
                "responses": {"201": {"description": "Usuario creado. Revisa tu email para verificar."}, "409": {"description": "Email ya registrado"}},
            }
        },
        "/autenticacion/verificar-correo": {
            "post": {
                "tags": ["1. Autenticación"],
                "summary": "Verificar email con código",
                "security": [],
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "properties": {"email": {"type": "string"}, "codigo": {"type": "string", "example": "123456"}}}}}},
                "responses": {"200": {"description": "Email verificado"}, "400": {"description": "Código incorrecto o expirado"}},
            }
        },
        "/autenticacion/reenviar-verificacion": {
            "post": {
                "tags": ["1. Autenticación"],
                "summary": "Reenviar código de verificación",
                "security": [],
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "properties": {"email": {"type": "string"}}}}}},
                "responses": {"200": {"description": "Código reenviado"}},
            }
        },
        "/autenticacion/iniciar-sesion": {
            "post": {
                "tags": ["1. Autenticación"],
                "summary": "Login — Obtener access_token + refresh_token",
                "security": [],
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/LoginRequest"}}}},
                "responses": {
                    "200": {"description": "Login exitoso. Guarda access_token y refresh_token."},
                    "401": {"description": "Credenciales incorrectas"},
                    "403": {"description": "Email no verificado o cuenta desactivada"},
                },
            }
        },
        "/autenticacion/renovar-token": {
            "post": {
                "tags": ["1. Autenticación"],
                "summary": "Renovar access_token con refresh_token",
                "description": "Usa el refresh_token en el header Authorization.",
                "responses": {"200": {"description": "Nuevo access_token generado"}, "401": {"description": "Refresh token inválido o sesión inactiva >40 min"}},
            }
        },
        "/autenticacion/cerrar-sesion": {
            "post": {
                "tags": ["1. Autenticación"],
                "summary": "Cerrar sesión (revoca el token)",
                "responses": {"200": {"description": "Sesión cerrada. Token revocado."}},
            }
        },
        "/autenticacion/olvide-contrasena": {
            "post": {
                "tags": ["1. Autenticación"],
                "summary": "Solicitar código de restablecimiento de contraseña",
                "security": [],
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "properties": {"email": {"type": "string"}}}}}},
                "responses": {"200": {"description": "Código enviado al email (si existe)"}},
            }
        },
        "/autenticacion/restablecer-contrasena": {
            "post": {
                "tags": ["1. Autenticación"],
                "summary": "Restablecer contraseña con código",
                "security": [],
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "properties": {"email": {"type": "string"}, "codigo": {"type": "string"}, "nueva_password": {"type": "string", "minLength": 8}}}}}},
                "responses": {"200": {"description": "Contraseña restablecida"}},
            }
        },
        # ── USUARIOS ───────────────────────────────────────────────────────
        "/usuarios/": {
            "get": {
                "tags": ["2. Usuarios"],
                "summary": "Listar usuarios (admin)",
                "parameters": [{"name": "rol", "in": "query", "schema": {"type": "string", "enum": ["admin", "teacher", "secretary", "parent"]}}, {"name": "page", "in": "query", "schema": {"type": "integer"}}, {"name": "per_page", "in": "query", "schema": {"type": "integer"}}],
                "responses": {"200": {"description": "Lista de usuarios"}},
            },
            "post": {
                "tags": ["2. Usuarios"],
                "summary": "Crear usuario con cualquier rol (admin)",
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "properties": {"email": {"type": "string"}, "password": {"type": "string"}, "first_name": {"type": "string"}, "last_name": {"type": "string"}, "role_id": {"type": "integer"}, "phone": {"type": "string"}}}}}},
                "responses": {"201": {"description": "Usuario creado"}},
            },
        },
        "/usuarios/yo": {
            "get": {
                "tags": ["2. Usuarios"],
                "summary": "Ver mi perfil",
                "responses": {"200": {"description": "Perfil del usuario autenticado"}},
            }
        },
        "/usuarios/{id}": {
            "get": {"tags": ["2. Usuarios"], "summary": "Detalle de usuario", "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}], "responses": {"200": {"description": "Detalle"}}},
            "patch": {"tags": ["2. Usuarios"], "summary": "Actualizar usuario", "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}], "requestBody": {"content": {"application/json": {"schema": {"type": "object"}}}}, "responses": {"200": {"description": "Actualizado"}}},
            "delete": {"tags": ["2. Usuarios"], "summary": "Desactivar usuario (admin)", "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}], "responses": {"200": {"description": "Desactivado"}}},
        },
        # ── ROLES ──────────────────────────────────────────────────────────
        "/roles/": {
            "get": {"tags": ["3. Roles"], "summary": "Listar roles (admin)", "responses": {"200": {"description": "Lista de roles"}}},
            "post": {
                "tags": ["3. Roles"],
                "summary": "Crear rol personalizado (admin)",
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "properties": {"name": {"type": "string"}, "description": {"type": "string"}, "permissions": {"type": "object", "example": {"workshops": {"read": True, "write": True, "delete": False}}}}}}}},
                "responses": {"201": {"description": "Rol creado"}},
            },
        },
        "/roles/{id}": {
            "get": {"tags": ["3. Roles"], "summary": "Detalle de rol", "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}], "responses": {"200": {"description": "Rol"}}},
            "patch": {"tags": ["3. Roles"], "summary": "Actualizar rol personalizado", "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}], "responses": {"200": {"description": "Actualizado"}}},
            "delete": {"tags": ["3. Roles"], "summary": "Eliminar rol personalizado", "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}], "responses": {"200": {"description": "Eliminado"}}},
        },
        # ── TALLERES ───────────────────────────────────────────────────────
        "/talleres/": {
            "get": {
                "tags": ["4. Talleres"],
                "summary": "Listar talleres (público)",
                "security": [],
                "parameters": [
                    {"name": "asignados", "in": "query", "description": "true = solo mis talleres (teacher)", "schema": {"type": "boolean"}},
                    {"name": "activo", "in": "query", "schema": {"type": "boolean"}},
                    {"name": "page", "in": "query", "schema": {"type": "integer"}},
                ],
                "responses": {"200": {"description": "Lista de talleres"}},
            },
            "post": {
                "tags": ["4. Talleres"],
                "summary": "Crear taller (admin) — soporta multipart con imagen",
                "requestBody": {"content": {"multipart/form-data": {"schema": {"$ref": "#/components/schemas/WorkshopCreate"}}, "application/json": {"schema": {"$ref": "#/components/schemas/WorkshopCreate"}}}},
                "responses": {"201": {"description": "Taller creado"}},
            },
        },
        "/talleres/{id}": {
            "get": {"tags": ["4. Talleres"], "summary": "Detalle de taller (público)", "security": [], "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}], "responses": {"200": {"description": "Taller"}}},
            "patch": {"tags": ["4. Talleres"], "summary": "Actualizar taller (admin)", "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}], "responses": {"200": {"description": "Actualizado"}}},
            "delete": {"tags": ["4. Talleres"], "summary": "Desactivar taller (admin)", "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}], "responses": {"200": {"description": "Desactivado"}}},
        },
        # ── NIÑOS ──────────────────────────────────────────────────────────
        "/ninos/": {
            "get": {
                "tags": ["5. Niños"],
                "summary": "Listar niños según rol",
                "parameters": [
                    {"name": "taller_id", "in": "query", "schema": {"type": "integer"}},
                    {"name": "dni_pendiente", "in": "query", "description": "true = solo DNI pendientes", "schema": {"type": "boolean"}},
                ],
                "responses": {"200": {"description": "Lista de niños"}},
            },
            "post": {
                "tags": ["5. Niños"],
                "summary": "Registrar niño (parent/admin/secretary)",
                "description": "Acepta JSON o multipart/form-data (con foto opcional).",
                "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/ChildCreate"}}, "multipart/form-data": {"schema": {"$ref": "#/components/schemas/ChildCreate"}}}},
                "responses": {"201": {"description": "Niño registrado"}},
            },
        },
        "/ninos/{id}": {
            "get": {"tags": ["5. Niños"], "summary": "Detalle del niño (descifra datos médicos)", "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}], "responses": {"200": {"description": "Niño"}}},
            "patch": {"tags": ["5. Niños"], "summary": "Actualizar niño", "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}], "responses": {"200": {"description": "Actualizado"}}},
            "delete": {"tags": ["5. Niños"], "summary": "Desactivar niño (admin)", "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}], "responses": {"200": {"description": "Desactivado"}}},
        },
        "/ninos/{id}/dni": {
            "post": {
                "tags": ["5. Niños — DNI"],
                "summary": "Subir documento DNI a Supabase Storage",
                "description": "**Requiere multipart/form-data.**\n\nEl archivo puede enviarse en el campo `dni`, `file` o `document`.\n\nFormatos aceptados: JPEG, PNG, WEBP, PDF (máx. 5MB).\n\nRequiere `SUPABASE_URL` y `SUPABASE_SERVICE_KEY` en `.env` y el bucket `dni-documents` creado como **privado** en Supabase Storage.",
                "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "multipart/form-data": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "dni": {"type": "string", "format": "binary", "description": "Archivo DNI (también acepta 'file' o 'document')"},
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "201": {"description": "DNI subido. Estado: dni_pending_review=true"},
                    "400": {"description": "Archivo inválido o faltante"},
                    "500": {"description": "Error de Supabase (verifica credenciales y bucket)"},
                },
            },
            "patch": {
                "tags": ["5. Niños — DNI"],
                "summary": "Verificar DNI (admin/secretary)",
                "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "properties": {"dni_verified": {"type": "boolean", "example": True}}}}}},
                "responses": {"200": {"description": "DNI verificado o rechazado"}},
            },
        },
        # ── CONTACTOS DE EMERGENCIA ────────────────────────────────────────
        "/ninos/{id}/contactos-emergencia/": {
            "get": {"tags": ["6. Contactos Emergencia"], "summary": "Listar contactos (máx. 3)", "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}], "responses": {"200": {"description": "Contactos"}}},
            "post": {"tags": ["6. Contactos Emergencia"], "summary": "Agregar contacto de emergencia", "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}], "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"full_name": {"type": "string"}, "phone": {"type": "string"}, "relationship": {"type": "string"}, "is_primary": {"type": "boolean"}}}}}}, "responses": {"201": {"description": "Contacto agregado"}}},
        },
        "/ninos/{child_id}/contactos-emergencia/{cid}": {
            "patch": {"tags": ["6. Contactos Emergencia"], "summary": "Actualizar contacto", "parameters": [{"name": "child_id", "in": "path", "required": True, "schema": {"type": "integer"}}, {"name": "cid", "in": "path", "required": True, "schema": {"type": "integer"}}], "responses": {"200": {"description": "Actualizado"}}},
            "delete": {"tags": ["6. Contactos Emergencia"], "summary": "Eliminar contacto (mín. 1 siempre)", "parameters": [{"name": "child_id", "in": "path", "required": True, "schema": {"type": "integer"}}, {"name": "cid", "in": "path", "required": True, "schema": {"type": "integer"}}], "responses": {"200": {"description": "Eliminado"}}},
        },
        # ── ÓRDENES ────────────────────────────────────────────────────────
        "/ordenes/": {
            "get": {"tags": ["7. Órdenes / Carrito"], "summary": "Listar órdenes (parent ve las suyas)", "parameters": [{"name": "nino_id", "in": "query", "schema": {"type": "integer"}}, {"name": "estado", "in": "query", "schema": {"type": "string", "enum": ["pending", "approved", "rejected", "cancelled"]}}], "responses": {"200": {"description": "Órdenes"}}},
            "post": {
                "tags": ["7. Órdenes / Carrito"],
                "summary": "Crear orden (carrito multi-ítem)",
                "description": "Si ya existe una orden 'pending' para el mismo niño+taller, la REUTILIZA y retorna `orden_existente: true` con HTTP 200.",
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/OrderCreate"}}}},
                "responses": {"201": {"description": "Orden nueva creada"}, "200": {"description": "Orden pending reutilizada"}, "409": {"description": "Ya inscrito o ya pagado"}},
            },
        },
        "/ordenes/{id}": {
            "get": {"tags": ["7. Órdenes / Carrito"], "summary": "Detalle de orden", "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}], "responses": {"200": {"description": "Orden"}}},
            "delete": {"tags": ["7. Órdenes / Carrito"], "summary": "Cancelar orden pending", "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}], "responses": {"200": {"description": "Cancelada"}}},
        },
        "/ordenes/{id}/pago": {
            "post": {
                "tags": ["7. Órdenes / Carrito"],
                "summary": "Generar preferencia MercadoPago → checkout_url",
                "description": "Retorna `{preference_id, checkout_url}`. El frontend redirige al usuario a `checkout_url`.",
                "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                "responses": {"200": {"description": "Preferencia generada con checkout_url"}},
            }
        },
        # ── PAGOS ──────────────────────────────────────────────────────────
        "/pagos/": {
            "get": {"tags": ["8. Pagos"], "summary": "Historial de pagos", "parameters": [{"name": "estado", "in": "query", "schema": {"type": "string"}}, {"name": "desde", "in": "query", "schema": {"type": "string", "format": "date"}}, {"name": "hasta", "in": "query", "schema": {"type": "string", "format": "date"}}], "responses": {"200": {"description": "Pagos"}}},
        },
        "/pagos/{id}": {
            "get": {"tags": ["8. Pagos"], "summary": "Detalle de pago", "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}], "responses": {"200": {"description": "Pago"}}},
        },
        "/pagos/verificar": {
            "post": {
                "tags": ["8. Pagos"],
                "summary": "✅ Verificar pago con API de MercadoPago",
                "description": (
                    "**Este es el endpoint más importante del flujo de pagos.**\n\n"
                    "Llámalo cuando MercadoPago redirija al usuario de vuelta a tu sitio.\n\n"
                    "**Flujo completo:**\n"
                    "1. `POST /ordenes/` → crea orden\n"
                    "2. `POST /ordenes/:id/pago` → obtiene `checkout_url`\n"
                    "3. Redirige al usuario a `checkout_url` (MercadoPago)\n"
                    "4. MP redirige a `MP_SUCCESS_URL?payment_id=XXX&external_reference=ORDER_ID`\n"
                    "5. Frontend llama `POST /pagos/verificar` con `{payment_id, order_id}`\n"
                    "6. Si `status: approved` → la orden queda como PAGADA y los enrollments se activan.\n\n"
                    "**Si el pago queda en pending:** Llama este endpoint de nuevo en unos minutos.\n\n"
                    "**Para debug:** Usa `GET /pagos/debug-mp/:payment_id` (solo admin)."
                ),
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/VerifyPayment"},
                            "example": {"payment_id": "12345678901", "order_id": 1},
                        }
                    },
                },
                "responses": {
                    "200": {"description": "Pago procesado (approved/rejected/pending)"},
                    "400": {"description": "Datos inválidos o monto no coincide"},
                    "502": {"description": "Error conectando con MercadoPago"},
                },
            }
        },
        "/pagos/debug-mp/{payment_id}": {
            "get": {
                "tags": ["8. Pagos"],
                "summary": "🔧 Debug: respuesta raw de MercadoPago (solo admin)",
                "description": "Muestra exactamente qué devuelve la API de MP para un payment_id. Útil para diagnosticar pagos.",
                "parameters": [{"name": "payment_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "responses": {"200": {"description": "Respuesta raw de MP"}},
            }
        },
        # ── EVALUACIONES ───────────────────────────────────────────────────
        "/evaluaciones/": {
            "get": {"tags": ["9. Evaluaciones"], "summary": "Listar evaluaciones", "parameters": [{"name": "nino_id", "in": "query", "schema": {"type": "integer"}}, {"name": "taller_id", "in": "query", "schema": {"type": "integer"}}, {"name": "teacher_id", "in": "query", "schema": {"type": "integer"}}], "responses": {"200": {"description": "Evaluaciones"}}},
            "post": {"tags": ["9. Evaluaciones"], "summary": "Crear evaluación (teacher/admin)", "description": "El niño debe tener `payment_status=verified` y `dni_verified=true`.", "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/EvaluationCreate"}}}}, "responses": {"201": {"description": "Evaluación registrada"}}},
        },
        "/evaluaciones/{id}": {
            "get": {"tags": ["9. Evaluaciones"], "summary": "Detalle de evaluación", "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}], "responses": {"200": {"description": "Evaluación"}}},
            "patch": {"tags": ["9. Evaluaciones"], "summary": "Actualizar evaluación", "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}], "responses": {"200": {"description": "Actualizada"}}},
            "delete": {"tags": ["9. Evaluaciones"], "summary": "Eliminar evaluación (admin)", "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}], "responses": {"200": {"description": "Eliminada"}}},
        },
        # ── IA ─────────────────────────────────────────────────────────────
        "/ia/recomendaciones/generar": {
            "post": {
                "tags": ["10. Inteligencia Artificial"],
                "summary": "Generar recomendaciones IA (Gemini 2.5 Flash)",
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "properties": {"evaluation_id": {"type": "integer"}, "regenerar": {"type": "boolean", "default": False}}}}}},
                "responses": {"201": {"description": "Recomendaciones generadas"}},
            }
        },
        "/ia/recomendaciones/nino/{id}": {
            "get": {"tags": ["10. Inteligencia Artificial"], "summary": "Listar recomendaciones del niño", "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}], "responses": {"200": {"description": "Recomendaciones"}}},
        },
        "/ia/recomendaciones/{id}": {
            "get": {"tags": ["10. Inteligencia Artificial"], "summary": "Detalle de recomendación", "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}], "responses": {"200": {"description": "Recomendación"}}},
            "patch": {"tags": ["10. Inteligencia Artificial"], "summary": "Actualizar / cambiar visibilidad (admin)", "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}], "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"is_visible_to_parent": {"type": "boolean"}, "recommendations_text": {"type": "string"}}}}}}, "responses": {"200": {"description": "Actualizada"}}},
            "delete": {"tags": ["10. Inteligencia Artificial"], "summary": "Eliminar recomendación (admin)", "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}], "responses": {"200": {"description": "Eliminada"}}},
        },
        "/ia/chat": {
            "post": {
                "tags": ["10. Inteligencia Artificial"],
                "summary": "Chat con asistente 'Maaji' (público, sin login)",
                "security": [],
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "properties": {"mensaje": {"type": "string", "example": "¿Qué talleres tienen para bebés de 6 meses?"}, "session_token": {"type": "string", "description": "Token de sesión anónima (opcional, se crea si no se envía)"}}}}}},
                "responses": {"200": {"description": "Respuesta del asistente + session_token"}},
            }
        },
        "/ia/chat/historial": {
            "get": {
                "tags": ["10. Inteligencia Artificial"],
                "summary": "Historial de chat (sin ?sesion_id: lista sesiones; con ?sesion_id: mensajes)",
                "parameters": [{"name": "sesion_id", "in": "query", "schema": {"type": "integer"}}],
                "responses": {"200": {"description": "Sesiones o mensajes"}},
            }
        },
        # ── CONTACTO ───────────────────────────────────────────────────────
        "/contacto/": {
            "post": {
                "tags": ["11. Contacto"],
                "summary": "Enviar mensaje de contacto (público)",
                "security": [],
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "properties": {"sender_name": {"type": "string"}, "sender_email": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string", "minLength": 10}}}}}},
                "responses": {"201": {"description": "Mensaje enviado"}},
            },
            "get": {"tags": ["11. Contacto"], "summary": "Listar mensajes (admin/secretary)", "parameters": [{"name": "estado", "in": "query", "schema": {"type": "string", "enum": ["unread", "read", "replied"]}}], "responses": {"200": {"description": "Mensajes"}}},
        },
        "/contacto/{id}": {
            "get": {"tags": ["11. Contacto"], "summary": "Detalle de mensaje", "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}], "responses": {"200": {"description": "Mensaje"}}},
            "patch": {
                "tags": ["11. Contacto"],
                "summary": "Actualizar estado o responder (admin/secretary)",
                "description": "Si incluyes `reply_text` → envía email de respuesta al remitente y marca como 'replied'.\nSi solo incluyes `status` → actualiza el estado.",
                "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"reply_text": {"type": "string"}, "status": {"type": "string", "enum": ["unread", "read", "replied"]}}}}}},
                "responses": {"200": {"description": "Actualizado"}},
            },
            "delete": {"tags": ["11. Contacto"], "summary": "Eliminar mensaje (admin)", "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}], "responses": {"200": {"description": "Eliminado"}}},
        },
        # ── REPORTES PDF ───────────────────────────────────────────────────
        "/reportes/nino/{id}": {
            "get": {
                "tags": ["12. Reportes PDF"],
                "summary": "PDF del niño (evaluaciones o recomendaciones)",
                "parameters": [
                    {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}},
                    {"name": "tipo", "in": "query", "required": True, "schema": {"type": "string", "enum": ["evaluaciones", "recomendaciones"]}},
                ],
                "responses": {"200": {"description": "PDF", "content": {"application/pdf": {}}}},
            }
        },
        "/reportes/pagos": {
            "get": {
                "tags": ["12. Reportes PDF"],
                "summary": "PDF reporte de pagos aprobados",
                "parameters": [{"name": "desde", "in": "query", "schema": {"type": "string", "format": "date"}}, {"name": "hasta", "in": "query", "schema": {"type": "string", "format": "date"}}],
                "responses": {"200": {"description": "PDF", "content": {"application/pdf": {}}}},
            }
        },
        "/reportes/inscripciones": {
            "get": {"tags": ["12. Reportes PDF"], "summary": "PDF inscripciones activas (admin/secretary)", "responses": {"200": {"description": "PDF", "content": {"application/pdf": {}}}}}
        },
        "/reportes/taller/{id}/ninos": {
            "get": {"tags": ["12. Reportes PDF"], "summary": "PDF lista de niños de un taller", "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}], "responses": {"200": {"description": "PDF", "content": {"application/pdf": {}}}}}
        },
    },
    "tags": [
        {"name": "1. Autenticación", "description": "Registro, login, JWT, recuperación de contraseña"},
        {"name": "2. Usuarios", "description": "Gestión de usuarios del sistema"},
        {"name": "3. Roles", "description": "Roles del sistema y personalizados (JSONB)"},
        {"name": "4. Talleres", "description": "Catálogo de talleres (público sin login)"},
        {"name": "5. Niños", "description": "Registro de niños, foto y verificación de DNI"},
        {"name": "5. Niños — DNI", "description": "Flujo de subida y verificación de documentos DNI"},
        {"name": "6. Contactos Emergencia", "description": "Contactos de emergencia por niño (máx. 3)"},
        {"name": "7. Órdenes / Carrito", "description": "Carrito multi-ítem con reutilización de órdenes pending"},
        {"name": "8. Pagos", "description": "Verificación activa de pagos con MercadoPago (sin webhook)"},
        {"name": "9. Evaluaciones", "description": "Evaluaciones en 4 dominios (0-10) por profesor"},
        {"name": "10. Inteligencia Artificial", "description": "Gemini 2.5 Flash: recomendaciones + asistente Maaji"},
        {"name": "11. Contacto", "description": "Mensajes de contacto desde la web pública"},
        {"name": "12. Reportes PDF", "description": "Generación de PDFs con logo MaajiKids (ReportLab)"},
    ],
}


@bp.route("/api/docs")
def swagger_ui():
    """Swagger UI — Documentación interactiva."""
    return render_template_string(SWAGGER_HTML)


@bp.route("/api/spec")
def openapi_spec():
    """OpenAPI 3.0 JSON spec."""
    return jsonify(OPENAPI_SPEC)
