import asyncio
from copilot import CopilotClient

async def main():
    # Create and start client
    client = CopilotClient()
    await client.start()

    # Create a session
    session = await client.create_session({"model": "GPT-4.1"})

    # Wait for response using session.idle event
    done = asyncio.Event()

    def on_event(event):
        if event.type.value == "assistant.message":
            print(event.data.content)
        elif event.type.value in {"session.idle", "session.error"}:
            done.set()

    session.on(on_event)

    try:
        # Send a message and wait for completion
        await session.send({"prompt": "What is 2+2?"})
        await asyncio.wait_for(done.wait(), timeout=30)
    except asyncio.TimeoutError:
        print("Timeout waiting for session idle.")
    finally:
        # Clean up
        await session.destroy()
        await client.stop()

asyncio.run(main())