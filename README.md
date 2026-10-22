## Rental API
 
The API starts rentals and provides read endpoints.
All endpoints require authentication.
 
- GET /api/consoles/
- GET /api/prices/?console=ID
- POST /api/rentals/
- GET /api/rentals/
- GET /api/rentals/ID/
 
POST fields:
- end_at: a future date and time in ISO 8601 format.
- items: a non-empty list of objects with console and pricing IDs.
- delivery_address and notes: optional strings.
 
The server sets the customer, start time, Active status and tariff snapshots.
Consoles must be available and not booked. Duplicate consoles are rejected.
Invalid requests roll back all changes. Charges round up to tariff blocks.
Customers see their own rentals; staff can see all rentals.
 
Checks:
 
    .venv\Scripts\python.exe manage.py check
    .venv\Scripts\python.exe manage.py makemigrations --check --dry-run
    .venv\Scripts\python.exe manage.py test apps.rental --verbosity 2