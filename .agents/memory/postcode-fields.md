---
name: Postcode field implementation
description: International postcode support added to ESP-Website user address fields (GitHub issue #5845).
---

## Rule
`address_postcode = CharField(max_length=10)` was added to `ContactInfo` model (migration `0046`).

**Files changed:**
- Model: `esp/users/models/__init__.py`
- Forms: `esp/users/forms/user_profile.py` — `UserContactForm`, `EmergContactForm`, `MinimalUserInfo`; `validate_postcode()` validator allows only `A-Za-z0-9 -`
- Templates: `users/profile.html`, `users/usercontact.html`, `users/emergencycontact.html`, `users/studentprofile.html`, `users/userview.html`, `program/modules/medliab.html`, `accounting/refund_receipt_form.html`
- Admin/search: `program/forms.py` (`ProgramFilterForm`), `program/views.py`, `users/controllers/usersearch.py`, `statistics.py` (`zipcodes()`), `mapgenmodule.py`, `customforms/DynamicForm.py`

**Why:** Supports non-US addresses where ZIP code (5 digits) is not valid. The field is optional (blank allowed); the form's `clean()` enforces that at least one of `address_zip` or `address_postcode` is supplied when a non-US state is selected.
