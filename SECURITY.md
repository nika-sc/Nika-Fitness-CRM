# Security Policy

## Reporting a vulnerability

If you find a security issue, do not open a public issue first.  
Email maintainers privately at **info@nika-sc.ru** (subject: `Nika Fit — security`) and include:

- affected endpoint/module;
- reproduction steps;
- potential impact;
- suggested mitigation (if any).

## Baseline controls in this project

- staff authentication via Flask-Login + password hashing;
- RBAC checks with permission decorators;
- CSRF protection for state-changing forms;
- secure session cookie settings in production;
- upload restrictions and path safety;
- single-club database isolation (`DATABASE_URL` per deployment).

## Responsible disclosure

- Give maintainers reasonable time to patch before public disclosure.
- Share sanitized PoC only (no real user data).
