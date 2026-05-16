import unittest
from unittest.mock import MagicMock, patch

from git_eventhub_agent import workspace_tools as wt


class AgentUseCaseTest(unittest.TestCase):
    def setUp(self) -> None:
        wt._WORKSPACE_OAUTH_TOKEN.set("")
        wt._WORKSPACE_FILE_STORE.set({})
        wt.require_oauth_token("ya29.test-token")

    def test_calendar_summary_use_case_lists_may_events(self) -> None:
        calendar_service = MagicMock()
        calendar_service.events.return_value.list.return_value.execute.return_value = {
            "items": [
                {
                    "id": "event-1",
                    "summary": "Mentor matching session",
                    "start": {"dateTime": "2026-05-07T10:00:00Z"},
                },
                {
                    "id": "event-2",
                    "summary": "Climate Tech demo day",
                    "start": {"dateTime": "2026-05-21T16:00:00Z"},
                },
            ]
        }

        with patch("git_eventhub_agent.workspace_tools._google_service", return_value=calendar_service):
            result = wt.list_calendar_events(
                time_min="2026-05-01T00:00:00Z",
                time_max="2026-05-31T23:59:59Z",
                execute=True,
            )

        _, kwargs = calendar_service.events.return_value.list.call_args
        self.assertEqual(result["operation"], "list_calendar_events")
        self.assertTrue(result["executed"])
        self.assertEqual([event["summary"] for event in result["events"]], [
            "Mentor matching session",
            "Climate Tech demo day",
        ])
        self.assertEqual(kwargs["calendarId"], "primary")
        self.assertEqual(kwargs["timeMin"], "2026-05-01T00:00:00Z")
        self.assertEqual(kwargs["timeMax"], "2026-05-31T23:59:59Z")
        self.assertTrue(kwargs["singleEvents"])

    def test_smart_fork_use_case_creates_workspace_assets_in_one_folder(self) -> None:
        drive_service = MagicMock()
        docs_service = MagicMock()
        forms_service = MagicMock()
        sheets_service = MagicMock()

        drive_service.files.return_value.create.return_value.execute.side_effect = [
            {"id": "folder-123", "name": "Climate Hack Workspace"},
            {"id": "doc-123", "name": "Judging Rubric"},
            {"id": "sheet-123", "name": "Participant CRM"},
        ]
        drive_service.files.return_value.get.return_value.execute.return_value = {"parents": ["root"]}
        drive_service.files.return_value.update.return_value.execute.return_value = {
            "id": "form-123",
            "parents": ["folder-123"],
        }
        docs_service.documents.return_value.batchUpdate.return_value.execute.return_value = {
            "replies": [{}]
        }
        forms_service.forms.return_value.create.return_value.execute.return_value = {"formId": "form-123"}
        forms_service.forms.return_value.batchUpdate.return_value.execute.return_value = {
            "replies": [{}, {}, {}]
        }
        sheets_service.spreadsheets.return_value.values.return_value.append.return_value.execute.return_value = {
            "updates": {"updatedRange": "A1:C1"}
        }

        def service_for(api_name: str, version: str):
            if api_name == "drive":
                return drive_service
            if api_name == "docs":
                return docs_service
            if api_name == "forms":
                return forms_service
            if api_name == "sheets":
                return sheets_service
            raise AssertionError(f"Unexpected service: {api_name}/{version}")

        with patch("git_eventhub_agent.workspace_tools._google_service", side_effect=service_for):
            folder = wt.create_drive_folder("Climate Hack Workspace", execute=True)
            doc = wt.create_google_doc(
                "Judging Rubric",
                "Score projects on impact, feasibility, and ecosystem value.",
                folder_id=folder["resource_id"],
                execute=True,
            )
            form = wt.create_google_form(
                "Climate Hack Registration",
                questions_json='["Name", "Email", "What are you building?"]',
                folder_id=folder["resource_id"],
                execute=True,
            )
            sheet = wt.create_google_sheet(
                "Participant CRM",
                headers_json='["Name", "Email", "Track"]',
                folder_id=folder["resource_id"],
                execute=True,
            )

        self.assertEqual(folder["resource_id"], "folder-123")
        self.assertEqual(doc["resource_id"], "doc-123")
        self.assertEqual(form["resource_id"], "form-123")
        self.assertEqual(sheet["resource_id"], "sheet-123")
        self.assertEqual(form["form_title"], "Climate Hack Registration")
        self.assertTrue(all(item["executed"] for item in [folder, doc, form, sheet]))

        create_calls = drive_service.files.return_value.create.call_args_list
        self.assertEqual(create_calls[1].kwargs["body"]["parents"], ["folder-123"])
        self.assertEqual(create_calls[2].kwargs["body"]["parents"], ["folder-123"])
        docs_service.documents.return_value.batchUpdate.assert_called_once()
        forms_service.forms.return_value.batchUpdate.assert_called_once()
        sheets_service.spreadsheets.return_value.values.return_value.append.assert_called_once()

    def test_form_read_use_case_accepts_exact_title(self) -> None:
        drive_service = MagicMock()
        forms_service = MagicMock()
        drive_service.files.return_value.list.return_value.execute.return_value = {
            "files": [
                {
                    "id": "form-123",
                    "name": "GIEH CRUD Test Registration",
                    "mimeType": wt.GOOGLE_FORM_MIME_TYPE,
                }
            ]
        }
        forms_service.forms.return_value.get.return_value.execute.return_value = {
            "formId": "form-123",
            "info": {"title": "GIEH CRUD Test Registration"},
        }

        def service_for(api_name: str, version: str):
            if api_name == "drive":
                return drive_service
            if api_name == "forms":
                return forms_service
            raise AssertionError(f"Unexpected service: {api_name}/{version}")

        with patch("git_eventhub_agent.workspace_tools._google_service", side_effect=service_for):
            result = wt.get_google_form("GIEH CRUD Test Registration", execute=True)

        _, list_kwargs = drive_service.files.return_value.list.call_args
        _, get_kwargs = forms_service.forms.return_value.get.call_args
        self.assertEqual(result["resource_id"], "form-123")
        self.assertEqual(result["form"]["info"]["title"], "GIEH CRUD Test Registration")
        self.assertIn("name = 'GIEH CRUD Test Registration'", list_kwargs["q"])
        self.assertEqual(get_kwargs["formId"], "form-123")

    def test_gmail_list_use_case_returns_metadata_not_only_ids(self) -> None:
        gmail_service = MagicMock()
        gmail_service.users.return_value.messages.return_value.list.return_value.execute.return_value = {
            "messages": [{"id": "msg-1", "threadId": "thread-1"}]
        }

        # Mock the batch API: when batch.execute() is called, invoke the
        # callback registered via new_batch_http_request(callback=...) with
        # the metadata response for each message.
        msg_response = {
            "id": "msg-1",
            "threadId": "thread-1",
            "snippet": "Hackathon mentor intro",
            "payload": {
                "headers": [
                    {"name": "From", "value": "mentor@example.com"},
                    {"name": "Subject", "value": "Hackathon mentoring"},
                    {"name": "Date", "value": "Sun, 17 May 2026 09:00:00 +0800"},
                ]
            },
        }

        def fake_batch_factory(callback):
            batch = MagicMock()
            batch._callback = callback
            batch._requests = []

            def add(request):
                batch._requests.append(request)

            def execute():
                for i, req in enumerate(batch._requests):
                    batch._callback(str(i), msg_response, None)

            batch.add = add
            batch.execute = execute
            return batch

        gmail_service.new_batch_http_request = fake_batch_factory

        with patch("git_eventhub_agent.workspace_tools._google_service", return_value=gmail_service):
            result = wt.list_gmail_messages("hackathon", execute=True)

        self.assertEqual(result["messages"], [
            {
                "id": "msg-1",
                "thread_id": "thread-1",
                "title": "Hackathon mentoring",
                "from": "mentor@example.com",
                "subject": "Hackathon mentoring",
                "date": "Sun, 17 May 2026 09:00:00 +0800",
                "snippet": "Hackathon mentor intro",
            }
        ])

    def test_gmail_read_use_case_returns_email_title(self) -> None:
        gmail_service = MagicMock()
        gmail_service.users.return_value.messages.return_value.get.return_value.execute.return_value = {
            "id": "msg-1",
            "threadId": "thread-1",
            "snippet": "Hackathon mentor intro",
            "payload": {
                "headers": [
                    {"name": "From", "value": "mentor@example.com"},
                    {"name": "Subject", "value": "Hackathon mentoring"},
                    {"name": "Date", "value": "Sun, 17 May 2026 09:00:00 +0800"},
                ]
            },
        }

        with patch("git_eventhub_agent.workspace_tools._google_service", return_value=gmail_service):
            result = wt.get_gmail_message("msg-1", execute=True)

        _, get_kwargs = gmail_service.users.return_value.messages.return_value.get.call_args
        self.assertEqual(result["resource_id"], "msg-1")
        self.assertEqual(result["title"], "Hackathon mentoring")
        self.assertEqual(result["subject"], "Hackathon mentoring")
        self.assertEqual(result["from"], "mentor@example.com")
        self.assertEqual(get_kwargs["metadataHeaders"], ["From", "Subject", "Date"])

    def test_gmail_follow_up_use_case_creates_draft_not_sent_message(self) -> None:
        gmail_service = MagicMock()
        gmail_service.users.return_value.drafts.return_value.create.return_value.execute.return_value = {
            "id": "draft-123",
            "message": {"id": "message-123"},
        }

        with patch("git_eventhub_agent.workspace_tools._google_service", return_value=gmail_service):
            result = wt.create_gmail_draft(
                "mentor@example.com",
                "Follow up from Climate Hack",
                "Thanks for mentoring the teams.",
                execute=True,
            )

        _, kwargs = gmail_service.users.return_value.drafts.return_value.create.call_args
        self.assertEqual(result["operation"], "create_gmail_draft")
        self.assertEqual(result["resource_id"], "draft-123")
        self.assertEqual(result["message_id"], "message-123")
        self.assertEqual(kwargs["userId"], "me")
        self.assertIn("raw", kwargs["body"]["message"])
        gmail_service.users.return_value.messages.return_value.send.assert_not_called()

    def test_productivity_use_case_creates_event_task(self) -> None:
        tasks_service = MagicMock()
        tasks_service.tasks.return_value.insert.return_value.execute.return_value = {
            "id": "task-123",
            "title": "Invite mentors",
            "selfLink": "https://tasks.google.com/task/task-123",
        }

        with patch("git_eventhub_agent.workspace_tools._google_service", return_value=tasks_service):
            result = wt.create_task(
                "task-list-123",
                "Invite mentors",
                notes="Use the mentor list from the playbook.",
                due="2026-05-20T00:00:00.000Z",
                execute=True,
            )

        _, kwargs = tasks_service.tasks.return_value.insert.call_args
        self.assertEqual(result["operation"], "create_task")
        self.assertEqual(result["resource_id"], "task-123")
        self.assertEqual(kwargs["tasklist"], "task-list-123")
        self.assertEqual(kwargs["body"]["title"], "Invite mentors")
        self.assertEqual(kwargs["body"]["notes"], "Use the mentor list from the playbook.")
        self.assertEqual(kwargs["body"]["due"], "2026-05-20T00:00:00.000Z")


if __name__ == "__main__":
    unittest.main()
