# apartments-search

## Mail setup

Put mail credentials in `.env` for local runs. The app loads that file automatically from the project root.

For GitHub Actions, store the same values in repository secrets and inject them as environment variables in the workflow:

```yaml
env:
	MAIL_SMTP_HOST: ${{ secrets.MAIL_SMTP_HOST }}
	MAIL_SMTP_PORT: ${{ secrets.MAIL_SMTP_PORT }}
	MAIL_USERNAME: ${{ secrets.MAIL_USERNAME }}
	MAIL_PASSWORD: ${{ secrets.MAIL_PASSWORD }}
	MAIL_FROM_ADDRESS: ${{ secrets.MAIL_FROM_ADDRESS }}
	MAIL_TO_ADDRESS: ${{ secrets.MAIL_TO_ADDRESS }}
	MAIL_USE_TLS: ${{ secrets.MAIL_USE_TLS }}
```
