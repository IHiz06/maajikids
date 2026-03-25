-- ============================================================
-- MaajiKids — Schema SQL para Supabase PostgreSQL
-- Ejecuta este script en el SQL Editor de Supabase
-- ANTES de arrancar el backend por primera vez.
-- Las tablas también se crean automáticamente con db.create_all(),
-- pero este script agrega índices, constraints y el bucket de Storage.
-- ============================================================

-- ── Extensiones ──────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Tabla: roles ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS roles (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(50)  UNIQUE NOT NULL,
    description TEXT,
    is_system   BOOLEAN      NOT NULL DEFAULT false,
    permissions JSONB        NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    created_by  INTEGER      REFERENCES users(id) ON DELETE SET NULL
);

-- ── Tabla: users ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id                   SERIAL PRIMARY KEY,
    email                VARCHAR(255) UNIQUE NOT NULL,
    password_hash        VARCHAR(255) NOT NULL,
    role_id              INTEGER      NOT NULL REFERENCES roles(id),
    first_name           VARCHAR(100) NOT NULL,
    last_name            VARCHAR(100) NOT NULL,
    phone                VARCHAR(20),
    is_active            BOOLEAN      NOT NULL DEFAULT true,
    email_verified       BOOLEAN      NOT NULL DEFAULT false,
    verification_code    VARCHAR(10),
    verification_expires TIMESTAMPTZ,
    last_activity        TIMESTAMPTZ,
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    last_login           TIMESTAMPTZ
);

-- ── Tabla: workshops ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS workshops (
    id               SERIAL PRIMARY KEY,
    title            VARCHAR(200)   NOT NULL,
    description      TEXT           NOT NULL,
    teacher_id       INTEGER        REFERENCES users(id) ON DELETE SET NULL,
    schedule         VARCHAR(200)   NOT NULL,
    age_min          INTEGER        NOT NULL CHECK (age_min >= 0),
    age_max          INTEGER        NOT NULL CHECK (age_max <= 72),
    max_capacity     INTEGER        NOT NULL CHECK (max_capacity > 0),
    current_enrolled INTEGER        NOT NULL DEFAULT 0 CHECK (current_enrolled >= 0),
    price            NUMERIC(10,2)  NOT NULL CHECK (price > 0),
    image_url        VARCHAR(500),
    is_active        BOOLEAN        NOT NULL DEFAULT true,
    created_at       TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_age_range CHECK (age_min < age_max)
);

-- ── Tabla: children ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS children (
    id                 SERIAL PRIMARY KEY,
    parent_id          INTEGER      NOT NULL REFERENCES users(id),
    full_name          VARCHAR(200) NOT NULL,
    date_of_birth      DATE         NOT NULL,
    gender             VARCHAR(10)  NOT NULL CHECK (gender IN ('M','F','OTRO')),
    photo_url          VARCHAR(500),
    medical_info       TEXT,
    allergies          TEXT,
    payment_status     VARCHAR(20)  NOT NULL DEFAULT 'none'
                                    CHECK (payment_status IN ('none','pending','verified')),
    dni_document_url   VARCHAR(500),
    dni_uploaded_by    VARCHAR(20)  CHECK (dni_uploaded_by IN ('parent','admin','secretary')),
    dni_verified       BOOLEAN      NOT NULL DEFAULT false,
    dni_pending_review BOOLEAN      NOT NULL DEFAULT false,
    is_active          BOOLEAN      NOT NULL DEFAULT true,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ── Tabla: emergency_contacts ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS emergency_contacts (
    id           SERIAL PRIMARY KEY,
    child_id     INTEGER      NOT NULL REFERENCES children(id) ON DELETE CASCADE,
    full_name    VARCHAR(200) NOT NULL,
    phone        VARCHAR(20)  NOT NULL,
    relationship VARCHAR(100) NOT NULL,
    is_primary   BOOLEAN      NOT NULL DEFAULT false,
    order_index  INTEGER      NOT NULL DEFAULT 1
);

-- ── Tabla: orders ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS orders (
    id               SERIAL PRIMARY KEY,
    parent_id        INTEGER       NOT NULL REFERENCES users(id),
    status           VARCHAR(20)   NOT NULL DEFAULT 'pending'
                                   CHECK (status IN ('pending','approved','rejected','cancelled')),
    total_amount     NUMERIC(10,2) NOT NULL,
    mp_preference_id VARCHAR(200),
    mp_payment_id    VARCHAR(200),
    created_at       TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    paid_at          TIMESTAMPTZ
);

-- ── Tabla: order_items ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS order_items (
    id          SERIAL PRIMARY KEY,
    order_id    INTEGER       NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    child_id    INTEGER       NOT NULL REFERENCES children(id),
    workshop_id INTEGER       NOT NULL REFERENCES workshops(id),
    unit_price  NUMERIC(10,2) NOT NULL,
    CONSTRAINT uq_order_item_child_workshop UNIQUE (child_id, workshop_id)
);

-- ── Tabla: enrollments ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS enrollments (
    id          SERIAL PRIMARY KEY,
    child_id    INTEGER     NOT NULL REFERENCES children(id),
    workshop_id INTEGER     NOT NULL REFERENCES workshops(id),
    order_id    INTEGER     NOT NULL REFERENCES orders(id),
    status      VARCHAR(20) NOT NULL DEFAULT 'active'
                            CHECK (status IN ('active','cancelled')),
    enrolled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_enrollment_child_workshop UNIQUE (child_id, workshop_id)
);

-- ── Tabla: evaluations ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS evaluations (
    id               SERIAL PRIMARY KEY,
    child_id         INTEGER      NOT NULL REFERENCES children(id),
    workshop_id      INTEGER      NOT NULL REFERENCES workshops(id),
    teacher_id       INTEGER      NOT NULL REFERENCES users(id),
    eval_date        DATE         NOT NULL,
    score_cognitive  NUMERIC(4,1) NOT NULL CHECK (score_cognitive BETWEEN 0 AND 10),
    score_motor      NUMERIC(4,1) NOT NULL CHECK (score_motor      BETWEEN 0 AND 10),
    score_language   NUMERIC(4,1) NOT NULL CHECK (score_language   BETWEEN 0 AND 10),
    score_social     NUMERIC(4,1) NOT NULL CHECK (score_social     BETWEEN 0 AND 10),
    observations     TEXT,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ── Tabla: ai_recommendations ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ai_recommendations (
    id                   SERIAL PRIMARY KEY,
    evaluation_id        INTEGER     NOT NULL REFERENCES evaluations(id),
    child_id             INTEGER     NOT NULL REFERENCES children(id),
    recommendations_text TEXT        NOT NULL,
    is_visible_to_parent BOOLEAN     NOT NULL DEFAULT true,
    generated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    model_used           VARCHAR(100) NOT NULL DEFAULT 'gemini-2.5-flash'
);

-- ── Tabla: contact_messages ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS contact_messages (
    id           SERIAL PRIMARY KEY,
    sender_name  VARCHAR(200) NOT NULL,
    sender_email VARCHAR(255) NOT NULL,
    subject      VARCHAR(300) NOT NULL,
    body         TEXT         NOT NULL,
    status       VARCHAR(20)  NOT NULL DEFAULT 'unread'
                              CHECK (status IN ('unread','read','replied')),
    reply_text   TEXT,
    replied_by   INTEGER      REFERENCES users(id) ON DELETE SET NULL,
    replied_at   TIMESTAMPTZ,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ── Tabla: token_blacklist ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS token_blacklist (
    id          SERIAL PRIMARY KEY,
    jti         VARCHAR(200) UNIQUE NOT NULL,
    token_type  VARCHAR(20)  NOT NULL,
    user_id     INTEGER      NOT NULL REFERENCES users(id),
    revoked_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    expires_at  TIMESTAMPTZ  NOT NULL
);

-- ── Tabla: chat_sesiones ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS chat_sesiones (
    id              SERIAL PRIMARY KEY,
    session_token   VARCHAR(200) UNIQUE NOT NULL,
    user_id         INTEGER      REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    last_message_at TIMESTAMPTZ
);

-- ── Tabla: chat_mensajes ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS chat_mensajes (
    id         SERIAL PRIMARY KEY,
    sesion_id  INTEGER     NOT NULL REFERENCES chat_sesiones(id) ON DELETE CASCADE,
    role       VARCHAR(20) NOT NULL CHECK (role IN ('user','assistant')),
    content    TEXT        NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Índices de rendimiento ────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_users_email          ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role_id        ON users(role_id);
CREATE INDEX IF NOT EXISTS idx_children_parent_id   ON children(parent_id);
CREATE INDEX IF NOT EXISTS idx_children_payment_status ON children(payment_status);
CREATE INDEX IF NOT EXISTS idx_children_dni_pending ON children(dni_pending_review) WHERE dni_pending_review = true;
CREATE INDEX IF NOT EXISTS idx_workshops_teacher_id ON workshops(teacher_id);
CREATE INDEX IF NOT EXISTS idx_workshops_is_active  ON workshops(is_active);
CREATE INDEX IF NOT EXISTS idx_orders_parent_id     ON orders(parent_id);
CREATE INDEX IF NOT EXISTS idx_orders_status        ON orders(status);
CREATE INDEX IF NOT EXISTS idx_order_items_child_ws ON order_items(child_id, workshop_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_child    ON enrollments(child_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_workshop ON enrollments(workshop_id);
CREATE INDEX IF NOT EXISTS idx_evaluations_child_id ON evaluations(child_id);
CREATE INDEX IF NOT EXISTS idx_evaluations_teacher  ON evaluations(teacher_id);
CREATE INDEX IF NOT EXISTS idx_token_blacklist_jti  ON token_blacklist(jti);
CREATE INDEX IF NOT EXISTS idx_token_blacklist_exp  ON token_blacklist(expires_at);
CREATE INDEX IF NOT EXISTS idx_chat_sesiones_user   ON chat_sesiones(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_sesiones_created ON chat_sesiones(created_at);
CREATE INDEX IF NOT EXISTS idx_chat_mensajes_sesion  ON chat_mensajes(sesion_id);
CREATE INDEX IF NOT EXISTS idx_contact_status        ON contact_messages(status);

-- ── Seed: Roles del sistema ───────────────────────────────────────────────────
INSERT INTO roles (name, description, is_system, permissions) VALUES
('admin', 'Administrador del sistema. Control total.', true,
 '{"workshops":{"read":true,"write":true,"delete":true},"children":{"read":true,"write":true,"delete":true},"evaluations":{"read":true,"write":true,"delete":true},"payments":{"read":true,"write":true,"delete":true},"users":{"read":true,"write":true,"delete":true},"reports":{"read":true},"contact":{"read":true,"write":true,"delete":true},"ai":{"read":true,"write":true},"roles":{"read":true,"write":true,"delete":true}}'),
('teacher', 'Especialista / Educadora del centro.', true,
 '{"workshops":{"read":true,"write":false,"delete":false},"children":{"read":true,"write":false,"delete":false},"evaluations":{"read":true,"write":true,"delete":false},"payments":{"read":false,"write":false,"delete":false},"users":{"read":false,"write":false,"delete":false},"reports":{"read":true},"contact":{"read":false,"write":false,"delete":false},"ai":{"read":true,"write":true}}'),
('secretary', 'Secretaría / Recepción.', true,
 '{"workshops":{"read":true,"write":false,"delete":false},"children":{"read":true,"write":true,"delete":false},"evaluations":{"read":false,"write":false,"delete":false},"payments":{"read":true,"write":false,"delete":false},"users":{"read":false,"write":false,"delete":false},"reports":{"read":true},"contact":{"read":true,"write":true,"delete":false},"ai":{"read":false,"write":false}}'),
('parent', 'Padre, madre o tutor.', true,
 '{"workshops":{"read":true,"write":false,"delete":false},"children":{"read":true,"write":true,"delete":false},"evaluations":{"read":true,"write":false,"delete":false},"payments":{"read":true,"write":true,"delete":false},"users":{"read":false,"write":false,"delete":false},"reports":{"read":true},"contact":{"read":false,"write":true,"delete":false},"ai":{"read":true,"write":true}}')
ON CONFLICT (name) DO NOTHING;

-- ── Supabase Storage: Crear bucket privado para DNI ───────────────────────────
-- Ejecutar en el SQL Editor de Supabase o desde el panel Storage:
INSERT INTO storage.buckets (id, name, public)
VALUES ('dni-documents', 'dni-documents', false)
ON CONFLICT (id) DO NOTHING;

-- Policy: solo service_role puede leer/escribir (el backend usa service_role key)
CREATE POLICY "Service role full access" ON storage.objects
  FOR ALL TO service_role
  USING (bucket_id = 'dni-documents')
  WITH CHECK (bucket_id = 'dni-documents');
