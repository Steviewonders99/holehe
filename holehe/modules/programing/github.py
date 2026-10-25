"""GitHub signup probe. Unknown responses must never become account claims."""

from bs4 import BeautifulSoup


async def github(email, client, out):
    result = {
        "name": "github", "domain": "github.com", "method": "register",
        "frequent_rate_limit": False, "rateLimit": True, "exists": None,
        "emailrecovery": None, "phoneNumber": None, "others": None,
    }
    try:
        landing = await client.get("https://github.com/join")
        if landing.status_code != 200:
            out.append(result)
            return
        field = BeautifulSoup(landing.text, "html.parser").find(
            "auto-check", attrs={"src": "/signup_check/email"}
        )
        token = field.get("value") if field else None
        if not isinstance(token, str) or not token:
            out.append(result)
            return
        response = await client.post(
            "https://github.com/signup_check/email",
            data={"value": email, "authenticity_token": token},
        )
        body = response.text.casefold()
        if response.status_code == 422 and "email" in body and (
            "already in use" in body or "already taken" in body
        ):
            result.update(rateLimit=False, exists=True)
        elif response.status_code == 200 and "email" in body and "available" in body:
            result.update(rateLimit=False, exists=False)
    except Exception:
        # A changed page, challenge, timeout or parser failure is inconclusive.
        pass
    out.append(result)
