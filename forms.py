 class UserForm(forms.Form):
-    email = forms.EmailField()
+    email = forms.EmailField(
+        label="Email Address",
+        widget=forms.EmailInput(attrs={
+            "placeholder": "Enter your email address"
+        })
+    )

-    username = forms.CharField()
+    username = forms.CharField(
+        label="Username",
+        widget=forms.TextInput(attrs={
+            "placeholder": "Choose a username"
+        })
+    )

-    password = forms.CharField(widget=forms.PasswordInput())
+    password = forms.CharField(
+        label="Password",
+        widget=forms.PasswordInput(attrs={
+            "placeholder": "Enter a secure password"
+        })
+    )
