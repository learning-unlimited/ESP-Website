---
name: Postcode field implementation
description: International postcode support added to ESP-Website user address fields (GitHub issue #5845). All known bugs fixed.
---

## Rule
`address_postcode = CharField(max_length=12)` exists on `ContactInfo` (migration `0046` added it at max_length=10; migration `0047` widened both fields).
`address_zip = CharField(max_length=10)` — widened from 5 to support ZIP+4 format "12345-6789" (migration `0047`).

**Why:** Supports non-US addresses where ZIP code (5 digits) is not valid. The fields are optional individually; form `clean()` requires at least one of zip or postcode when address data is submitted.

## Completed fixes (all done)

1. **Model** — `address_zip` max_length 5→10, `address_postcode` max_length 10→12 (`esp/users/models/__init__.py`)
2. **Migration 0047** — `esp/users/migrations/0047_alter_contactinfo_zip_postcode.py` — alters both fields. Must exactly match model field kwargs (no help_text in model → no help_text in migration) or Django's autodetector flags a mismatch.
3. **Profile forms** — `UserContactForm`, `EmergContactForm`, `MinimalUserInfo` in `user_profile.py` — postcode max_length updated to 12 to match model.
4. **Custom forms** — `esp/customforms/forms.py` — `AddressWidget` now has 5 sub-widgets (added postcode TextInput hidden by default); `HiddenAddressWidget` has 5 `HiddenInput` widgets; `AddressField` compress() includes `{name}_postcode`; zip CharField max_length 5→10; postcode CharField max_length=12; `format_output()` injects self-contained IIFE JS that toggles ZIP/postcode rows based on USStateSelect value ("International" triggers postcode mode). Uses `document.currentScript.previousElementSibling` to scope each widget independently — safe with multiple address widgets on the same page.
5. **DynamicForm** — already had `_contactinfo_map` with `address_postcode` and `'postcode': 'address_postcode'` (no change needed).
6. **Admin** — `ContactInfoAdmin` now displays and searches by `address_zip`, `address_postcode`, `address_city`, `address_street`.

## Known gotcha
If a migration's field definition includes kwargs (e.g., `help_text`) that are absent from the model, Django's autodetector logs: "Your models have changes not reflected in a migration." Fix: keep the migration field kwargs identical to the model field kwargs.
