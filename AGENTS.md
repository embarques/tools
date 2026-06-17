# AGENTS.md

This repository contains tools for importing data into the MongoDB application database.
When adding or updating import actions, use this file as the reference for the target
Mongo collection object shapes.

## Import Action Guidelines

- Postgres source schemas may remain unchanged. Import actions should transform source rows into the Mongo shapes below.
- Reference objects should use `id` for referenced records when an id is available.
- Do not use `_id` inside embedded reference objects unless the collection explicitly stores the document primary key at the top level.
- Phone numbers should be stored in `phones` arrays with objects like `{ "type": "mobile", "number": "...", "isPrimary": true }`.
- Branch references should generally use `{ "id": 1, "code": "NYC" }`, and include `name` when available.
- Invoice parent documents should use `invoiceDetails`, not `invoice_details`.
- Keep collection documents close to these shapes when creating or updating import/build logic.

## Mongo Object Payloads

```jsonc
{
  // Model: Customer. Collection: customers.
  "customer": {
    "name": "Acme Corp",
    "customerType": 1,
    "phones": [
      { "type": "mobile", "number": "+12015550100", "isPrimary": true },
      { "type": "business", "number": "555-0101" }
    ],
    "email": "acme@example.com",
    "active": true,
    "IDNumber": "123456789",
    "notes": "",
    "branch": { "id": 1, "code": "NYC", "name": "New York" },
    "address": {
      "address1": "123 Main St",
      "city": "Miami",
      "state": "FL",
      "zipcode": "33101",
      "country": "US"
    }
  },
  // Model: User. Collection: users.
  "user": {
    "uid": "firebase_uid_from_auth",
    "email": "user@example.com",
    "userName": "jdoe",
    "fullName": "John Doe",
    "active": true,
    "branch": { "id": 1, "name": "Main", "code": "NYC" },
    "role": { "id": 1, "name": "Administrador", "active": true }
  },
  // Model: Role. Collection: roles.
  "role": {
    "name": "Manager",
    "active": true,
    "permissions": [{ "id": 26 }, { "id": 27 }, { "id": 28 }]
  },
  // Model: Permission. Collection: permissions.
  "permission": {
    "name": "canViewCustomer",
    "resourceType": "customer",
    "create": false,
    "view": true,
    "update": false,
    "delete": false,
    "print": false
  },
  // Model: Branch. Collection: branches.
  "branch": {
    "name": "New York Office",
    "type": "office",
    "code": "NYC",
    "phones": [
      { "type": "business", "number": "+12125551000", "isPrimary": true }
    ],
    "disclaimer": "",
    "logo": "",
    "address": {
      "address1": "100 Broadway",
      "city": "New York",
      "state": "NY",
      "zipcode": "10005",
      "country": "US"
    },
    "settings": {
      "labelPrefix": "NYC",
      "roundDecimalPlaces": 2,
      "defaultLabelStatus": 1
    }
  },
  // Model: Employee. Collection: employees.
  "employee": {
    "name": "Jane Driver",
    "title": "Driver",
    "department": "Delivery",
    "phones": [
      { "type": "mobile", "number": "+12125552000", "isPrimary": true }
    ],
    "email": "jane@example.com",
    "active": true,
    "branch": { "id": 1, "code": "NYC" },
    "address": { "city": "Bronx", "state": "NY", "zipcode": "10451" }
  },
  // Model: Container. Collection: containers.
  "container": {
    "name": "Container A",
    "booking": "BK-1001",
    "containerNumber": "MSCU1234567",
    "sealNumber": "SEAL-99",
    "broker": "Broker Co",
    "company": "Shipping Co",
    "cost": 1500.0,
    "departureDate": "2026-06-01T00:00:00Z",
    "arrivalDate": "2026-06-15T00:00:00Z"
  },
  // Model: Delivery. Collection: deliveries.
  "delivery": {
    "name": "Route 1",
    "date": "2026-06-10T08:00:00Z",
    "container": { "id": 1, "name": "Container A", "containerNumber": "MSCU1234567" },
    "employee": { "id": 5, "name": "Jane Driver" },
    "helper1": { "id": 6, "name": "Helper One" },
    "helper2": null
  },
  // Model: Barcode. Embedded in invoice detail documents.
  "barcode": {
    "number": "LBL-00001",
    "status": { "id": 1, "name": "CREATED" },
    "container": { "id": 1, "name": "Container A" },
    "delivery": { "id": 1, "name": "Route 1" }
  },
  // Model: Pickup. Collection: pickups.
  "pickup": {
    "date": "2026-06-10",
    "branch": { "id": 1, "code": "NYC" },
    "employee": {
      "id": 5,
      "name": "Jane Driver",
      "phones": [
        { "type": "mobile", "number": "+12125552000", "isPrimary": true }
      ],
      "active": true
    },
    "sender": {
      "name": "Sender Name",
      "customerType": 1,
      "phones": [
        { "type": "mobile", "number": "+12125553000", "isPrimary": true }
      ],
      "email": "sender@example.com",
      "IDNumber": "111",
      "address": {
        "address1": "10 Oak Ave",
        "city": "Bronx",
        "state": "NY",
        "zipcode": "10451"
      }
    },
    "receiver": {
      "name": "Receiver Name",
      "customerType": 2,
      "phones": [
        { "type": "mobile", "number": "+12125554000", "isPrimary": true }
      ],
      "address": { "city": "Miami", "state": "FL", "zipcode": "33101" }
    },
    "purpose": "Pickup boxes",
    "sector": { "id": 1, "name": "North" },
    "comments": [
      { "purpose": "Boxes", "unit": "pcs", "quantity": 3, "description": "Medium boxes" }
    ]
  },
  // Model: PickupRoute. Collection: pickup_routes.
  "pickupRoute": {
    "name": "Bronx NY",
    "states": ["NY"],
    "cities": [{ "cityName": "Bronx", "stateCode": "NY" }],
    "zipCodes": ["10451", "10452"],
    "zipRanges": [{ "start": "10400", "end": "10499" }]
  },
  // Model: Invoice. Collection: invoices.
  "invoice": {
    "number": "INV-1001",
    "date": "2026-06-10",
    "branch": { "id": 1, "code": "NYC" },
    "cost": 120.0,
    "payment": 20.0,
    "balance": 100.0,
    "discount": 0,
    "surcharge": 0,
    "paidRegion": "",
    "paidStatus": "PARTIAL",
    "employee": { "id": 5, "name": "Tasador", "userName": "tasador1", "fullName": "Main Tasador" },
    "container": { "id": 1, "name": "Container A" },
    "sender": {
      "name": "Sender Co",
      "customerType": 1,
      "phones": [
        { "type": "business", "number": "+13055551000", "isPrimary": true }
      ],
      "IDNumber": "123",
      "address": { "city": "Miami", "state": "FL", "zipcode": "33101" }
    },
    "receiver": {
      "name": "Receiver Co",
      "customerType": 2,
      "phones": [
        { "type": "mobile", "number": "+13055552000", "isPrimary": true }
      ]
    },
    "invoiceDetails": [
      { "id": "6a1a968553f10a166b216694" },
      { "id": "6a1a968553f10a166b216695" }
    ]
  },
  // Model: JournalPayment. Action payload for journal/payment creation.
  "journalPayment": {
    "transactionType": "PAYMENT",
    "amount": 50.0,
    "invoiceId": "674a1b2c3d4e5f6789012345",
    "paymentMethod": { "id": 1, "name": "CASH" },
    "description": "Invoice payment"
  },
  // Model: IncomeStatement. Collection: income_statements.
  "incomeStatement": {
    "date": "2026-06-10T00:00:00Z",
    "branch": { "id": 1, "name": "Main Branch", "code": "NYC" },
    "currency": "USD",
    "rate": 1,
    "container": { "id": 1, "name": "Container A" },
    "delivery": { "id": 1, "name": "Route 1" }
  },
  // Model: Truck. Collection: trucks.
  "truck": {
    "truckId": "TRK-001",
    "name": "Truck 1",
    "vin": "1HGCM82633A004352",
    "year": 2022,
    "fuelType": "diesel",
    "branch": "NYC"
  },
  // Model: EmployeeGroup. Collection: employee_groups.
  "employeeGroup": {
    "employeeGroupId": "EG-001",
    "name": "Morning Crew",
    "branch": "NYC",
    "employees": [
      { "id": 5, "name": "Jane Driver" },
      { "id": 6, "name": "Helper One" }
    ]
  },
  // Model: RouteAssignment. Collection: route_assignments.
  "routeAssignment": {
    "routeAssignmentId": "RA-2026-06-10",
    "name": "Monday Route",
    "date": "2026-06-10T08:00:00Z",
    "truck": { "id": "674a1b2c3d4e5f6789012345", "name": "Truck 1" },
    "employeeGroup": { "id": "674b2c3d4e5f6789012346", "name": "Morning Crew" }
  }
}
```
