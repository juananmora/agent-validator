import asyncio
from copilot import CopilotClient


async def main():
    client = CopilotClient({
        "cli_path": "copilot",  # Optional: path to CLI executable
        "cli_url": None,        # Optional: URL of existing server (e.g., "localhost:8080")
        "log_level": "info",    # Optional: log level (default: "info")
        "auto_start": True,     # Optional: auto-start server (default: True)
        "auto_restart": True,   # Optional: auto-restart on crash (default: True)
    })
    await client.start()

    session = await client.create_session({"model": "claude-sonnet-4.5"})

    done = asyncio.Event()

    def on_event(event):
        if event.type.value == "assistant.message" and event.data.content:
            print(event.data.content)
        else:
            print(f"Event: {event.type.value}")
        if event.type.value in {"session.idle", "session.error"}:
            done.set()

    session.on(on_event)

    try:
        await session.send({"prompt": "Hello!"})
        await asyncio.wait_for(done.wait(), timeout=30)
    except asyncio.TimeoutError:
        print("Timeout waiting for session idle.")
    finally:
        await session.destroy()
        await client.stop()


asyncio.run(main())