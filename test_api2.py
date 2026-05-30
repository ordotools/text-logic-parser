import asyncio
import httpx
import json

text_full = """
There are exactly 4 classical syllogisms in this text, 2 of which are valid and 2 of which are invalid.

Academic philosophers often spend their careers analyzing historical arguments, which frequently leads to intense departmental debates. All logicians are meticulous thinkers, and some meticulous thinkers are professors; therefore, some logicians are professors. This classic puzzle often trips up undergraduates, who find it incredibly frustrating to untangle during exams.

Furthermore, no politicians are entirely transparent. Since all transparent speakers are trustworthy leaders, it follows that no politicians are trustworthy leaders. When a student successfully identifies this pattern, it proves they understand formal deduction. However, most students prefer studying ethics because they find the material more relatable to daily life.

Consider another case: all reptiles are cold-blooded creatures, and all iguanas are reptiles, so all iguanas are cold-blooded creatures. A professor might present this example to a student while he is grading essays late at night. Finally, all birds can fly, and some insects can fly, which means some birds are insects.
"""

async def test():
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "http://localhost:8080/api/analyze",
            json={"text": text_full, "version": "v2"}
        )
        for line in resp.iter_lines():
            if line.startswith("data:"):
                data = json.loads(line[5:])
                if data.get("event") == "chunk_result":
                    for arg in data.get("arguments", []):
                        syl = arg.get("reconstructed_syllogism")
                        if syl:
                            print("SYLLOGISM EXTRACTED:")
                            print(f"  Minor: {arg.get('minor_term')}")
                            print(f"  Major: {arg.get('major_term')}")
                            print(f"  Middle: {arg.get('middle_term')}")

asyncio.run(test())
