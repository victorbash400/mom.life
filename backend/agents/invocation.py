import asyncio


async def invoke(agent, prompt, timeout_seconds: int):
    try:
        async with asyncio.timeout(timeout_seconds):
            return await agent.invoke_async(prompt)
    except TimeoutError:
        agent.cancel()
        raise RuntimeError(f"The AI provider did not respond within {timeout_seconds} seconds.") from None
