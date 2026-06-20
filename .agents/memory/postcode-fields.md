---
name: Postcode field implementation
description: International postcode support on ContactInfo — fully implemented and tested. All known bugs fixed.
---

## Summary of changes

`address_zip` and `address_postcode` live on `ContactInfo`. Users see a state/province dropdown that includes "International". Selecting International hides the ZIP field and shows the postcode field via JS.

## Model (migration 0047)
- `address_zip`      max_length **10**  (was 5 — too short for ZIP+4 "12345-6789")
- `address_postcode` max_length **12**  (was 10 — extra headroom for edge-case formats)

## Validators (`user_profile.py`)
- `validate_zip`      — regex `r'^\d{5}(-\d{4})?$'`  rejects script injection, allows 5-digit and ZIP+4
- `validate_postcode` — regex `r'^[A-Za-z0-9 \-]+$'` rejects all special chars; covers UK/CA/IE formats

## Forms (all three: UserContactForm, EmergContactForm, MinimalUserInfo)
- Both fields `required=False`; `clean()` requires **at least one** of zip or postcode
- `UserContactForm.clean()` guarded by `self._address_required` (False for teachers when tag is off)
- `EmergContactForm.clean()` guarded by `self.cleaned_data.get('emerg_address_state')` — avoids
  a misleading "missing zip" cascade error when other required address fields also fail
- All zip fields: `length=10, max_length=10`; all postcode fields: `length=12, max_length=12`
- `MinimalUserInfo.address_state` has `widget=forms.Select(attrs={'class': 'input-mini', ...})`

## JS toggle (`profile.html`)
- `check_state()` / `check_emerg_state()` — toggle ZIP↔postcode + country on state dropdown change
- Called on page load and on `change` event; safe when field IDs are absent (no-op)
- `copy_parent_info()` in `emergencycontact.html` copies postcode and re-runs `check_emerg_state()`

## Custom forms (`customforms/forms.py` — AddressWidget)
- 5-widget layout: street, city, state, zip, postcode
- Inline IIFE JS in `format_output()` scoped via `document.currentScript.previousElementSibling`
  — safe with multiple AddressWidget instances on the same page
- `compress()` returns `{name}_postcode`; `decompress()` pads to 5 values for backward compat
- `HiddenAddressWidget` has 5 HiddenInput widgets (preserves postcode across FormWizard steps)

## Templates
- `usercontact.html` / `emergencycontact.html` — both fields rendered with error spans
- `userview.html` — `{% firstof address_postcode address_zip %}` for display
- Admin `ContactInfoAdmin` — displays and searches zip, postcode, city, street

## Other modules
- `usersearch.py` — `postcode` criterion does case-insensitive exact match on `address_postcode`
- `program/forms.py` — `ProgramFilterForm` has `zip_query_type` with 'postcode' choice
- `mapgenmodule.py` — collects both `address_zip` and `address_postcode` for map data

## Gotcha: migration field kwargs must exactly match the model
If a migration's field definition adds kwargs (e.g., `help_text`) that are absent from the model,
Django's autodetector logs "models have changes not reflected in a migration."
Fix: keep migration AlterField kwargs identical to the model field definition.
