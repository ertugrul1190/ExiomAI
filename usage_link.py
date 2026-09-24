# ---------------------------------------------------------
# USAGE LINK
# ---------------------------------------------------------
#
# Prints the private usage-page link to send the client:
#
#   python usage_link.py https://your-site.com
#
# The token goes after "#", which browsers never send to a
# server: it stays out of logs and referrers. Anyone holding
# the link can see the usage counters (never questions or
# answers), so send it privately. To revoke it, change
# EXIOM_USAGE_TOKEN and restart.
# ---------------------------------------------------------

import os
import sys
from urllib.parse import quote

from dotenv import load_dotenv

import security


def usage_link(site, token):
    return f"{site.rstrip('/')}/usage#{quote(token, safe='')}"


def main(argv):

    load_dotenv()

    if len(argv) != 2 or not argv[1].startswith(("https://", "http://")):
        print("Usage: python usage_link.py https://your-site.com")
        return 2

    token = security.usage_token_from(
        os.getenv("EXIOM_USAGE_TOKEN", "")
    )

    if not token:
        print(
            "EXIOM_USAGE_TOKEN is missing or shorter than 32 "
            "characters. Make one with:\n"
            "  python -c \"import secrets; "
            "print(secrets.token_urlsafe(32))\"\n"
            "set it on the server, restart, then run this again."
        )
        return 1

    print(usage_link(argv[1], token))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
