# Release Process

## Versioning

HubEx follows [Semantic Versioning](https://semver.org/):
- **MAJOR** (v2.0.0): Breaking API changes
- **MINOR** (v0.2.0): New features, backward compatible
- **PATCH** (v0.1.1): Bug fixes, security patches

## Pre-Release Checklist

```
[ ] All tests pass (build, unit, E2E)
[ ] CHANGELOG.md updated with new version
[ ] No console errors on all pages (manual check)
[ ] Security audit passed (OWASP Top 10)
[ ] Documentation updated for new features
[ ] .env.example has all new variables
[ ] Docker images build successfully
[ ] Backup procedure tested
```

## Release Steps

### 1. Version Bump
```bash
# Update version in:
# - app/main.py (version string)
# - package.json (frontend)
# - CHANGELOG.md (new section)
```

### 2. Tag & Release
```bash
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin v0.1.0
```

### 3. Docker Build
```bash
docker build -t hubex/backend:v0.1.0 .
docker build -t hubex/frontend:v0.1.0 ./frontend
docker push hubex/backend:v0.1.0
docker push hubex/frontend:v0.1.0
```

### 4. GitHub Release
- Create release from tag on GitHub
- Attach CHANGELOG section as release notes
- Link to documentation

### 5. Announce
- GitHub Discussions: Announcement post
- Discord: #announcements channel
- Landing Page: Update version number

## Deprecation Policy

- Features deprecated in MINOR versions (v0.2.0)
- Deprecation warning in API response headers + documentation
- 6 months notice before removal
- Removed only in MAJOR versions (v1.0.0)
- Deprecated endpoints return `Sunset` header with removal date

## Hotfix Process

For critical security fixes:
1. Fix on main branch
2. Cherry-pick to release branch
3. Bump PATCH version
4. Release immediately (skip normal cycle)
5. Post-mortem within 48h
