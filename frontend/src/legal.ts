export const TERMS_OF_SERVICE = `Smart Market Watch Terms of Service

Last updated: 4 September 2026

1. What this product is
Smart Market Watch is a delayed-quote monitoring tool. It remembers the last price you acknowledged, scores later moves against that name’s own volatility and volume, and explains why a move may deserve attention. It is not a broker, not an exchange, and not investment, tax, or legal advice.

2. Your account
You must give a real email you control and keep your password private. You are responsible for activity on your account. We may suspend access if we detect abuse, scraping that violates market-data terms, or attempts to break the service.

3. Market data
Quotes may be delayed, stale, or unavailable. Yahoo Finance and other vendors can fail or lag the tape. Do not trade solely on what you see here. Freshness labels (LIVE, DELAYED, STALE, UNAVAILABLE) are informational, not a guarantee. Mock quotes exist only when MARKET_DATA_PROVIDER=mock.

4. Intelligence scores
Significance scores (conservative / balanced / sensitive) are heuristics: a volatility-standardized move plus session-scaled volume and a short-vs-longer realized-vol comparison. They can miss important moves and can flag noise.

5. Acceptable use
Do not use the service to manipulate markets, harass others, reverse-engineer vendor feeds for redistribution, or overload the API.

6. Availability
Production requires a persistent database (Postgres). Local development may use SQLite. Accounts are stored only on the server; the browser is not a backup of password hashes.

7. Limitation of liability
The service is provided as-is. We are not liable for trading losses, missed alerts, or data gaps.

8. Contact
Questions about these terms: use the email on your profile, or the operator who deployed this instance.`

export const PRIVACY_POLICY = `Smart Market Watch Privacy Policy

Last updated: 4 September 2026

1. What we collect
When you sign up we store your name, email, password hash (not your raw password), timezone, watchlists, last-seen prices, and the sensitivity / in-app alert preferences you set. We do not ask for brokerage account numbers or government IDs.

2. How we use it
We use this data only to run the product: authenticate you, remember acknowledged baselines, score changes, and show your profile.

3. Market data
Ticker searches and quotes are requested from delayed public market-data endpoints (Yahoo). Those requests include the symbols you look up, not your name.

4. Cookies and storage
We store a session token in local storage. Signing out clears it. Password hashes never leave the server.

5. Sharing
We do not sell your personal data. Hosting providers (for example Vercel) may process requests as infrastructure. Password-reset email is sent only when the operator has configured the production email provider.

6. Retention
You can stop using the product at any time. Without a persistent DATABASE_URL, a local SQLite file is development-only and is not a production store.

7. Your choices
You can update name, timezone, and intelligence preferences in Profile, Settings, and Preferences.

8. Contact
Privacy questions: the email address on your account is the identifier we hold for you.`
