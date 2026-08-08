# Security Policy

## Reporting a vulnerability

If you find a security issue, do not open a public issue first.  
Contact maintainers privately and include:

- affected endpoint/module;
- reproduction steps;
- potential impact;
- suggested mitigation.

## Baseline controls in this project

- staff authentication via Flask-Login + password hashing;
- RBAC checks with permission decorators;
- CSRF protection for state-changing forms;
- secure session cookie settings in production;
- upload restrictions and path safety;
- tenant isolation by database and slug context.

## Responsible disclosure

- Give maintainers reasonable time to patch before public disclosure.
- Share sanitized PoC only (no real user data).
