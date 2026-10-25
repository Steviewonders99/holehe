"""Account checks return unknown when sites change or reject a request."""

import httpx
import pytest

from holehe.core import launch_module, select_sites
from holehe.modules.programing.github import github
from holehe.modules.social_media.twitter import twitter


@pytest.mark.asyncio
@pytest.mark.parametrize("status,body", [
    (403, "blocked"),
    (200, "<html>new signup flow</html>"),
])
async def test_github_changed_signup_flow_is_unknown(status, body):
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(status, text=body)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        out = []
        await github("person@example.test", client, out)
    assert calls == ["/join"]
    assert out[0]["exists"] is None
    assert out[0]["rateLimit"] is True


@pytest.mark.asyncio
async def test_github_requires_explicit_account_availability_response():
    def handler(request):
        if request.url.path == "/join":
            return httpx.Response(200, text=(
                '<auto-check src="/signup_check/email" value="token-1"></auto-check>'
            ))
        assert request.content == b"value=person%40example.test&authenticity_token=token-1"
        return httpx.Response(422, text="Validation failed")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        out = []
        await github("person@example.test", client, out)
    assert out[0]["exists"] is None
    assert out[0]["rateLimit"] is True


@pytest.mark.asyncio
async def test_twitter_network_failure_is_not_a_negative_registration_result():
    def handler(request):
        raise httpx.ReadTimeout("timeout")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        out = []
        await twitter("person@example.test", client, out)
    assert out[0]["exists"] is None
    assert out[0]["rateLimit"] is True


@pytest.mark.asyncio
async def test_module_failure_is_unknown():
    async def github(email, client, out):
        raise RuntimeError("changed endpoint")

    out = []
    await launch_module(github, "person@example.test", None, out)
    assert out[0]["exists"] is None
    assert out[0]["error"] is True


def test_site_selection_rejects_unknown_modules():
    assert select_sites([github, twitter], "twitter") == [twitter]
    with pytest.raises(ValueError, match="unknown site"):
        select_sites([github, twitter], "nonexistent")
