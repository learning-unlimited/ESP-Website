# Formstack Integration

## Security Configuration

### Webhook Handshake Key

The Formstack webhook endpoint (`/formstack/webhook/`) requires a handshake key for security. This prevents unauthorized parties from sending fake form submissions.

**To configure:**

1. Add to your `local_settings.py`:
   ```python
   # Formstack webhook handshake key
   # Get this from your Formstack form settings > Webhooks
   FORMSTACK_HANDSHAKE_KEY = 'your-secret-handshake-key-here'
   ```

2. In your Formstack form settings:
   - Go to **Settings** → **Webhooks**
   - Set the webhook URL: `https://yourdomain.com/formstack/webhook/`
   - Configure the handshake key to match your `FORMSTACK_HANDSHAKE_KEY` setting
   - Include `HandshakeKey` in the webhook payload

**Security Notes:**
- Keep the handshake key secret (don't commit to version control)
- Use a strong, randomly generated key
- If `FORMSTACK_HANDSHAKE_KEY` is not configured, a warning will be logged but webhooks will still be processed (backwards compatibility)
- Once configured, invalid or missing handshake keys will return HTTP 403 Forbidden

**Example Formstack webhook payload:**
```json
{
  "FormID": "12345",
  "UniqueID": "abc123",
  "HandshakeKey": "your-secret-key",
  "field_name": "field_value"
}
```

## References
- [Formstack Webhooks Documentation](https://www.formstack.com/developers/webhooks)
