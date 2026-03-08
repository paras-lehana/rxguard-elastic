The ideal Knowledge Base architecture decouples document state management from the vector index. Search engines (like Kendra or OpenSearch) are not databases; they are eventually consistent and lack native table-listing features. The best practice is to use S3 for storage, DynamoDB as the source-of-truth for listing/tracking, and Bedrock's native Data Source sync to manage the vector store.

Steps

AWS Console: Create an S3 bucket for document storage and a DynamoDB table (DocumentMetadata) with document_id as the partition key.

AWS Console: Recreate your Bedrock Knowledge Base. Instead of pushing to Kendra directly, attach the S3 bucket as a Data Source.

Replace ingest_document in bedrock_service.py. It should now upload the PDF to the S3 bucket, write a record to DynamoDB (status="ACTIVE"), and optionally trigger a Bedrock StartIngestionJob to sync the KB.

Replace list_documents in bedrock_service.py to perform a DynamoDB Scan or Query for active items. This natively provides exact counts and cursor-based pagination instantly, bypassing Kendra entirely.

Replace delete_document in bedrock_service.py. It should mark the DynamoDB record as status="DELETED" and delete the object from S3. The next Bedrock sync will naturally prune the vector store.

Clean up rag_search in bedrock_service.py. Bedrock will handle the RAG natively based solely on the synced S3 contents.

Verification

Upload a document via your API. Check DynamoDB (AWS Console) to ensure the metadata record exists. Check S3 to see the file. Finally, check the Bedrock Knowledge Base sync history to ensure it processed the new file. Call your list API to verify it reads perfectly from DynamoDB without querying the search index