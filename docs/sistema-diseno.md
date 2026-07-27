# Sistema de Diseño Visual — Dashboard Institucional Simulacros AGS

Este documento define las especificaciones del nuevo sistema de diseño visual para **Simulacros AGS**, transformando el estilo juvenil basado en emojis hacia una experiencia **profesional, elegante, seria e institucional** orientada a directivos, docentes y coordinadores académicos.

---

## 🎨 1. Paleta de Colores Institucional

La paleta se deriva directamente de la identidad cromática del logo del colegio ([Logo.png](file:///home/santiago/Desktop/simulacros-ags/Logo.png)) y de la base estructural azul marino de la plataforma.

### 🔷 Colores Base e Identidad (Brand & Canvas)
| Rol | Nombre | Código Hex | Aplicación |
| :--- | :--- | :---: | :--- |
| **Acento Primario** | Cyan Saucará | `#21B7D2` | Extraído directamente de `Logo.png`. Botones primarios, indicadores de valor, foco activo, enlaces institucionales. |
| **Fondo Sidebar / Hero** | Obsidian Navy | `#0D1B2A` | Fondo principal del menú lateral de navegación y encabezados de alta jerarquía. |
| **Superficie Contenedores** | Deep Sapphire | `#1B263B` | Tarjetas del sidebar, tarjetas métricas oscuras, headers desplegables. |
| **Acento Secundario** | Royal Blue | `#3B82F6` | Gradientes secundarios, elementos interactivos seleccionados, íconos informativos. |
| **Fondo Principal Canvas** | Slate Light | `#F8FAFC` | Fondo general de las páginas de contenido (modo claro institucional). |
| **Superficie Tarjetas** | Pure White | `#FFFFFF` | Fondo de contenedores, tarjetas de datos, métricas y tablas. |
| **Texto Principal** | Charcoal Slate | `#0F172A` | Encabezados, títulos de gráficos, texto de tablas (máximo contraste). |
| **Texto Secundario** | Muted Slate | `#64748B` | Labels, subtítulos, captions y metadatos secundarios. |

### 🚦 Colores Semánticos Adapta-ICFES (Estados y Rendimiento)
| Estado | Nombre | Código Hex | Criterio ICFES / Aplicación |
| :--- | :--- | :---: | :--- |
| **Sobresaliente** | Emerald Excellence | `#10B981` | Puntajes \(\ge 350\) / Tendencias positivas (+). |
| **Satisfactorio** | Sky Blue | `#0EA5E9` | Puntajes \(300 - 349\) / Metas alcanzadas. |
| **Medio** | Amber Warning | `#F59E0B` | Puntajes \(250 - 299\) / Áreas en observación. |
| **Crítico / Bajo** | Rose Crimson | `#EF4444` | Puntajes \(< 250\) / Tendencias negativas (-). |
| **Informativo** | Indigo Slate | `#6366F1` | Notificaciones y llamados de atención institucionales. |

---

## 🔤 2. Tipografía Deliberada

Se establece una pareja tipográfica moderna, profesional y optimizada para la visualización de datos académicos masivos.

```css
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');
```

1. **Tipografía de Display, Títulos y Métricas:** **`Plus Jakarta Sans`**
   - **Justificación:** Una tipografía sans-serif geométrica con carácter institucional, excelente peso en negritas (`600`, `700`, `800`) y estructura limpia. Otorga autoridad visual a los encabezados y números de puntaje sin sentirse rígida ni informal.

2. **Tipografía de Cuerpo, Tablas y Formularios:** **`Inter`** con números tabulares (`font-variant-numeric: tabular-nums lining-nums;`)
   - **Justificación:** Extremadamente legible en densidades altas de datos. La propiedad de **números tabulares** garantiza que los decimales y cifras de puntaje (ej: `350.50` vs `280.10`) se alineen perfectamente en columnas verticales, facilitando la lectura rápida para docentes y rectores.

---

## 📐 3. Escala de Espaciado y Radios de Borde

Se eliminan las medidas arbitrarias en favor de una escala de 8px estandarizada:

### Espaciado (Padding / Margin / Gap)
- `space-xs`: `4px` (Chips, badges internos)
- `space-sm`: `8px` (Espacio entre ícono y texto, padding de botones pequeños)
- `space-md`: `12px` (Padding interno de celdas de tabla, brechas compactas)
- `space-lg`: `16px` (Padding estándar de tarjetas y contenedores)
- `space-xl`: `24px` (Distancia entre secciones principales)
- `space-2xl`: `32px` (Separación de bloques estructurales)

### Radios de Borde (Border Radius)
- `radius-sm`: `4px` (Badges de estado, tags)
- `radius-md`: `8px` (Botones, inputs, selectores, celdas resaltadas)
- `radius-lg`: `12px` (Tarjetas de métricas, contenedores de gráficos, ventanas)
- `radius-xl`: `16px` (Contenedores del sidebar, tarjetas hero)

---

## ☀️ 4. Elevación y Sombras (Depth System)

- **Elevación Nivel 0 (Flat):** Sin sombra, borde sutil `1px solid #E2E8F0`. Usado en tablas e insumos.
- **Elevación Nivel 1 (Tarjetas en reposo):** `box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08), 0 1px 2px rgba(15, 23, 42, 0.04);`
- **Elevación Nivel 2 (Hover interactivo):** `box-shadow: 0 10px 15px -3px rgba(15, 23, 42, 0.1), 0 4px 6px -2px rgba(15, 23, 42, 0.05);`
- **Elevación Nivel 3 (Modales y Popovers):** `box-shadow: 0 20px 25px -5px rgba(15, 23, 42, 0.15), 0 10px 10px -5px rgba(15, 23, 42, 0.04);`

---

## ⚡ 5. Sistema de Movimiento (Transiciones CSS)

Streamlit regenera el DOM en cada interacción. Por tanto, las animaciones deben ser **CSS puras, sutiles y ultrarrápidas**:

- **Duración estándar:** `180ms`
- **Easing:** `cubic-bezier(0.16, 1, 0.3, 1)` (ease-out suavizado)
- **Casos de aplicación:**
  1. Hover en tarjetas métricas y botones (`transform: translateY(-2px);`).
  2. Transición de color en botones e íconos.
  3. Despliegue de menús selectbox y acordeones.
- **Regla:** Quedan prohibidas animaciones de bucle continuo, rotaciones pesadas o JS libraries (GSAP / Framer Motion).

---

## 🎨 6. Sistema de Íconos: Bootstrap Icons (CDN)

Se adopta **Bootstrap Icons v1.11.3** mediante CDN oficial:

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">
```

### Ventajas Técnicas e Institucionales:
1. **Integración Nativa:** El proyecto ya importa Bootstrap 5 en `styles.py`.
2. **Cero Dependencias de Python:** No requiere instalar ni compilar librerías adicionales en `requirements.txt`.
3. **Renderizado Vectorial Perfecto:** Sustituye los 208 emojis informales por íconos vectoriales crisp de categoría ejecutiva (`<i class="bi bi-award-fill"></i>`, `<i class="bi bi-bar-chart-line-fill"></i>`, `<i class="bi bi-person-badge"></i>`).

---

## 💎 7. Elemento de Firma Visual (Visual Signature)

**Firma:** **"Card Metric Ribbon + Cyan Accent Indicator"**

Cada tarjeta de métrica principal incorporará:
- Un **Borde de Acento Institucional** de 4px a la izquierda con el cian oficial `#21B7D2` (o el color semántico del estado).
- Un badge circular sutil en la esquina superior con el ícono de área vectorial en tono semántico.
- El valor numérico formateado en **`Plus Jakarta Sans`** con font-weight `800` y `tabular-nums`.
- Un micro-indicador de referencia sobre el puntaje máximo ICFES (ej: `Score / 500 pts`).

---

## 🔍 8. Autocrítica y Control de Calidad

- **Descarte de cliché IA #1 (Fondo crema / terracota):** Rechazado por carecer de jerarquía técnica. Se mantiene la paleta limpia azul marino y cian de `Logo.png`.
- **Descarte de cliché IA #2 (Modo neón / cyberpunk):** Rechazado por ser inapropiado para un entorno rectoral y directivo.
- **Descarte de cliché IA #3 (Layout plano sin bordes ni radios):** Rechazado por restar profundidad. Se aplican radios moderados de 8px-12px que lucen ejecutivos y modernos.
