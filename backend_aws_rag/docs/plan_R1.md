Plan: Quick Fix with Pagination and Soft Deletes
This approach modifies your existing direct-Kendra implementation. We will update the listing query to capture all PDFs, introduce pagination parameters to handle >10 items, and implement a metadata-based soft-deletion to immediately hide deleted outputs from search results.

Steps

Modify list_documents in bedrock_service.py to accept page_number and page_size arguments. Change the Kendra API call to use QueryText="*.pdf", and pass the pagination arguments into Kendra's PageNumber and PageSize fields.

Update the API route in documents.py to accept page (default 1) and size (default 10) as query parameters and pass them to the service.

Update your frontend/response schema in schemas.py to include page and total_pages in the response payload.

Prepare Kendra for soft deletes by going to the AWS Console -> Kendra -> Index -> Facets/Custom Attributes and adding an is_active boolean field.

Fix deletion side-effects in bedrock_service.py by updating delete_document to first run batch_put_document setting is_active to false for that ID, then firing the standard batch_delete_document.

Fix search artifacts by updating rag_search in bedrock_service.py to include a retrievalConfiguration filter requiring is_active to equal true.

Verification
Upload 12 PDFs. Call the list API with ?page=1&size=10 and verify you receive 10 items. Delete one of the PDFs, then immediately hit the search API for its contents—it should return zero results due to the is_active filter.