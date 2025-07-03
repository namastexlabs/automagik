from automagik.tools.flashed.provider import FlashedProvider
import asyncio, pprint
import logging

logging.basicConfig(level=logging.INFO)

async def run():
    async with FlashedProvider() as p:
        print("\n1. Testing get_user_by_email:")
        try:
            data = await p.get_user_by_email("cezar@namastex.ai")
            print("✅ Result:")
            pprint.pprint(data)
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        print("\n2. Testing search_users:")
        try:
            search_result = await p.search_users(email="cezar@namastex.ai")
            print("✅ Search result:")
            pprint.pprint(search_result)
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            
        print("\n3. Testing with phone number:")
        try:
            phone_result = await p.search_users(phone="5551997285829")
            print("✅ Phone search result:")
            pprint.pprint(phone_result)
        except Exception as e:
            print(f"❌ Error: {str(e)}")

asyncio.run(run())