#!/usr/bin/env python3
"""简单连接测试"""
import asyncio
import httpx

async def test():
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get('http://localhost:8000/state/test')
            print(f"Status: {response.status_code}")
            print(f"Text: {response.text[:300]}")
        except Exception as e:
            print(f"Error: {type(e).__name__}: {e}")

asyncio.run(test())

