import unittest

from git_eventhub_agent.agent import root_agent
from git_eventhub_agent.tools import run_reconnection_workflow
from git_eventhub_agent import workspace_tools as wt


class WorkflowSmokeTest(unittest.TestCase):
    def test_root_agent_loads_with_expected_model_ids(self) -> None:
        self.assertEqual(root_agent.name, "git_eventhub_orchestrator")
        self.assertEqual(root_agent.model, "gemini-3-flash-preview")
        self.assertEqual(root_agent.sub_agents[0].model, "gemini-2.0-flash-lite")
        self.assertEqual(root_agent.sub_agents[3].model, "gemini-3-pro-preview")

    def test_root_agent_registers_workspace_tools(self) -> None:
        tool_names = {tool.__name__ for tool in root_agent.tools if hasattr(tool, "__name__")}
        workspace_tool_names = [tool.__name__ for tool in wt.WORKSPACE_TOOLS]

        self.assertEqual(len(workspace_tool_names), len(set(workspace_tool_names)))
        self.assertTrue(set(workspace_tool_names).issubset(tool_names))
        self.assertIn("create_drive_folder", tool_names)
        self.assertIn("create_google_doc", tool_names)
        self.assertIn("create_google_form", tool_names)
        self.assertIn("create_google_sheet", tool_names)
        self.assertIn("update_sheet_crm", tool_names)
        self.assertIn("create_gmail_draft", tool_names)
        self.assertIn("create_calendar_draft", tool_names)
        self.assertIn("delete_drive_file", tool_names)
        self.assertIn("update_google_doc_content", tool_names)
        self.assertIn("update_google_form", tool_names)
        self.assertIn("update_google_sheet_values", tool_names)
        self.assertIn("update_gmail_draft", tool_names)
        self.assertIn("update_calendar_event", tool_names)
        self.assertIn("create_google_slide_deck", tool_names)
        self.assertIn("create_task", tool_names)
        self.assertIn("create_chat_message", tool_names)
        self.assertIn("create_meet_space", tool_names)
        self.assertIn("create_keep_note", tool_names)
        self.assertIn("send_gmail_message", tool_names)
        self.assertIn("create_notebooklm_notebook", tool_names)
        self.assertIn("call_appsheet_table_action", tool_names)
        self.assertIn("plan_google_vids_action", tool_names)
        self.assertIn("plan_google_sites_action", tool_names)

    def test_reconnection_workflow_returns_grounded_drafts(self) -> None:
        result = run_reconnection_workflow(
            "Find promising climate-tech startups that Cradle should reconnect with and draft outreach."
        )

        self.assertEqual(result["intent"]["intent"], "reconnection_query")
        self.assertIn("Cradle Ventures", result["intent"]["entities"])
        self.assertGreaterEqual(len(result["recommendations"]), 1)
        self.assertTrue(
            all(rec["verification_status"] == "grounded" for rec in result["recommendations"])
        )
        self.assertTrue(all(draft["requires_approval"] for draft in result["workspace_drafts"]))

    def test_workspace_tools_are_approval_gated_by_default(self) -> None:
        planned_calls = [
            wt.create_drive_folder("Demo Workspace"),
            wt.list_drive_files(),
            wt.get_drive_file("file-id"),
            wt.update_drive_file_metadata("file-id", name="New Name"),
            wt.delete_drive_file("file-id"),
            wt.create_google_doc("Judging Rubric", "Rubric body"),
            wt.get_google_doc("doc-id"),
            wt.update_google_doc_content("doc-id", "Updated body"),
            wt.delete_google_doc("doc-id"),
            wt.create_google_form("Registration", questions_json='["Name", "Email"]'),
            wt.get_google_form("form-id"),
            wt.update_google_form("form-id", description="Updated"),
            wt.delete_google_form("form-id"),
            wt.create_google_sheet("CRM", headers_json='["Name", "Status"]'),
            wt.get_google_sheet_values("sheet-id"),
            wt.update_google_sheet_values("sheet-id", '[["Name", "Status"]]'),
            wt.update_sheet_crm("sheet-id", '["ClimaLoop", "Follow up"]'),
            wt.delete_google_sheet("sheet-id"),
            wt.create_gmail_draft("founder@example.com", "Follow up", "Hello"),
            wt.get_gmail_draft("draft-id"),
            wt.update_gmail_draft("draft-id", "founder@example.com", "Updated", "Hello again"),
            wt.delete_gmail_draft("draft-id"),
            wt.create_calendar_draft(
                "Follow-up",
                "2026-05-16T09:00:00+08:00",
                "2026-05-16T09:30:00+08:00",
                attendee_emails_json='["founder@example.com"]',
                timezone="Asia/Kuala_Lumpur",
            ),
            wt.get_calendar_event("primary", "event-id"),
            wt.update_calendar_event("primary", "event-id", summary="Updated"),
            wt.delete_calendar_event("primary", "event-id"),
            wt.create_google_slide_deck("Event Deck"),
            wt.get_google_slide_deck("deck-id"),
            wt.update_google_slide_deck("deck-id", "[]"),
            wt.delete_google_slide_deck("deck-id"),
            wt.create_task_list("Event Tasks"),
            wt.list_task_lists(),
            wt.get_task_list("tasklist-id"),
            wt.update_task_list("tasklist-id", "Updated Tasks"),
            wt.delete_task_list("tasklist-id"),
            wt.create_task("tasklist-id", "Invite mentors"),
            wt.list_tasks("tasklist-id"),
            wt.get_task("tasklist-id", "task-id"),
            wt.update_task("tasklist-id", "task-id", title="Updated task"),
            wt.delete_task("tasklist-id", "task-id"),
            wt.create_chat_space("Event War Room"),
            wt.list_chat_spaces(),
            wt.get_chat_space("spaces/AAA"),
            wt.update_chat_space("spaces/AAA", "Updated Room"),
            wt.delete_chat_space("spaces/AAA"),
            wt.create_chat_message("spaces/AAA", "Hello team"),
            wt.get_chat_message("spaces/AAA/messages/BBB"),
            wt.update_chat_message("spaces/AAA/messages/BBB", "Updated"),
            wt.delete_chat_message("spaces/AAA/messages/BBB"),
            wt.create_meet_space(),
            wt.get_meet_space("spaces/meet-space"),
            wt.end_meet_active_conference("spaces/meet-space"),
            wt.create_keep_note("Reminder", "Follow up with mentors"),
            wt.list_keep_notes(),
            wt.get_keep_note("notes/note-id"),
            wt.delete_keep_note("notes/note-id"),
            wt.list_gmail_messages(),
            wt.get_gmail_message("message-id"),
            wt.send_gmail_message("founder@example.com", "Hello", "Body"),
            wt.modify_gmail_message_labels("message-id", '["STARRED"]', '["UNREAD"]'),
            wt.trash_gmail_message("message-id"),
            wt.create_notebooklm_notebook("123456789", "Event Research"),
            wt.get_notebooklm_notebook("123456789", "notebook-id"),
            wt.share_notebooklm_notebook(
                "123456789",
                "notebook-id",
                '[{"email":"planner@example.com","role":"PROJECT_ROLE_READER"}]',
            ),
            wt.delete_notebooklm_notebooks(
                "123456789",
                '["projects/123456789/locations/global/notebooks/notebook-id"]',
            ),
            wt.call_appsheet_table_action("app-id", "Events", "Find"),
            wt.plan_google_vids_action("create_video"),
            wt.plan_google_sites_action("create_site"),
        ]

        self.assertTrue(all(call["status"] == "planned" for call in planned_calls))
        self.assertTrue(all(call["requires_approval"] for call in planned_calls))
        self.assertTrue(all(not call["executed"] for call in planned_calls))


if __name__ == "__main__":
    unittest.main()
