Creating Your First Program (After Fresh Local Setup)
=====================================================

After running ``docker compose up`` and creating a superuser, the site loads with only placeholder content (the "New Site" page with Learn/Teach/Volunteer sections).

The frontend remains minimal until at least one **Program** is created.  
Adding a program unlocks the real UI: program listings, registration flows, class creation, scheduling, and many Bootstrap-styled elements (forms, buttons, grids, cards, etc.).

Prerequisites
-------------
- Docker environment is running (``docker compose up`` completed successfully)
- A superuser account has been created:

.. note::
   If you haven't created a superuser yet, run:

  .. code-block:: bash

     docker compose exec web python esp/manage.py createsuperuser

  and follow the prompts.

Step-by-Step Instructions
-------------------------

1. **Log in as superuser**  
   Go to one of these URL and log in with your superuser credentials:  
   - http://127.0.0.1:8000/admin/  
   - http://localhost:8000/admin/ (fallback if 127.0.0.1 doesn't work)

   .. note:: On Windows with Docker Desktop, ``localhost:8000`` may be unreliable. Use ``127.0.0.1:8000`` instead.

2. **Go to the program management page**  
   Visit:  
   - http://127.0.0.1:8000/manage/programs/  
   - http://localhost:8000/manage/programs/ (fallback)

3. **Create a new program**  
   - Click **Create a New Program**.  
   - Fill in the minimal required fields:  
     - **Program Title**: e.g., "Test Program 2026"  
     - **Short name / Slug**: e.g., "test_2026" (used in URLs)  
     - **Status**: "Open" or "Active"  
   - Other fields (dates, description, grade range, etc.): use defaults or simple values.  
   - Click **Make Program Happen!**.

4. **Verify the program appears**  
   - Refresh the homepage: http://127.0.0.1:8000/ (or http://localhost:8000/)  
   - Or try: http://127.0.0.1:8000/manage/program/  
   - Or direct detail view: http://127.0.0.1:8000/manage/test-2026/main (replace with your slug)  
   You should now see your program listed, with links to view, register, etc.

What Success Looks Like
-----------------------
After creating a program, the site transforms from a static placeholder to a dynamic platform with:
- Program listings and detail pages
- Registration links
- Class creation interfaces
- Full Bootstrap-styled components you can inspect and modify

Tips & Troubleshooting
----------------------

- **Page still looks empty**  
  - Ensure you're logged in  
  - Hard refresh browser (Ctrl + F5 on Windows/Linux, Cmd + Shift + R on Mac)  
  - Restart web container: ``docker compose restart web``

- **Learn / Teach / Volunteer sections still empty**  
  These are **QSD** (Quick Static Documents) pages — editable content stored in the database.  
  To populate them:  
  1. Visit http://127.0.0.1:8000/learn/index.html (and similarly for /teach/, /volunteer/)  
  2. Click **"change that"**  
  3. Add some text content and save

- **localhost:8000 doesn't load, but 127.0.0.1:8000 does**  
  This is a known Windows + Docker Desktop behavior. Use 127.0.0.1 — it's reliable.

Next Steps
----------
Now that you have a working program, you can:
- Explore the Bootstrap-styled components (forms, buttons, navigation) that will be part of the theming improvements
- Inspect how Bootstrap 2.3.2 is currently loaded (hint: check base templates and static files)
- Add classes, resources, or open registration to see more UI elements
- Start identifying color contrast issues or outdated Bootstrap usage

Happy building — and thanks for your interest in contributing to the Learning Unlimited developer experience!