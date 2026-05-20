import asyncio
import os
import sys

# add parent directory to path so it can import llm
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm import generate_problem

async def main():
    try:
        data = await generate_problem("arrays", "easy")
        import json
        print(json.dumps(data, indent=2))
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
