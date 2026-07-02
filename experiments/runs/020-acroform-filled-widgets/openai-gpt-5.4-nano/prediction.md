# Filled Vendor Onboarding Form

**Document ID:** T20-ACROFORM-WIDGETS

This packet tests whether filled PDF form widget appearances are preserved.  
Static labels alone are not enough; selected states and entered values are part of the record.

## Vendor Intake Form

- **Vendor ID:** VEN-4092-Q  
- **Legal name:** Northstar Reagents LLC  
- **Tax class:** C-Corp *(selected)*, LLC, Sole Proprietor  
- **Payment method:** ACH *(selected)*, Wire  
- **Routing number:** RT-072-441  
- **Account suffix:** ACCT-8831  
- **Review queue:** Ops-7A  
- **Expedite review:** Expedite review  
- **W-9 received:** W-9 received  
- **Approver initials:** MR  

## Action

Route the vendor to the selected review queue using the selected payment method.

[FORM FIELD] tax_class: LLC  
[FORM FIELD] payment_ach: Yes  
[FORM FIELD] expedite_review: Yes