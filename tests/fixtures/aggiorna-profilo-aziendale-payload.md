# Payload test - Aggiorna profilo aziendale

Payload per il form "Gestione diretta - Aggiorna profilo aziendale" mostrato nello screenshot.

Payload completo: include riferimenti al form frontend e `allowedValues` per select/dropdown.

```json
{
  "formName": "Aggiorna profilo aziendale",
  "fields": [
    {
      "fieldId": "organization_name",
      "targetRef": "companyProfile.organizationName",
      "label": "Nome organizzazione",
      "question": "Qual e' il nome dell'organizzazione o la ragione sociale dell'azienda?",
      "expectedType": "string"
    },
    {
      "fieldId": "legal_address",
      "targetRef": "companyProfile.legalAddress",
      "label": "Indirizzo legale",
      "question": "Qual e' l'indirizzo legale dell'organizzazione?",
      "expectedType": "address"
    },
    {
      "fieldId": "country",
      "targetRef": "companyProfile.country",
      "label": "Paese",
      "question": "Qual e' il paese dell'organizzazione?",
      "expectedType": "enum",
      "validationRules": {
        "allowedValues": [
          { "value": "IT", "label": "Italia" },
          { "value": "DE", "label": "Germania" },
          { "value": "FR", "label": "Francia" },
          { "value": "ES", "label": "Spagna" }
        ]
      }
    },
    {
      "fieldId": "operating_countries",
      "targetRef": "companyProfile.operatingCountries",
      "label": "Paesi operativi",
      "question": "In quali paesi opera l'organizzazione? Restituisci l'elenco dei paesi se presenti.",
      "expectedType": "array",
      "validationRules": {
        "multiple": true,
        "allowedValues": [
          { "value": "IT", "label": "Italia" },
          { "value": "DE", "label": "Germania" },
          { "value": "FR", "label": "Francia" },
          { "value": "ES", "label": "Spagna" }
        ]
      }
    },
    {
      "fieldId": "industry_sector",
      "targetRef": "companyProfile.industrySector",
      "label": "Settore",
      "question": "Qual e' il settore dell'organizzazione?",
      "expectedType": "enum",
      "validationRules": {
        "allowedValues": [
          { "value": "IT_CONSULTING", "label": "Consulenza IT" },
          { "value": "HEALTHCARE", "label": "Sanita'" },
          { "value": "FINANCE", "label": "Finanza" },
          { "value": "MANUFACTURING", "label": "Industria" },
          { "value": "RETAIL", "label": "Retail" }
        ]
      }
    },
    {
      "fieldId": "employee_count",
      "targetRef": "companyProfile.employeeCount",
      "label": "Numero dipendenti",
      "question": "Qual e' il numero di dipendenti dell'organizzazione?",
      "expectedType": "integer"
    },
    {
      "fieldId": "representative",
      "targetRef": "companyProfile.representative",
      "label": "Rappresentante",
      "question": "Chi e' il rappresentante dell'organizzazione?",
      "expectedType": "string"
    },
    {
      "fieldId": "organization_email",
      "targetRef": "companyProfile.organizationEmail",
      "label": "Email organizzazione",
      "question": "Qual e' l'email dell'organizzazione?",
      "expectedType": "email"
    },
    {
      "fieldId": "privacy_contact_name",
      "targetRef": "privacy.contactName",
      "label": "Contatto privacy",
      "question": "Chi e' il contatto privacy dell'organizzazione?",
      "expectedType": "string"
    },
    {
      "fieldId": "privacy_contact_role",
      "targetRef": "privacy.contactRole",
      "label": "Ruolo contatto privacy",
      "question": "Qual e' il ruolo del contatto privacy?",
      "expectedType": "enum",
      "validationRules": {
        "allowedValues": [
          { "value": "PRIVACY_OFFICER", "label": "Privacy Officer" },
          { "value": "DPO", "label": "DPO" },
          { "value": "LEGAL", "label": "Legale" },
          { "value": "HR", "label": "HR" },
          { "value": "IT_MANAGER", "label": "Responsabile IT" }
        ]
      }
    },
    {
      "fieldId": "privacy_contact_email",
      "targetRef": "privacy.contactEmail",
      "label": "Email privacy",
      "question": "Qual e' l'email del contatto privacy?",
      "expectedType": "email"
    },
    {
      "fieldId": "privacy_contact_phone",
      "targetRef": "privacy.contactPhone",
      "label": "Telefono contatto privacy",
      "question": "Qual e' il numero di telefono del contatto privacy?",
      "expectedType": "phone"
    }
  ],
  "options": {
    "strictEvidence": true,
    "language": "it"
  }
}
```
