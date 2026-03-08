Plan: Jan Aushadhi UI & Backend Upgrade
This plan redesigns the Jan Aushadhi tool within the existing pharmai_portal. We are upgrading from basic LLM prompts to an accurate RAG knowledge base. The system will handle generic alternatives (via the Medicine PDF) and list store locators for a specific city/state (via the Kendra Locations PDF). Stores will feature a native "Get Directions" link that opens Google Maps.

Steps

Frontend UI Redesign:

Update [frontend/index.html](frontend/index.html) to redesign the existing Jan Aushadhi <div id="janAushadhiPanel">.
Create a clean, modern tabbed interface:
Tab 1: Find Alternatives: Input for prescribed medicine name. Results table displaying the original medicine, Jan Aushadhi generic equivalent, MRP, and computed savings.
Tab 2: Find a Kendra: Input for City/State. Displays a scrollable list of store result cards.
Add a "Get Directions" button to each locator card holding a Smart URL: https://www.google.com/maps/dir/?api=1&destination=${encodedAddress} with target="_blank".
Update [frontend/js/main.js](frontend/js/main.js) (or the main controller) to process these distinct JSON responses and bind them to the new UI DOM elements.
Backend Intent Router:

Create a new endpoint in [frontend/app.py](frontend/app.py), e.g., /api/janaushadhi/query.
LLM Intent Classification: First, pass the query to an LLM router to classify the request as either medicine_alternative or kendra_locator, extracting the relevant entity (Medicine Pattern vs City/State Pattern).
RAG Backend Integration:

Medicine Query: If medicine_alternative, query the AWS RAG backend specifically targeting the Medicine PDF: "Find the Jan Aushadhi equivalent and MRP for {medicine}".
Location Query: If kendra_locator, query the AWS RAG specifically targeting the Location PDF: "Provide the exact addresses of all Jan Aushadhi Kendras located in {City/State}".
JSON Formatting: Enforce a strict structured JSON output layer post-RAG so the frontend receives normalized arrays (e.g., locations: [{ name, address, pin }] or medicines: [{ generic_name, original_name, mrp, savings_percentage }]).
Knowledge Base Ingestion Pipeline:

Ensure the existing /api/kb/upload endpoints seamlessly accommodate the ingestion of the two PDF files to the existing AWS RAG infrastructure.
Verification

Run local server using flask run (or existing startup script).
Test UI by typing a city (e.g., "Kerkera, Haryana") and confirm the Google Maps link successfully resolves to the generated text address.
Test UI by typing a common drug (e.g., "Paracetamol 500mg") and verify the returned generic matches the uploaded RAG PDF and not raw LLM hallucination.
Decisions

Geo vs RAG Constraint: Instead of unreliable geospatial proximity computing out of RAG embeddings, we will extract all stored locators matching a given "City or State" string.
Google Maps: Used the native map redirection URL instead of embedding an interactive map layer to save on Google API complexity and paid tokens.