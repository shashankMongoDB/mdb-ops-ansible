# Deployment Checklist

## Pre-Deployment

### Environment Setup
- [ ] Node.js 18+ installed
- [ ] npm or yarn installed
- [ ] Git repository initialized
- [ ] `.env.local` configured with correct values
- [ ] `.env.local` added to `.gitignore`

### Configuration Review
- [ ] `NEXT_PUBLIC_CONTROL_PLANE_API_BASE_URL` points to production API
- [ ] `MCP_MONGODB_URI` uses production credentials (if applicable)
- [ ] `NEXT_PUBLIC_ENVIRONMENT` set to appropriate value (PROD/STAGING)
- [ ] MongoDB credentials are read-only (if used)

### Code Quality
- [ ] Run `npm run type-check` - no TypeScript errors
- [ ] Run `npm run lint` - no ESLint errors
- [ ] All components render without errors
- [ ] No console errors in browser

### Testing
- [ ] Test tenant creation
- [ ] Test deployment creation (Standalone)
- [ ] Test deployment creation (ReplicaSet)
- [ ] Test scale operation with validation
- [ ] Test version upgrade with downgrade prevention
- [ ] Test shutdown operation with confirmation
- [ ] Test start operation
- [ ] Test restart operation
- [ ] Test Prometheus enable/disable
- [ ] Verify connection info display and copy functionality
- [ ] Test auto-refresh (wait 15 seconds)
- [ ] Test manual refresh button
- [ ] Test error handling (disconnect API, test error responses)
- [ ] Test all toast notifications appear correctly
- [ ] Verify all modals open and close properly
- [ ] Test navigation (all routes work)

### Cross-Browser Testing
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)

### Mobile Responsiveness
- [ ] Test on tablet (768px width)
- [ ] Test on mobile (375px width)
- [ ] Verify sidebar navigation works on mobile

## Deployment

### Build
- [ ] Run `npm run build` successfully
- [ ] No build errors or warnings
- [ ] Check build output size
- [ ] Test production build locally (`npm start`)

### Security
- [ ] Sensitive data not hardcoded in source
- [ ] `.env.local` not committed to Git
- [ ] API credentials stored securely
- [ ] HTTPS enabled in production
- [ ] CORS configured on API server
- [ ] Security headers configured
- [ ] Rate limiting considered
- [ ] Authentication/authorization plan in place

### Infrastructure
- [ ] Server/hosting platform ready
- [ ] Domain name configured (if applicable)
- [ ] SSL certificate installed
- [ ] Load balancer configured (if applicable)
- [ ] CDN configured (if applicable)
- [ ] Firewall rules configured
- [ ] Monitoring tools set up

### Database
- [ ] MongoDB control plane database accessible
- [ ] Connection string tested
- [ ] Read-only user created (if applicable)
- [ ] Network access configured
- [ ] Backup strategy in place

## Post-Deployment

### Smoke Tests
- [ ] Homepage loads successfully
- [ ] Can create a test tenant
- [ ] Can create a test deployment
- [ ] Status updates are visible
- [ ] Connection info displays correctly
- [ ] Prometheus toggle works
- [ ] All lifecycle operations work

### Performance
- [ ] Page load times acceptable (< 3s)
- [ ] API response times acceptable
- [ ] Auto-refresh doesn't cause performance issues
- [ ] No memory leaks during prolonged use

### Monitoring
- [ ] Application logs accessible
- [ ] Error tracking configured (e.g., Sentry)
- [ ] Uptime monitoring configured
- [ ] Performance monitoring configured
- [ ] API health checks configured

### Documentation
- [ ] README.md updated with production URLs
- [ ] Deployment guide documented
- [ ] Operations runbook created
- [ ] User guide available
- [ ] API documentation accessible

### Backup & Recovery
- [ ] Database backup strategy tested
- [ ] Application rollback plan documented
- [ ] Disaster recovery plan in place

### Team Handoff
- [ ] Operations team trained
- [ ] Support team notified
- [ ] Documentation shared
- [ ] Access credentials provided securely
- [ ] Escalation procedures documented

## Production Monitoring (First Week)

### Daily Checks
- [ ] Check error logs
- [ ] Review API response times
- [ ] Monitor user activity
- [ ] Check for failed requests
- [ ] Review auto-refresh performance

### Weekly Checks
- [ ] Review user feedback
- [ ] Check for UI issues
- [ ] Monitor database performance
- [ ] Review security logs
- [ ] Check for outdated dependencies

## Troubleshooting Guide

### Issue: Can't connect to API
**Symptoms**: "Failed to load tenants" error on homepage
**Solution**:
1. Verify API URL in environment variables
2. Check API server is running
3. Test API directly with curl
4. Check CORS configuration
5. Review network/firewall rules

### Issue: Status not updating
**Symptoms**: Deployment status stuck, doesn't refresh
**Solution**:
1. Check auto-refresh timer (should update every 15s)
2. Click manual refresh button
3. Check API response contains status field
4. Review browser console for errors
5. Check API logs for errors

### Issue: Toast notifications not appearing
**Symptoms**: Actions complete but no feedback
**Solution**:
1. Check browser console for JavaScript errors
2. Verify ToastProvider wraps components
3. Check z-index conflicts with LeafyGreen components
4. Test in different browser

### Issue: Modals won't close
**Symptoms**: Modal stays open after action
**Solution**:
1. Check for errors in form submission
2. Verify onClose handler is called
3. Check for loading state stuck true
4. Clear browser cache
5. Review modal state management

### Issue: Build fails
**Symptoms**: `npm run build` exits with error
**Solution**:
1. Run `npm run type-check` to find TypeScript errors
2. Check for missing dependencies
3. Clear .next folder: `rm -rf .next`
4. Delete node_modules and reinstall: `rm -rf node_modules && npm install`
5. Check Node.js version (should be 18+)

## Rollback Procedure

If critical issues are discovered post-deployment:

1. **Immediate**: Switch to previous version
   ```bash
   git checkout <previous-tag>
   npm install
   npm run build
   npm start
   ```

2. **Communicate**: Notify users and team of rollback

3. **Investigate**: Review logs, errors, and user reports

4. **Fix**: Create hotfix branch
   ```bash
   git checkout -b hotfix/issue-description
   # Make fixes
   git commit -m "Fix: issue description"
   ```

5. **Test**: Thoroughly test hotfix in staging

6. **Deploy**: Deploy hotfix to production

7. **Verify**: Run smoke tests again

## Support Contacts

**Application Issues**:
- Contact: [Your Team]
- Email: [support@example.com]
- Slack: [#atlasforge-support]

**API Issues**:
- Contact: [API Team]
- Email: [api-support@example.com]

**Infrastructure Issues**:
- Contact: [DevOps Team]
- Email: [devops@example.com]

## Success Criteria

Deployment is considered successful when:
- [ ] All smoke tests pass
- [ ] No critical errors in logs
- [ ] Users can create tenants
- [ ] Users can create deployments
- [ ] Users can perform lifecycle operations
- [ ] Status updates work correctly
- [ ] No performance degradation
- [ ] All monitoring alerts are green

---

**Deployment Date**: _____________

**Deployed By**: _____________

**Version**: 0.1.0

**Sign-off**: _____________
