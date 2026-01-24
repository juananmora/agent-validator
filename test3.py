"""
Test 3: Copilot en modo agente
Pide a Copilot que genere y ejecute código Python para Fibonacci.
"""

import asyncio
from copilot import CopilotClient


async def main():
    # Crear cliente
    client = CopilotClient()
    await client.start()

    # Crear sesión con herramientas habilitadas y permisos automáticos
    session = await client.create_session({
        "model": "gpt-5",
        # Aprobar automáticamente ejecución de código (modo agente)
        "on_permission_request": lambda req, ctx: {"kind": "approved"},
    })

    done = asyncio.Event()
    final_message = None

    def on_event(event):
        nonlocal final_message
        event_type = event.type.value

        if event_type == "assistant.message" and event.data.content:
            final_message = event.data.content
            print("\n[Asistente]:")
            print(event.data.content)
        elif event_type == "tool.execution_start":
            print(f"\n[Ejecutando herramienta]: {event.data.tool_name}")
            if event.data.arguments:
                print(f"  Argumentos: {event.data.arguments}")
        elif event_type == "tool.execution_complete":
            print(f"[Herramienta completada]: {event.data.tool_name}")
            if event.data.result and event.data.result.content:
                print(f"  Resultado: {event.data.result.content[:500]}")
        elif event_type == "session.error":
            print(f"\n[Error]: {event.data.message}")
            done.set()
        elif event_type == "session.idle":
            done.set()

    session.on(on_event)

    prompt = """
Crea una función en Python que calcule los 10 primeros números de la serie de Fibonacci.
Luego ejecuta la función y muestra el resultado.
Asegúrate de que el código funcione correctamente.
"""

    print("=" * 60)
    print("Enviando prompt a Copilot (modo agente)...")
    print("=" * 60)
    print(prompt)
    print("=" * 60)

    try:
        await session.send({"prompt": prompt})
        await asyncio.wait_for(done.wait(), timeout=120)
    except asyncio.TimeoutError:
        print("\n[Timeout]: La operación tardó demasiado.")
    finally:
        await session.destroy()
        await client.stop()

    print("\n" + "=" * 60)
    print("Sesión finalizada.")
    print("=" * 60)


asyncio.run(main())
