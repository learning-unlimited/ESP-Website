## djhtml Assessment Report

### Summary of Findings

To evaluate whether **djhtml** would be a good fit for formatting Django templates in the ESP Website codebase, I tested it on a small but representative set of templates that cover different parts of the application. This included:

* `esp/templates/customforms/form.html`
* `esp/templates/admin/emails.html`
* `esp/templates/contact.html`
* `esp/templates/404.html`

These files were chosen intentionally to reflect a mix of real-world usage such as form-heavy pages, admin interfaces, and general layout templates.

After running djhtml on these templates, I observed that it consistently applied clean 2-space indentation across both standard HTML elements and Django template constructs like:

* `{% block %}`
* `{% if %}`
* `{% for %}`

Importantly, the formatter handled nested logic inside tags such as `<form>`, `<table>`, `<style>`, and `<script>` without introducing any syntax issues or altering template behavior. Even custom template tags (e.g., `{% inline_qsd_block %}`) were formatted correctly.

Overall, the formatted output was noticeably more readable, and I did not detect any disruptions in template execution or rendering.

### Integration & Automation

To make formatting consistent across the team and avoid manual cleanup, I set up a `.pre-commit-config.yaml` configuration using djhtml:

```yaml
repos:
-   repo: https://github.com/rtts/djhtml
    rev: 3.0.10
    hooks:
    -   id: djhtml
```

With this configuration in place, running `pre-commit` automatically reformats any modified HTML template files before they are committed. This helps enforce a uniform style without adding overhead to the development workflow.

### Recommendation

Based on my evaluation, **djhtml is a good addition to the ESP development workflow**. It provides consistent and Django-aware formatting that improves template readability while preserving functionality. Integrating djhtml via pre-commit allows contributors to focus on application logic during code reviews, instead of spending time addressing indentation and formatting inconsistencies.

I recommend adopting djhtml as the standard template formatter for the project moving forward.