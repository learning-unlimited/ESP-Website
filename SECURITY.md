# Security Policy

The ESP Website is used to run educational programs that serve students, including
minors, so keeping it secure matters a great deal to us. We appreciate the efforts
of security researchers and community members who help keep the ESP Website and
the people who rely on it safe.

## Supported Versions

The [`main`](https://github.com/learning-unlimited/ESP-Website/tree/main) branch
is the only version that receives security fixes. Chapter-specific deployment
branches (e.g. `berkeley`, `chicago-prod`) are maintained by their respective
chapters; we recommend chapters keep those branches in sync with `main` so they
receive fixes promptly.

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues,
discussions, or pull requests.** Public reports of unpatched vulnerabilities put
program participants' data at risk before a fix is available.

Instead, report vulnerabilities privately by emailing:

**web-team@learningu.org**

To help us triage and respond quickly, please include as much of the following as
you can:

- The type of vulnerability (e.g. SQL injection, XSS, authentication/authorization
  bypass, information disclosure)
- The affected file(s), URL(s), or module(s), and the branch or commit where you
  found the issue
- Step-by-step reproduction instructions, including any special configuration
  required
- Proof-of-concept or exploit code, if available
- The potential impact, including whether the issue could expose data belonging
  to students or other program participants

### What to expect

- We will acknowledge receipt of your report within 5 business days.
- We will investigate, validate the report, and follow up with an initial
  assessment and an expected timeline for a fix.
- We will keep you updated as we work toward a resolution, and will credit you in
  the fix (e.g. release notes or commit message) unless you'd prefer to remain
  anonymous.
- We ask that you give us a reasonable amount of time to address the issue before
  any public disclosure, and coordinate the disclosure timeline with us.

## Scope

This policy covers the ESP Website application code in this repository. The
following are out of scope for reports to this project directly:

- Third-party services, libraries, or dependencies (please report those to their
  respective maintainers)
- Chapter-specific infrastructure or hosting not managed in this repository
- Social engineering, physical security, or denial-of-service attacks

## Safe Harbor

We consider security research conducted in good faith and consistent with this
policy to be authorized. When you:

- make a good-faith effort to avoid privacy violations, data destruction, and
  disruption of service,
- only interact with accounts and data you own or have explicit permission to
  test, and
- report any vulnerabilities you find promptly and do not publicly disclose them
  before we've had a reasonable opportunity to address them,

we will not pursue legal action against you for that research, and we will work
with you to understand and resolve the issue quickly.

Thank you for helping keep the ESP Website, and the students who depend on it,
safe.
