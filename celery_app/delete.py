import os
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

index_name = "ptt"
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(index_name)

index.delete(deleteAll=True)
print(f"成功刪除索引 {index_name} 的所有資料")