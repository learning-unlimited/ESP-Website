Creating Your First Program (After Fresh Local Setup)
=====================================================

After `setting up your Docker environment <docker.rst>`_, the site loads with only placeholder content (the "New Site" page with Learn/Teach/Volunteer sections).

The frontend remains minimal until at least one **Program** is created.  
Adding a program unlocks the real UI: program listings, registration flows, class creation, scheduling, and many Bootstrap-styled elements (forms, buttons, grids, cards, etc.).

Prerequisites
-------------
- Docker environment is running (``docker compose up`` completed successfully)
- A superuser account has been created

Step-by-Step Instructions
-------------------------

Quick Start (Optional)
^^^^^^^^^^^^^^^^^^^^^^
If you want a working program with sample data immediately, run::

   docker compose exec web python esp/manage.py seed_dummy_data

This creates a program with timeslots, rooms, teachers, students, and classes already configured. You can skip ahead to step 4 to verify it worked, or continue below to learn how to create a program from scratch.

Full Walkthrough
^^^^^^^^^^^^^^^^
If you want to make your own program and understand the process, follow these steps:

1. **Log in as superuser**  
   Log in with your superuser credentials:  
   - http://127.0.0.1:8000/  

2. **Go to the program management page**  
   Visit:  
   - http://127.0.0.1:8000/manage/programs/  

3. **Create a new program**  
   - Click **Create a New Program**.  
   - Fill in the minimal required fields:  
     - **Term or year, in URL form**: e.g., "2026"  
     - **Term, in English**: e.g., "Splash Dev"  
     - **Program Type**: e.g., "SplashDev"
   - Other fields (dates, description, grade range, etc.): use defaults or simple values.  
   - Click **Make Program Happen!**.

4. **Verify the program appears**  
   - Refresh the list of programs: http://127.0.0.1:8000/manage/programs/  
   - Or direct detail view: http://127.0.0.1:8000/manage/SplashDev/2026/main (replace with your slug)  
   You should now see your program listed, with links to view, register, etc.

What Success Looks Like
-----------------------
After creating a program, the site transforms from a static placeholder to a dynamic platform with:
- Program listings and detail pages
- Registration links
- Class creation interfaces

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
