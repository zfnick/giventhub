import base64
import unittest
from unittest.mock import MagicMock, patch

from git_eventhub_agent import workspace_tools as wt
from git_eventhub_agent.agent import root_agent


class WorkflowSmokeTest(unittest.TestCase):
    def setUp(self) -> None:
        wt._WORKSPACE_OAUTH_TOKEN.set("")

    def test_root_agent_loads_workspace_hierarchy(self) -> None:
        self.assertEqual(root_agent.name, "workspace_coordinator")
        self.assertEqual(root_agent.model, "gemini-2.5-flash")
        self.assertEqual(
            [agent.name for agent in root_agent.sub_agents],
            [
                "drive_agent",
                "docs_agent",
                "forms_agent",
                "sheets_agent",
                "slides_agent",
                "gmail_agent",
                "calendar_agent",
                "chat_meet_agent",
                "productivity_agent",
            ],
        )

    def test_root_agent_requires_oauth_token_tool_first(self) -> None:
        tool_names = {tool.__name__ for tool in root_agent.tools if hasattr(tool, "__name__")}

        self.assertEqual(tool_names, {"require_oauth_token", "draft_workspace_actions"})
        self.assertIn("AUTH FIRST", root_agent.instruction)

    def test_workspace_tool_lists_are_unique(self) -> None:
        tool_names = [tool.__name__ for tool in wt.WORKSPACE_TOOLS]

        self.assertEqual(len(tool_names), len(set(tool_names)))
        self.assertIn("require_oauth_token", tool_names)
        self.assertIn("create_drive_folder", tool_names)
        self.assertIn("upload_drive_file", tool_names)
        self.assertIn("upload_drive_files", tool_names)
        self.assertIn("create_google_doc", tool_names)
        self.assertIn("create_google_form", tool_names)
        self.assertIn("create_google_sheet", tool_names)
        self.assertIn("create_gmail_draft", tool_names)
        self.assertIn("create_calendar_draft", tool_names)
        self.assertIn("create_chat_message", tool_names)
        self.assertIn("create_notebooklm_notebook", tool_names)
        self.assertIn("plan_google_vids_action", tool_names)

    def test_workspace_tools_require_oauth_before_planning(self) -> None:
        with self.assertRaisesRegex(ValueError, "oauth_token is required"):
            wt.create_drive_folder("Demo Workspace")

        with self.assertRaisesRegex(ValueError, "oauth_token is required"):
            wt.draft_workspace_actions("[]")

    def test_oauth_token_enables_planned_workspace_calls(self) -> None:
        token_result = wt.require_oauth_token("ya29.test-token")
        planned_calls = [
            wt.create_drive_folder("Demo Workspace"),
            wt.upload_drive_file("playbook.json", "e30=", mime_type="application/json"),
            wt.upload_drive_files(
                '[{"file_name": "rubric.txt", "content_base64": "UnVicmlj"}]',
                folder_id="folder-123",
            ),
            wt.create_google_doc("Judging Rubric", "Rubric body"),
            wt.create_google_form("Registration", questions_json='["Name", "Email"]'),
            wt.create_google_sheet("CRM", headers_json='["Name", "Status"]'),
            wt.create_google_slide_deck("Event Deck"),
            wt.create_gmail_draft("founder@example.com", "Follow up", "Hello"),
            wt.create_calendar_draft(
                "Follow-up",
                "2026-05-16T09:00:00+08:00",
                "2026-05-16T09:30:00+08:00",
                attendee_emails_json='["founder@example.com"]',
                timezone="Asia/Kuala_Lumpur",
            ),
            wt.create_task_list("Event Tasks"),
            wt.create_chat_space("Event War Room"),
            wt.create_meet_space(),
            wt.create_keep_note("Reminder", "Follow up with mentors"),
            wt.create_notebooklm_notebook("123456789", "Event Research"),
            wt.call_appsheet_table_action("app-id", "Events", "Find"),
            wt.plan_google_vids_action("create_video"),
            wt.plan_google_sites_action("create_site"),
        ]

        self.assertEqual(token_result["operation"], "require_oauth_token")
        self.assertTrue(token_result["oauth_token_registered"])
        self.assertNotIn("ya29.test-token", str(token_result))
        self.assertTrue(all(call["status"] == "planned" for call in planned_calls))
        self.assertTrue(all(call["requires_approval"] for call in planned_calls))
        self.assertTrue(all(not call["executed"] for call in planned_calls))

    def test_upload_drive_file_plans_without_exposing_base64(self) -> None:
        wt.require_oauth_token("ya29.test-token")

        planned = wt.upload_drive_file(
            "playbook.json",
            base64.b64encode(b'{"title": "Demo"}').decode(),
            folder_id="folder-123",
        )

        self.assertEqual(planned["operation"], "upload_drive_file")
        self.assertEqual(planned["payload"]["mime_type"], "application/json")
        self.assertEqual(planned["payload"]["folder_id"], "folder-123")
        self.assertNotIn("content_base64", planned["payload"])
        self.assertTrue(planned["payload"]["has_content"])

    def test_upload_drive_files_plans_batch_uploads(self) -> None:
        wt.require_oauth_token("ya29.test-token")

        planned = wt.upload_drive_files(
            '[{"file_name": "one.txt", "content_base64": "T25l"},'
            ' {"file_name": "two.csv", "content_base64": "YSxi"}]',
            folder_id="folder-123",
        )

        self.assertEqual(planned["operation"], "upload_drive_files")
        self.assertEqual(planned["payload"]["file_count"], 2)
        self.assertEqual(planned["payload"]["files"][0]["mime_type"], "text/plain")
        self.assertEqual(planned["payload"]["files"][1]["mime_type"], "text/csv")
        self.assertNotIn("content_base64", planned["payload"]["files"][0])

    def test_upload_drive_file_executes_drive_upload(self) -> None:
        wt.require_oauth_token("ya29.test-token")
        drive_service = MagicMock()
        drive_service.files.return_value.create.return_value.execute.return_value = {
            "id": "file-123",
            "name": "playbook.json",
            "mimeType": "application/json",
            "webViewLink": "https://drive.google.com/file/d/file-123/view",
            "parents": ["folder-123"],
        }

        with patch("git_eventhub_agent.workspace_tools._google_service", return_value=drive_service):
            result = wt.upload_drive_file(
                "playbook.json",
                base64.b64encode(b'{"title": "Demo"}').decode(),
                folder_id="folder-123",
                execute=True,
            )

        _, kwargs = drive_service.files.return_value.create.call_args
        self.assertEqual(kwargs["body"]["name"], "playbook.json")
        self.assertEqual(kwargs["body"]["parents"], ["folder-123"])
        self.assertIn("media_body", kwargs)
        self.assertTrue(result["executed"])
        self.assertEqual(result["resource_id"], "file-123")

    def test_google_service_uses_registered_oauth_token(self) -> None:
        wt.require_oauth_token("ya29.test-token")

        with patch("git_eventhub_agent.workspace_tools.build") as build:
            wt._google_service("drive", "v3")

        _, kwargs = build.call_args
        self.assertEqual(kwargs["credentials"].token, "ya29.test-token")

    def test_registered_placeholder_preserves_existing_oauth_token(self) -> None:
        wt.require_oauth_token("ya29.real-token")
        token_result = wt.require_oauth_token("<registered>")

        with patch("git_eventhub_agent.workspace_tools.build") as build:
            wt._google_service("calendar", "v3")

        _, kwargs = build.call_args
        self.assertTrue(token_result["oauth_token_registered"])
        self.assertEqual(kwargs["credentials"].token, "ya29.real-token")

    def test_oauth_registration_strips_accidental_bearer_prefix(self) -> None:
        wt.require_oauth_token("Bearer ya29.real-token")

        with patch("git_eventhub_agent.workspace_tools.build") as build:
            wt._google_service("calendar", "v3")

        _, kwargs = build.call_args
        self.assertEqual(kwargs["credentials"].token, "ya29.real-token")

    def test_google_service_fails_without_oauth_token(self) -> None:
        with self.assertRaisesRegex(ValueError, "oauth_token is required"):
            wt._google_service("drive", "v3")


if __name__ == "__main__":
    unittest.main()
