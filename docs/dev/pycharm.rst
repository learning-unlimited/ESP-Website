Using the PyCharm IDE
---------------------

The Professional Edition of PyCharm (unfortunately, not the free Community Edition) supports development and debugging of Django projects running in Docker.
Follow these steps to set it up for this project:

1. Enable Docker support in PyCharm (Preferences > Build, Execution, Deployment > Docker).

2. Enable Django support (Preferences > Languages & Frameworks > Django). The Django project root is the ``esp`` directory. The Settings file is ``esp/settings.py``.

3. Set up a remote Python interpreter via Docker Compose (Preferences > Project > Python Interpreter > Add > Docker Compose). Select the ``web`` service.

4. Set up your run/debug configuration by going to Run -> Edit Configurations. Add a configuration of type "Django Server".
    * Host: 0.0.0.0   Port: 8000
    * Environment variables:
        * DJANGO_SETTINGS_MODULE=esp.settings
        * VIRTUAL_ENV=/usr

To get started, make sure your containers are built by running ``docker compose up --build`` once from a terminal.

Now you can start or stop the server using the Run, Debug, or Stop commands in the ``Run`` menu. To debug your code, you can set whatever
breakpoints you want, and select Run -> Debug to run the server. Go to localhost:8000 on your browser as usual, and the debugger will stop
on a breakpoint when it is hit.
