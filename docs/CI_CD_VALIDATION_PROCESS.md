# Proceso de Validación Automática de Agentes

## Visión General

```mermaid
flowchart LR
    subgraph Developer["👨‍💻 Developer"]
        A[Crear/Modificar Agente]
    end
    
    subgraph GitHub["🐙 GitHub"]
        B[Push a Branch]
        C[Crear PR]
        D[GitHub Action]
    end
    
    subgraph Validation["🔍 Validación"]
        E[agent_validator.py]
        F{Quality Gate}
    end
    
    subgraph Result["📊 Resultado"]
        G[✅ PR Aprobada]
        H[❌ PR Bloqueada]
    end
    
    A --> B --> C --> D --> E --> F
    F -->|score >= threshold| G
    F -->|score < threshold| H
    
    style A fill:#2196F3,stroke:#1565C0,color:#fff
    style D fill:#9C27B0,stroke:#6A1B9A,color:#fff
    style E fill:#FF9800,stroke:#E65100,color:#fff
    style F fill:#FFEB3B,stroke:#F9A825,color:#000
    style G fill:#4CAF50,stroke:#2E7D32,color:#fff
    style H fill:#F44336,stroke:#C62828,color:#fff
```

---

## Flujo del Proceso

### 1. Desarrollo del Agente

El desarrollador crea o modifica un archivo de agente en la carpeta `agents/`:

```
agents/
├── python_expert.md      ← Agente existente
├── sql_expert.md         ← Nuevo agente (PR)
└── devops_helper.md      ← Nuevo agente (PR)
```

**Requisitos del archivo de agente:**
- Nombre descriptivo (`.md`)
- Sección de instrucciones del sistema
- Mínimo 3 casos de prueba
- Campo `expected_behavior` en cada test (para LLM-as-judge)

---

### 2. Creación de Pull Request

```mermaid
flowchart TD
    A[Developer hace push] --> B[Crea PR hacia main]
    B --> C[GitHub detecta cambios en agents/]
    C --> D{¿Cambios en agents/*.md?}
    D -->|Sí| E[Trigger: Validate Agent Action]
    D -->|No| F[Workflow estándar]
    
    style A fill:#2196F3,stroke:#1565C0,color:#fff
    style D fill:#FFEB3B,stroke:#F9A825,color:#000
    style E fill:#9C27B0,stroke:#6A1B9A,color:#fff
```

**Triggers de la Action:**
- Push a cualquier branch con cambios en `agents/*.md`
- PR hacia `main` con cambios en `agents/*.md`
- Manual dispatch para re-validación

---

### 3. Ejecución del Validador

```mermaid
flowchart TD
    subgraph Setup["⚙️ Setup"]
        A[Checkout código]
        B[Configurar Python 3.11+]
        C[Instalar dependencias]
        D[Configurar Copilot SDK]
    end
    
    subgraph Detection["🔍 Detección"]
        E[Detectar agentes modificados]
        F[Filtrar solo archivos .md en agents/]
    end
    
    subgraph Validation["🧪 Validación"]
        G[Ejecutar agent_validator.py]
        H[Evaluar cada caso de prueba]
        I[LLM-as-judge análisis]
        J[Calcular score final]
    end
    
    subgraph Output["📊 Output"]
        K[Generar reporte JSON]
        L[Generar reporte Markdown]
        M[Publicar como PR Comment]
    end
    
    A --> B --> C --> D --> E --> F --> G --> H --> I --> J --> K --> L --> M
    
    style A fill:#2196F3,stroke:#1565C0,color:#fff
    style G fill:#FF9800,stroke:#E65100,color:#fff
    style I fill:#9C27B0,stroke:#6A1B9A,color:#fff
    style J fill:#FFEB3B,stroke:#F9A825,color:#000
```

---

### 4. Quality Gate

```mermaid
flowchart TD
    A[Score Final Calculado] --> B{Score >= Threshold?}
    
    B -->|score >= 70| C[✅ Quality Gate PASSED]
    B -->|score < 70| D[❌ Quality Gate FAILED]
    
    C --> E[PR Check: Success]
    C --> F[Comentario: Reporte positivo]
    C --> G[Merge habilitado]
    
    D --> H[PR Check: Failure]
    D --> I[Comentario: Áreas de mejora]
    D --> J[Merge bloqueado]
    
    style A fill:#2196F3,stroke:#1565C0,color:#fff
    style B fill:#FFEB3B,stroke:#F9A825,color:#000
    style C fill:#4CAF50,stroke:#2E7D32,color:#fff
    style D fill:#F44336,stroke:#C62828,color:#fff
    style E fill:#4CAF50,stroke:#2E7D32,color:#fff
    style H fill:#F44336,stroke:#C62828,color:#fff
```

**Umbrales configurables:**

| Nivel | Score Mínimo | Uso Recomendado |
|-------|--------------|-----------------|
| 🔴 Estricto | 85+ | Producción crítica |
| 🟡 Estándar | 70+ | Desarrollo normal |
| 🟢 Permisivo | 50+ | Experimentos/POC |

---

### 5. Componentes del Score

El score final se calcula con la fórmula ponderada:

```
Score = (Success × 0.40) + (LLM × 0.25) + (Latency × 0.15) + (Security × 0.20)
```

```mermaid
pie title Distribución del Score
    "Success Rate (40%)" : 40
    "LLM Evaluation (25%)" : 25
    "Latency (15%)" : 15
    "Security (20%)" : 20
```

**Criterios de cada componente:**

| Componente | Qué evalúa | Cómo se mide |
|------------|------------|--------------|
| **Success Rate** | Tests pasados vs totales | `passed / total × 100` |
| **LLM Evaluation** | Calidad semántica de respuestas | Promedio de scores LLM (1-10) |
| **Latency** | Tiempo de respuesta | Penalización si > 5 segundos |
| **Security** | Ausencia de patrones peligrosos | Detección de código inseguro |

---

### 6. Reporte en PR

El validador genera un comentario automático en la PR:

```
## 🤖 Agent Validation Report

### 📊 Resumen
| Métrica | Valor |
|---------|-------|
| **Score Final** | 82.5 / 100 |
| **Quality Gate** | ✅ PASSED |
| **Tests Pasados** | 4/5 (80%) |
| **LLM Score** | 8.2/10 |

### 📋 Resultados por Test

| Test | Estado | LLM | Latencia |
|------|--------|-----|----------|
| fibonacci_basico | ✅ | 9.0 | 1.2s |
| manejo_errores | ✅ | 8.5 | 0.9s |
| optimizacion | ❌ | 6.0 | 2.1s |
| documentacion | ✅ | 8.5 | 1.5s |
| edge_cases | ✅ | 8.0 | 1.1s |

### 💡 Recomendaciones
- Test `optimizacion`: Mejorar sugerencias de complejidad algorítmica
```

---

### 7. Branch Protection Rules

Configuración recomendada para `main`:

```mermaid
flowchart TD
    A[PR hacia main] --> B{Checks requeridos}
    
    B --> C[agent-validation ✓]
    B --> D[code-review ✓]
    B --> E[tests ✓]
    
    C --> F{¿Todos pasaron?}
    D --> F
    E --> F
    
    F -->|Sí| G[🔓 Merge habilitado]
    F -->|No| H[🔒 Merge bloqueado]
    
    style A fill:#2196F3,stroke:#1565C0,color:#fff
    style C fill:#9C27B0,stroke:#6A1B9A,color:#fff
    style F fill:#FFEB3B,stroke:#F9A825,color:#000
    style G fill:#4CAF50,stroke:#2E7D32,color:#fff
    style H fill:#F44336,stroke:#C62828,color:#fff
```

**Configuración en GitHub:**
1. Settings → Branches → Add rule
2. Branch name pattern: `main`
3. ✅ Require status checks to pass
4. ✅ Require branches to be up to date
5. Status checks: `agent-validation`

---

## Matriz de Decisiones

### Escenarios de Validación

| Escenario | Acción | Resultado |
|-----------|--------|-----------|
| Nuevo agente, score >= 70 | Aprobar | ✅ Merge habilitado |
| Nuevo agente, score < 70 | Bloquear | ❌ Requiere mejoras |
| Modificación agente, sin regresión | Aprobar | ✅ Merge habilitado |
| Modificación agente, con regresión | Bloquear | ❌ Revisar cambios |
| Solo cambios en docs/ | Skip validación | ✅ Merge directo |
| Cambios mixtos (agents + código) | Validar agentes | Depende del score |

### Gestión de Fallos

```mermaid
flowchart TD
    A[Quality Gate FAILED] --> B{Tipo de fallo}
    
    B -->|Score bajo| C[Mejorar casos de prueba]
    B -->|LLM score bajo| D[Refinar instrucciones del agente]
    B -->|Timeout| E[Simplificar prompts]
    B -->|Security issues| F[Eliminar patrones peligrosos]
    
    C --> G[Push nuevos cambios]
    D --> G
    E --> G
    F --> G
    
    G --> H[Re-ejecutar validación]
    H --> I{¿Pasa ahora?}
    
    I -->|Sí| J[✅ Continuar con PR]
    I -->|No| K[🔄 Iterar]
    
    style A fill:#F44336,stroke:#C62828,color:#fff
    style B fill:#FFEB3B,stroke:#F9A825,color:#000
    style J fill:#4CAF50,stroke:#2E7D32,color:#fff
```

---

## Variables de Entorno Requeridas

| Variable | Descripción | Dónde configurar |
|----------|-------------|------------------|
| `COPILOT_TOKEN` | Token de autenticación Copilot | GitHub Secrets |
| `QUALITY_THRESHOLD` | Score mínimo (default: 70) | Workflow variable |
| `ENABLE_LLM_JUDGE` | Activar evaluación LLM | Workflow variable |

---

## Siguientes Pasos

1. **Crear GitHub Action** (`agent-validation.yml`)
2. **Configurar secrets** en el repositorio
3. **Establecer branch protection** en `main`
4. **Probar con un agente de ejemplo**
5. **Documentar proceso para contribuidores**

---

## Referencias

- [AGENT_VALIDATOR_GUIDE.md](./AGENT_VALIDATOR_GUIDE.md) - Guía completa del validador
- [agent_validator.py](../agent_validator.py) - Script de validación
- [agents/python_expert.md](../agents/python_expert.md) - Ejemplo de agente válido
