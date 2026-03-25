# MaajiKids Backend API v5.0

**Centro de Estimulación Temprana y Psicoprofilaxis**

Stack: Python 3.13 · Flask 3.1 · Supabase/PostgreSQL · MercadoPago Checkout Pro · Gemini 2.5 Flash · Cloudinary · ReportLab

---

## ⚡ Arranque rápido (3 pasos)

### 1. Clonar e instalar dependencias

```bash
git clone <repo>
cd maajikids-backend

python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
# Edita .env con tus valores reales (ver sección Variables de Entorno)
```

### 3. Arrancar

```bash
python run.py
```

El backend arranca en `http://localhost:5000`
Documentación Swagger: `http://localhost:5000/api/docs`

---

## 🗄️ Base de Datos (Supabase)

### Opción A — SQLAlchemy automático (recomendado para desarrollo)

El archivo `app/__init__.py` ejecuta `db.create_all()` al arrancar.
Las tablas se crean automáticamente. Los 4 roles del sistema también.

**Usuario admin por defecto (solo dev):**
- Email: `admin@maajikids.com`
- Password: `Admin123!`
- ⚠️ **Cambia esta contraseña inmediatamente en producción.**

### Opción B — Script SQL manual (recomendado para producción/Supabase)

1. Abre el **SQL Editor** en tu proyecto de Supabase.
2. Pega y ejecuta el contenido de `schema.sql`.
3. Verifica que el bucket `dni-documents` se creó en **Storage**.

---

## 🔧 Variables de Entorno

| Variable | Descripción | Dónde obtenerla |
|---|---|---|
| `DATABASE_URL` | URL PostgreSQL de Supabase | Supabase → Settings → Database → Connection string |
| `JWT_SECRET_KEY` | Clave secreta JWT | Genera: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `FERNET_KEY` | Clave cifrado AES-256 | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `MAIL_USERNAME` | Cuenta Gmail | Gmail → App Passwords |
| `MAIL_PASSWORD` | App Password Gmail | Gmail → Seguridad → App Passwords |
| `MP_ACCESS_TOKEN` | Token MercadoPago | developers.mercadopago.com → Credenciales |
| `GEMINI_API_KEY` | API Key Gemini | aistudio.google.com |
| `CLOUDINARY_*` | Credenciales Cloudinary | cloudinary.com → Dashboard |
| `SUPABASE_URL` | URL del proyecto | Supabase → Settings → API |
| `SUPABASE_SERVICE_KEY` | Service Role Key | Supabase → Settings → API → service_role |

---

## 📋 Endpoints (63 total)

### `/autenticacion` — Autenticación
| Método | Endpoint | Acceso |
|--------|----------|--------|
| POST | `/autenticacion/registrar` | Público |
| POST | `/autenticacion/verificar-correo` | Público |
| POST | `/autenticacion/reenviar-verificacion` | Público |
| POST | `/autenticacion/iniciar-sesion` | Público |
| POST | `/autenticacion/renovar-token` | refresh_token |
| POST | `/autenticacion/cerrar-sesion` | JWT |
| POST | `/autenticacion/olvide-contrasena` | Público |
| POST | `/autenticacion/restablecer-contrasena` | Público |

### `/usuarios` — Usuarios
| Método | Endpoint | Acceso |
|--------|----------|--------|
| GET | `/usuarios/` | admin |
| POST | `/usuarios/` | admin |
| GET | `/usuarios/yo` | JWT |
| GET | `/usuarios/:id` | admin/propio |
| PATCH | `/usuarios/:id` | admin/propio |
| DELETE | `/usuarios/:id` | admin |

### `/roles` — Roles
| Método | Endpoint | Acceso |
|--------|----------|--------|
| GET | `/roles/` | admin |
| POST | `/roles/` | admin |
| GET | `/roles/:id` | admin |
| PATCH | `/roles/:id` | admin |
| DELETE | `/roles/:id` | admin |

### `/talleres` — Talleres
| Método | Endpoint | Acceso |
|--------|----------|--------|
| GET | `/talleres/` | Público |
| GET | `/talleres/:id` | Público |
| POST | `/talleres/` | admin |
| PATCH | `/talleres/:id` | admin |
| DELETE | `/talleres/:id` | admin |

### `/ninos` — Niños
| Método | Endpoint | Acceso |
|--------|----------|--------|
| GET | `/ninos/` | admin/secretary/teacher/parent |
| POST | `/ninos/` | parent/admin/secretary |
| GET | `/ninos/:id` | parent(propio)/admin/secretary |
| PATCH | `/ninos/:id` | parent(propio)/admin/secretary |
| DELETE | `/ninos/:id` | admin |
| POST | `/ninos/:id/dni` | parent(propio)/admin/secretary |
| PATCH | `/ninos/:id/dni` | admin/secretary |

### `/ninos/:id/contactos-emergencia` — Contactos de Emergencia
| Método | Endpoint | Acceso |
|--------|----------|--------|
| GET | `/ninos/:id/contactos-emergencia/` | parent(propio)/admin/secretary |
| POST | `/ninos/:id/contactos-emergencia/` | parent(propio)/admin/secretary |
| PATCH | `/ninos/:id/contactos-emergencia/:cid` | parent(propio)/admin |
| DELETE | `/ninos/:id/contactos-emergencia/:cid` | parent(propio)/admin |

### `/ordenes` — Carrito y Órdenes
| Método | Endpoint | Acceso |
|--------|----------|--------|
| GET | `/ordenes/` | parent/admin/secretary |
| POST | `/ordenes/` | parent |
| GET | `/ordenes/:id` | parent(propio)/admin/secretary |
| POST | `/ordenes/:id/pago` | parent |
| DELETE | `/ordenes/:id` | parent/admin |

### `/pagos` — Pagos
| Método | Endpoint | Acceso |
|--------|----------|--------|
| GET | `/pagos/` | parent/admin/secretary |
| GET | `/pagos/:id` | parent(propio)/admin/secretary |
| POST | `/pagos/verificar` | parent |

### `/evaluaciones` — Evaluaciones
| Método | Endpoint | Acceso |
|--------|----------|--------|
| GET | `/evaluaciones/` | admin/teacher/parent |
| POST | `/evaluaciones/` | teacher/admin |
| GET | `/evaluaciones/:id` | teacher(propio)/admin/parent(propio) |
| PATCH | `/evaluaciones/:id` | teacher(propio)/admin |
| DELETE | `/evaluaciones/:id` | admin |

### `/ia` — Inteligencia Artificial
| Método | Endpoint | Acceso |
|--------|----------|--------|
| POST | `/ia/recomendaciones/generar` | teacher/admin |
| GET | `/ia/recomendaciones/nino/:id` | parent(propio)/teacher/admin |
| GET | `/ia/recomendaciones/:id` | parent(propio)/teacher/admin |
| PATCH | `/ia/recomendaciones/:id` | admin |
| DELETE | `/ia/recomendaciones/:id` | admin |
| POST | `/ia/chat` | Público |
| GET | `/ia/chat/historial` | parent/admin |

### `/contacto` — Mensajes de Contacto
| Método | Endpoint | Acceso |
|--------|----------|--------|
| POST | `/contacto/` | Público |
| GET | `/contacto/` | admin/secretary |
| GET | `/contacto/:id` | admin/secretary |
| PATCH | `/contacto/:id` | admin/secretary |
| DELETE | `/contacto/:id` | admin |

### `/reportes` — PDFs
| Método | Endpoint | Acceso |
|--------|----------|--------|
| GET | `/reportes/nino/:id?tipo=evaluaciones` | admin/teacher/parent |
| GET | `/reportes/nino/:id?tipo=recomendaciones` | admin/teacher/parent |
| GET | `/reportes/pagos` | admin/secretary |
| GET | `/reportes/inscripciones` | admin/secretary |
| GET | `/reportes/taller/:id/ninos` | admin/teacher |

---

## 🔐 Flujo de Roles — Qué puede hacer cada uno

### Admin (`admin@maajikids.com`)
- Acceso total al sistema.
- Crea usuarios con cualquier rol.
- Crea/edita/desactiva talleres.
- Verifica DNI de niños.
- Genera y elimina reportes PDF.
- Crea roles personalizados (JSONB).
- Ve todos los pagos, órdenes y evaluaciones.

### Teacher (Profesor)
1. Inicia sesión → redirigido al panel docente.
2. Ve sus talleres asignados: `GET /talleres/?asignados=true`
3. Ve niños inscritos en sus talleres: `GET /ninos/?taller_id=X`
4. Crea evaluaciones de niños verificados: `POST /evaluaciones/`
5. Genera recomendaciones IA: `POST /ia/recomendaciones/generar`
6. Descarga PDF de niños de su taller: `GET /reportes/taller/:id/ninos`

### Secretary (Secretaría)
1. Gestiona inscripciones y órdenes.
2. Revisa DNI pendientes: `GET /ninos/?dni_pendiente=true`
3. Verifica DNI: `PATCH /ninos/:id/dni`
4. Lee y responde mensajes de contacto: `PATCH /contacto/:id`
5. Genera reportes de pagos e inscripciones.

### Parent (Padre/Madre)
1. Se registra → verifica email → inicia sesión.
2. Registra hijo (máx. 6 años): `POST /ninos/`
3. Sube DNI del hijo: `POST /ninos/:id/dni`
4. Explora talleres: `GET /talleres/`
5. Crea orden: `POST /ordenes/`
6. Paga: `POST /ordenes/:id/pago` → MercadoPago
7. Verifica pago: `POST /pagos/verificar`
8. Ve evaluaciones de sus hijos: `GET /evaluaciones/?nino_id=X`
9. Ve recomendaciones IA: `GET /ia/recomendaciones/nino/:id`
10. Descarga PDF: `GET /reportes/nino/:id?tipo=evaluaciones`

---

## 🗓️ APScheduler — Jobs automáticos

| Job | Frecuencia | Acción |
|-----|-----------|--------|
| Limpieza token_blacklist | Cada 60 min | `DELETE FROM token_blacklist WHERE expires_at < NOW()` |
| Auto-delete niños pending | Cada 15 min | Elimina niños con `payment_status='pending'` y `created_at < NOW()-2h` |
| Limpieza sesiones chat IA | Cada 30 min | Elimina sesiones con `created_at < NOW()-2h` (cascade mensajes) |
| Revisión inactividad | Cada 10 min | Audita usuarios inactivos >40 min |

---

## 🚀 Producción (Render / Railway)

```bash
# Comando de inicio en Render:
gunicorn -w 2 -b 0.0.0.0:$PORT "run:app"

# Variables de entorno en Render:
FLASK_ENV=production
DATABASE_URL=postgresql://...   # Supabase connection string
# ... (resto de variables del .env.example)
```

**Checklist producción:**
- [ ] Cambiar `MP_ACCESS_TOKEN` de `TEST-` a `APP_USR-` (MercadoPago)
- [ ] Cambiar contraseña del admin por defecto
- [ ] Configurar `SUPABASE_SERVICE_KEY` (no la anon key)
- [ ] Generar `FERNET_KEY` con el comando del .env.example
- [ ] Configurar `JWT_SECRET_KEY` con al menos 32 bytes aleatorios
- [ ] Verificar que el bucket `dni-documents` está creado como privado en Supabase

---

## 🧪 Tests

```bash
# Instalar dependencias de test
pip install pytest pytest-flask

# Ejecutar tests
pytest tests/ -v
```

---

## 📎 Notas importantes

- **CORS**: Acepta cualquier origen (`*`). Configura `FRONTEND_URL` en `.env` para restricción futura.
- **Sin webhook MP**: La confirmación de pago es activa vía `POST /pagos/verificar`.
- **Datos médicos**: `medical_info` y `allergies` están cifrados con AES-256 (Fernet). La clave `FERNET_KEY` debe mantenerse segura y nunca perderse.
- **Texto MAYÚSCULAS**: Todo texto (nombres, títulos, horarios) se almacena en mayúsculas excepto los emails.
- **Edad máxima**: 6 años (72 meses) para registrar niños.
- **DNI**: Almacenado en Supabase Storage (bucket privado). El backend usa la `service_role` key.
- **Imágenes**: Talleres y fotos de niños en Cloudinary (máx. 5MB, JPEG/PNG/WEBP).
