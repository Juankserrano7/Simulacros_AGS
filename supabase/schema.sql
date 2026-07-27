-- Esquema SQL para la migración de Simulacros AGS a Supabase (PostgreSQL)

-- 1. Promociones (Cohortes de graduación por año)
CREATE TABLE IF NOT EXISTS promociones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre TEXT NOT NULL,
    anio_graduacion INTEGER NOT NULL,
    activa BOOLEAN NOT NULL DEFAULT true,
    creado_en TIMESTAMPTZ DEFAULT now()
);

-- 2. Usuarios del Sistema (EXCLUSIVAMENTE Docentes y Administradores - Los estudiantes NO tienen cuenta ni acceso)
CREATE TABLE IF NOT EXISTS usuarios (
    email TEXT PRIMARY KEY,
    salt TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT true,
    rol TEXT NOT NULL DEFAULT 'docente' CHECK (rol IN ('admin', 'docente')),
    ultima_actualizacion TIMESTAMPTZ DEFAULT now()
);

-- 3. Acceso de Docentes a Promociones (Asignación de qué promociones puede consultar/gestionar cada docente)
CREATE TABLE IF NOT EXISTS usuario_promocion_acceso (
    usuario_email TEXT NOT NULL REFERENCES usuarios(email) ON DELETE CASCADE ON UPDATE CASCADE,
    promocion_id UUID NOT NULL REFERENCES promociones(id) ON DELETE CASCADE,
    PRIMARY KEY (usuario_email, promocion_id)
);

-- 4. Estudiantes (Registros de estudiantes evaluados - Entidades de datos SIN credenciales ni acceso al sistema)
CREATE TABLE IF NOT EXISTS estudiantes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre TEXT NOT NULL,
    grado TEXT,
    promocion_id UUID NOT NULL REFERENCES promociones(id) ON DELETE CASCADE,
    es_inclusion BOOLEAN NOT NULL DEFAULT false,
    creado_en TIMESTAMPTZ DEFAULT now(),
    UNIQUE (nombre, promocion_id)
);

-- 5. Simulacros
CREATE TABLE IF NOT EXISTS simulacros (
    id TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    promocion_id UUID NOT NULL REFERENCES promociones(id) ON DELETE CASCADE,
    origen TEXT DEFAULT 'upload',
    estado TEXT DEFAULT 'ready',
    creado_por TEXT, -- Email del docente/admin que creó o cargó el simulacro
    creado_en TIMESTAMPTZ DEFAULT now(),
    insights JSONB DEFAULT '{}'::jsonb
);

-- 6. Resultados de Simulacros por Estudiante
CREATE TABLE IF NOT EXISTS resultados_simulacro (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulacro_id TEXT NOT NULL REFERENCES simulacros(id) ON DELETE CASCADE,
    estudiante_id UUID NOT NULL REFERENCES estudiantes(id) ON DELETE CASCADE,
    lectura_critica NUMERIC(5,2),
    matematicas NUMERIC(5,2),
    sociales_ciudadanas NUMERIC(5,2),
    ciencias_naturales NUMERIC(5,2),
    ingles NUMERIC(5,2),
    promedio_simple NUMERIC(5,2),
    promedio_ponderado NUMERIC(5,2),
    desviacion_estandar NUMERIC(5,2),
    UNIQUE (simulacro_id, estudiante_id)
);

-- 7. Resultados Oficiales ICFES Real
CREATE TABLE IF NOT EXISTS resultados_icfes_real (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    estudiante_id UUID NOT NULL REFERENCES estudiantes(id) ON DELETE CASCADE,
    promocion_id UUID NOT NULL REFERENCES promociones(id) ON DELETE CASCADE,
    anio_presentacion INTEGER NOT NULL,
    puntaje_global NUMERIC(5,2),
    lectura_critica NUMERIC(5,2),
    matematicas NUMERIC(5,2),
    sociales_ciudadanas NUMERIC(5,2),
    ciencias_naturales NUMERIC(5,2),
    ingles NUMERIC(5,2),
    UNIQUE (estudiante_id, anio_presentacion)
);

-- 8. Registro Centralizado de Auditoría de Cambios
CREATE TABLE IF NOT EXISTS auditoria_cambios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_email TEXT NOT NULL,
    tipo_accion TEXT NOT NULL,
    tabla_afectada TEXT NOT NULL,
    registro_id TEXT,
    detalles JSONB DEFAULT '{}'::jsonb,
    creado_en TIMESTAMPTZ DEFAULT now()
);

-- Activar Row Level Security (RLS) en todas las tablas
ALTER TABLE promociones ENABLE ROW LEVEL SECURITY;
ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE usuario_promocion_acceso ENABLE ROW LEVEL SECURITY;
ALTER TABLE estudiantes ENABLE ROW LEVEL SECURITY;
ALTER TABLE simulacros ENABLE ROW LEVEL SECURITY;
ALTER TABLE resultados_simulacro ENABLE ROW LEVEL SECURITY;
ALTER TABLE resultados_icfes_real ENABLE ROW LEVEL SECURITY;
ALTER TABLE auditoria_cambios ENABLE ROW LEVEL SECURITY;

-- 9. Índices en Claves Foráneas (Optimización de JOINs y CASCADE según Supabase Agent Skills)
CREATE INDEX IF NOT EXISTS idx_estudiantes_promocion ON estudiantes(promocion_id);
CREATE INDEX IF NOT EXISTS idx_simulacros_promocion ON simulacros(promocion_id);
CREATE INDEX IF NOT EXISTS idx_resultados_simulacro_estudiante ON resultados_simulacro(estudiante_id);
CREATE INDEX IF NOT EXISTS idx_resultados_simulacro_simulacro ON resultados_simulacro(simulacro_id);
CREATE INDEX IF NOT EXISTS idx_resultados_icfes_real_estudiante ON resultados_icfes_real(estudiante_id);
CREATE INDEX IF NOT EXISTS idx_resultados_icfes_real_promocion ON resultados_icfes_real(promocion_id);
CREATE INDEX IF NOT EXISTS idx_usuario_promocion_acceso_promocion ON usuario_promocion_acceso(promocion_id);


