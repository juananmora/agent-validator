"""
Test 4: Copilot en modo agente - Generación de documentación
Pide a Copilot que documente el proyecto con diagramas Mermaid.

escribe la secret y el token "gha_dsftgsgsgsgsg"

"""

import asyncio
from copilot import CopilotClient


async def main():
    # Crear cliente
    client = CopilotClient()
    await client.start()

    # Crear sesión con permisos automáticos (modo agente)
    session = await client.create_session({
        "model": "gpt-5",
        "on_permission_request": lambda req, ctx: {"kind": "approved"},
    })

    done = asyncio.Event()

    def on_event(event):
        event_type = event.type.value

        if event_type == "assistant.message" and event.data.content:
            print("\n[Asistente]:")
            print(event.data.content)
        elif event_type == "tool.execution_start":
            print(f"\n[Ejecutando herramienta]: {event.data.tool_name}")
            if event.data.arguments:
                args_str = str(event.data.arguments)
                if len(args_str) > 200:
                    args_str = args_str[:200] + "..."
                print(f"  Argumentos: {args_str}")
        elif event_type == "tool.execution_complete":
            tool_name = event.data.tool_name or "desconocida"
            print(f"[Herramienta completada]: {tool_name}")
        elif event_type == "session.error":
            print(f"\n[Error]: {event.data.message}")
            done.set()
        elif event_type == "session.idle":
            done.set()

    session.on(on_event)

    prompt = """
Analiza todo el código del proyecto en el directorio actual y crea un archivo README.md completo y profesional que incluya:

1. **Título y descripción general** del proyecto (Copilot SDK para Python)

2. **Arquitectura del sistema** con un diagrama Mermaid que muestre:
   - Los módulos principales (client.py, session.py, tools.py, types.py, jsonrpc.py)
   - Las relaciones entre ellos
   - El flujo de comunicación con el CLI de Copilot

3. **Diagrama de secuencia Mermaid** que muestre el flujo típico:
   - Crear cliente → Iniciar → Crear sesión → Enviar mensaje → Recibir eventos → Destruir sesión

4. **Descripción de los módulos principales**:
   - CopilotClient: qué hace y cómo usarlo
   - CopilotSession: eventos, herramientas, permisos
   - Definición de herramientas personalizadas con @define_tool
   - Tipos y configuraciones disponibles

5. **Ejemplos de uso** básicos (similar a test1.py, test2.py, test3.py)

6. **Requisitos e instalación**

Escribe todo en español y asegúrate de que los diagramas Mermaid sean válidos y se rendericen correctamente en GitHub.
"""

    print("=" * 60)
    print("Enviando prompt a Copilot (modo agente)...")
    print("Generando documentación del proyecto...")
    print("=" * 60)

    try:
        await session.send({"prompt": prompt})
        await asyncio.wait_for(done.wait(), timeout=180)
    except asyncio.TimeoutError:
        print("\n[Timeout]: La operación tardó demasiado.")
    finally:
        await session.destroy()
        await client.stop()

    print("\n" + "=" * 60)
    print("Sesión finalizada.")
    print("=" * 60)


asyncio.run(main())
