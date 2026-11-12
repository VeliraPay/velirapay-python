from __future__ import annotations

import unittest
from datetime import UTC, datetime

from velirapay import ApiKeyPermission

from .support import MockTransport, body, client, path_of


class ApiKeyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.http = MockTransport()

    def test_a_key_is_created_with_the_key_itself_shown_once(self) -> None:
        self.http.json(
            {
                "data": {
                    "id": "42",
                    "object": "api_key",
                    "name": "Shop server",
                    "prefix": "vp_live_8Kq2",
                    "key": "vp_live_8Kq2abc",
                    "mode": "live",
                    "permissions": ["charges:read"],
                    "allowed_ips": ["203.0.113.7"],
                    "created_by": "Ada",
                    "last_used_at": None,
                    "created_at": "2026-11-06T09:12:44.000000Z",
                }
            },
            201,
        )

        api_key = client(self.http).api_keys.create(
            {"name": "Shop server", "permissions": ["charges:read"], "allowed_ips": ["203.0.113.7"]},
            idempotency_key="new-key",
        )

        request = self.http.last_request()
        self.assertEqual("POST", request.method)
        self.assertEqual("/v1/api-keys", path_of(request))
        self.assertEqual("new-key", request.headers["Idempotency-Key"])
        self.assertEqual(
            {"name": "Shop server", "permissions": ["charges:read"], "allowed_ips": ["203.0.113.7"]}, body(request)
        )
        self.assertEqual("vp_live_8Kq2abc", api_key.key)
        self.assertEqual("vp_live_8Kq2", api_key.prefix)
        self.assertEqual("live", api_key.mode)
        self.assertEqual(["charges:read"], api_key.permissions)
        self.assertEqual(["203.0.113.7"], api_key.allowed_ips)
        self.assertEqual("Ada", api_key.created_by)
        self.assertIsNone(api_key.last_used_at)
        self.assertEqual(datetime(2026, 11, 6, 9, 12, 44, tzinfo=UTC), api_key.created_at)
        self.assertFalse(api_key.has_full_access())

    def test_permissions_are_sent_as_their_values_whether_given_as_members_or_strings(self) -> None:
        self.http.json(
            {
                "data": {
                    "id": "43",
                    "object": "api_key",
                    "name": "Books",
                    "prefix": "vp_live_9Lr3",
                    "key": "vp_live_9Lr3abc",
                    "mode": "live",
                    "permissions": ["payouts:read", "account:write"],
                    "allowed_ips": None,
                }
            },
            201,
        )

        client(self.http).api_keys.create(
            {"name": "Books", "permissions": [ApiKeyPermission.PAYOUTS_READ, "account:write"]}
        )

        self.assertEqual(
            {"name": "Books", "permissions": ["payouts:read", "account:write"]}, body(self.http.last_request())
        )

    def test_keys_are_listed_changed_and_revoked(self) -> None:
        (
            self.http.json(
                {
                    "data": [
                        {
                            "id": "7",
                            "object": "api_key",
                            "name": "Old",
                            "prefix": "vp_live_aaaa",
                            "mode": "live",
                            "permissions": None,
                            "allowed_ips": None,
                        }
                    ],
                    "meta": {"current_page": 1, "last_page": 1, "per_page": 25, "total": 1},
                }
            )
            .json(
                {
                    "data": {
                        "id": "7",
                        "object": "api_key",
                        "name": "Reader",
                        "prefix": "vp_live_aaaa",
                        "mode": "live",
                        "permissions": ["charges:read"],
                        "allowed_ips": None,
                    }
                }
            )
            .empty()
        )
        velirapay = client(self.http)

        listed = velirapay.api_keys.list().data[0]

        self.assertEqual("/v1/api-keys", path_of(self.http.last_request()))
        self.assertIsNone(listed.key)
        self.assertTrue(listed.has_full_access())

        velirapay.api_keys.update("7", {"name": "Reader", "permissions": ["charges:read"]})

        self.assertEqual("PATCH", self.http.last_request().method)
        self.assertEqual("/v1/api-keys/7", path_of(self.http.last_request()))
        self.assertEqual({"name": "Reader", "permissions": ["charges:read"]}, body(self.http.last_request()))

        velirapay.api_keys.revoke("7")

        self.assertEqual("DELETE", self.http.last_request().method)
        self.assertEqual("/v1/api-keys/7", path_of(self.http.last_request()))


class MemberTest(unittest.TestCase):
    def setUp(self) -> None:
        self.http = MockTransport()

    def test_members_are_listed_changed_and_removed(self) -> None:
        (
            self.http.json(
                {
                    "data": [
                        {
                            "id": "3",
                            "object": "member",
                            "name": "Ada",
                            "email": "ada@example.com",
                            "role": "admin",
                            "joined_at": "2026-10-01T08:00:00.000000Z",
                        }
                    ],
                    "meta": {"current_page": 1, "last_page": 1, "per_page": 25, "total": 1},
                }
            )
            .json(
                {"data": {"id": "3", "object": "member", "name": "Ada", "email": "ada@example.com", "role": "finance"}}
            )
            .empty()
        )
        velirapay = client(self.http)

        member = velirapay.members.list().data[0]

        self.assertEqual("/v1/members", path_of(self.http.last_request()))
        self.assertEqual("3", member.id)
        self.assertEqual("Ada", member.name)
        self.assertEqual("ada@example.com", member.email)
        self.assertEqual("admin", member.role)
        self.assertEqual(datetime(2026, 10, 1, 8, 0, tzinfo=UTC), member.joined_at)

        self.assertEqual("finance", velirapay.members.update("3", {"role": "finance"}).role)
        self.assertEqual({"role": "finance"}, body(self.http.last_request()))

        velirapay.members.remove("3")

        self.assertEqual("DELETE", self.http.last_request().method)
        self.assertEqual("/v1/members/3", path_of(self.http.last_request()))

    def test_a_member_without_a_role_reads_as_none(self) -> None:
        self.http.json(
            {"data": [{"id": "4", "object": "member", "name": "Grace", "email": "grace@example.com", "role": None}]}
        )

        self.assertIsNone(client(self.http).members.list().data[0].role)

    def test_invitations_are_sent_listed_and_canceled(self) -> None:
        invitation = {
            "id": "9",
            "object": "invitation",
            "email": "grace@example.com",
            "role": "admin",
            "invited_by": "Ada",
            "expired": False,
            "expires_at": "2026-11-09T09:00:00.000000Z",
        }
        (
            self.http.json({"data": invitation}, 201)
            .json({"data": [invitation], "meta": {"current_page": 1, "last_page": 1, "per_page": 25, "total": 1}})
            .empty()
        )
        velirapay = client(self.http)

        sent = velirapay.invitations.create({"email": "grace@example.com", "role": "admin"})

        self.assertEqual("POST", self.http.last_request().method)
        self.assertEqual("/v1/invitations", path_of(self.http.last_request()))
        self.assertEqual({"email": "grace@example.com", "role": "admin"}, body(self.http.last_request()))
        self.assertEqual("9", sent.id)
        self.assertEqual("admin", sent.role)
        self.assertEqual("Ada", sent.invited_by)
        self.assertFalse(sent.expired)
        self.assertEqual(datetime(2026, 11, 9, 9, 0, tzinfo=UTC), sent.expires_at)

        self.assertEqual("grace@example.com", velirapay.invitations.list().data[0].email)

        velirapay.invitations.cancel("9")

        self.assertEqual("DELETE", self.http.last_request().method)
        self.assertEqual("/v1/invitations/9", path_of(self.http.last_request()))


if __name__ == "__main__":
    unittest.main()
