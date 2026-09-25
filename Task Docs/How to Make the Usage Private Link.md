# EXIOM AI — How to Make the Usage Private Link

A step-by-step guide to making the private link that opens the
usage page (`/usage`) with no typing. The link looks like
`https://<site>/usage#<token>`. The feature itself is described
in Task 15 (15.4). The pieces involved are `usage_link.py`,
`templates/usage.html` and the `/usage` and `/api/usage`
routes in `app.py`.


## 1. Make a usage token

The token must be at least 32 characters, or the usage page
stays off (`security.usage_token_from`). Generate one:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

This prints about 43 random characters. Keep it somewhere
safe, like a password manager. Anyone who has it can see the
usage counters.


## 2. Set it on the server

Set `EXIOM_USAGE_TOKEN` to that value wherever the app runs:

* **Production:** add it as a platform secret, as with
  `OPENAI_API_KEY`. Do not put it in a committed file.
* **Locally:** add it to `.env` (gitignored):

  ```
  EXIOM_USAGE_TOKEN=<the token>
  ```


## 3. Restart the app

The token is read once at startup, so restart the app, or
redeploy it. Every worker has to pick up the new value.


## 4. Check that the page is on

Open `https://<site>/usage`. It should show a "Usage token"
box.

* **404 (`not_enabled`):** the token is missing or shorter
  than 32 characters. The server log says
  `EXIOM usage endpoint disabled: ...` when it is too short.
  Go back to step 2.


## 5. Print the link

From the `XEQM-Hub` folder, using the project's virtualenv:

```bash
.venv/bin/python usage_link.py https://<site>
```

The script reads `EXIOM_USAGE_TOKEN` from `.env` or the
environment and prints the link:

```
https://<site>/usage#<token>
```

If the token only exists as a platform secret and not in your
local `.env`, pass it for this one command:

```bash
EXIOM_USAGE_TOKEN='<the token>' .venv/bin/python usage_link.py https://<site>
```

The token in the link must be the same one the server has.
Otherwise the page says "That token wasn't accepted."

Errors:

* `Usage: python usage_link.py https://your-site.com`: the
  site address is missing, or it doesn't start with
  `https://` or `http://`.
* `EXIOM_USAGE_TOKEN is missing or shorter than 32
  characters`: the token isn't set where the script runs.
  See step 1.


## 6. Test the link

Open the link in a private window. The page should load the
report straight away, with no box to type in. If it says "That
token wasn't accepted.", the token in the link and the token on
the server don't match.


## 7. Send it privately

Send the link to the client over a private channel, like a
direct message or email, never a public channel or a ticket.
They can bookmark it and open it any time.

Why it is safe to put the token in a link: the token is after
`#`, and browsers never send that part to a server. It stays
out of the access log, proxies, Cloudflare and referrers. The
page reads it in the browser and sends it in the
`X-Usage-Token` header. The page shows counters only (requests,
tokens, estimated cost, caches), never questions or answers.


## 8. Revoke or rotate the link

To revoke the link, change `EXIOM_USAGE_TOKEN` (step 1 and
step 2) and restart. The old link stops working at once. To
give access again, repeat steps 5 to 7 with the new token.

To turn the usage page off completely, remove
`EXIOM_USAGE_TOKEN` and restart. `/usage` and `/api/usage`
then return 404.


## Quick reference

```bash
# 1. Make a token
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 2–3. Set EXIOM_USAGE_TOKEN on the server, then restart

# 5. Print the link
.venv/bin/python usage_link.py https://<site>
```
