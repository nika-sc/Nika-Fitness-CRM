# Open Source Publication Checklist

Checklist before switching repository visibility to **Public**.

## 1) Secrets and private data

- [ ] `.env` is not tracked.
- [ ] No API keys/passwords/tokens in committed files.
- [ ] No real personal data in screenshots or sample dumps.
- [ ] Upload directories do not contain private files.

## 2) Legal and docs baseline

- [ ] `LICENSE` (MIT) exists.
- [ ] `README.md` is updated for public audience.
- [ ] `CONTRIBUTING.md`, `SECURITY.md`, `SUPPORT.md` are present.
- [ ] `docs/USER_GUIDE.md` and `docs/USER_WALKTHROUGH.md` are current.

## 3) Product positioning

- [ ] README clearly states this is **Nika Fitness CRM**.
- [ ] Service-center domain content is not mixed into this repo.

## 4) GitHub publication steps

1. Open repository settings in GitHub.
2. Set visibility to **Public**.
3. Confirm with repository name.
4. Create a release note from `docs/CHANGELOG.md`.

## 5) Post-publication validation

- [ ] Local app pages `/docs` and `/blog` open correctly (`/updates` redirects to `/blog`).
- [ ] README badges and links are valid.
- [ ] No broken links in docs.
- [ ] Opened at least one issue template or discussion path for feedback.
