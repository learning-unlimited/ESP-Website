+ ## 🚀 Getting Started
+
+ Follow these steps to set up the project locally:
+
+ ### 1. Clone the repository
+ ```bash
+ git clone https://github.com/learning-unlimited/ESP-Website.git
+ cd ESP-Website
+ ```
+
+ ### 2. Create a virtual environment
+ ```bash
+ python -m venv venv
+ source venv/bin/activate   # On Windows: venv\Scripts\activate
+ ```
+
+ ### 3. Install dependencies
+ ```bash
+ pip install -r requirements.txt
+ ```
+
+ ### 4. Run migrations
+ ```bash
+ python manage.py migrate
+ ```
+
+ ### 5. Start the development server
+ ```bash
+ python manage.py runserver
+ ```
+
+ ---
+
+ ## ⚠️ Common Issues
+
+ **Error: Module not found**
+ → Ensure virtual environment is activated
+
+ **Error: Database issues**
+ → Run:
+ ```bash
+ python manage.py migrate
+ ```
+
+ ---
+
+ ## 🤝 Contributing
+
+ 1. Fork the repository
+ 2. Create a new branch (`git checkout -b feature-name`)
+ 3. Commit your changes
+ 4. Push and open a PR
