# Project Guidelines

Estas instrucciones aplican únicamente a tareas de **code review** en este repositorio (GitHub Copilot SDK para Python).

## Code Review

Al revisar código, evalúa y comenta sobre los siguientes aspectos:

### Corrección y Lógica
- Escribe la review en catalan
- Verifica que la lógica sea correcta y que se manejen los casos límite (valores nulos, listas vacías, entradas inesperadas).
- Detecta condiciones de carrera o problemas de concurrencia en el código `async/await`.
- Asegura que las corutinas se esperen (`await`) correctamente y que no haya tareas huérfanas.

### Estilo y Convenciones de Python
- Confirma el cumplimiento de PEP 8 y el uso de nombres descriptivos.
- Exige type hints completos en firmas de funciones y métodos públicos.
- Verifica que existan docstrings en módulos, clases y funciones públicas.
- Señala el uso de imports no utilizados o desordenados.

### Seguridad
- Identifica vulnerabilidades del OWASP Top 10 (inyección, deserialización insegura, exposición de datos sensibles).
- Comprueba que no se registren ni expongan secretos, tokens o credenciales.
- Revisa el manejo seguro de entrada/salida con procesos externos (CLI, subprocess, JSON-RPC).
- Valida que la lectura de JSON y datos externos se haga de forma segura.

### Manejo de Errores
- Verifica que las excepciones se capturen de forma específica (evitar `except:` genérico).
- Asegura que los errores se propaguen o registren con contexto suficiente.
- Confirma que los recursos (conexiones, ficheros, procesos) se liberen correctamente.

### Mantenibilidad
- Señala duplicación de código y sugiere reutilización solo cuando aporte valor.
- Detecta funciones demasiado largas o con responsabilidades múltiples.
- Evita sobre-ingeniería: comenta si se añade complejidad innecesaria.

### Pruebas
- Verifica que los cambios incluyan o actualicen pruebas relevantes.
- Confirma que las pruebas cubran los casos de éxito y de error.

## Formato de los Comentarios de Review
- Sé conciso y específico; referencia la línea o el bloque afectado.
- Clasifica cada comentario como **bloqueante**, **sugerencia** o **menor**.
- Propón siempre una solución concreta, no solo el problema.
