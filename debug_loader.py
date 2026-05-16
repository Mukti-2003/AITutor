import os
from langchain_community.document_loaders import PyPDFDirectoryLoader

DATA_PATH = os.path.join("uploaded_data", "files")
print(f"Checking DATA_PATH: {DATA_PATH}")
print(f"Absolute path: {os.path.abspath(DATA_PATH)}")
print(f"Directory exists: {os.path.exists(DATA_PATH)}")
print(f"Contents: {os.listdir(DATA_PATH)}")

from langchain_text_splitters import RecursiveCharacterTextSplitter

loader = PyPDFDirectoryLoader(DATA_PATH)
docs = loader.load()
print(f"Loaded {len(docs)} documents")

splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=80,
    length_function=len,
)
chunks = splitter.split_documents(docs)
print(f"Created {len(chunks)} chunks")

if len(docs) > 0:
    print(f"First doc page content length: {len(docs[0].page_content)}")
    print(f"First 100 chars: '{docs[0].page_content[:100]}'")
