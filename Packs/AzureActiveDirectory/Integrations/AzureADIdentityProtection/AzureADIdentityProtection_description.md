Note: This is a beta Integration, which lets you implement and test pre-release software. Since the integration is beta, it might contain bugs. Updates to the integration during the beta phase might include non-backward compatible features. We appreciate your feedback on the quality and usability of the integration to help us identify issues, fix them, and continually improve.

The API this integration uses is defined as beta by Microsoft.

---

In order to connect to the Azure Active Directory - Identity Protection using either Cortex XSOAR Azure App or the Self-Deployed Azure App:
1. Fill in the required parameters.
2. Make sure to provide both the `IdentityRiskEvent.Read.All` permission and `IdentityRiskyUser.ReadWrite.All`. The latter is used to update user status, for example by calling the `!azure-ad-identity-protection-risky-user-confirm-compromised` command.
3. Run the ***!azure-ad-auth-start*** command. 
4. Follow the instructions that appear.
5. Run the ***!azure-ad-auth-complete*** command.

At the end of the process, a confirmation message is shown. 