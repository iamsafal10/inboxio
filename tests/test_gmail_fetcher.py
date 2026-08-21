"""Tests for Gmail fetching, parsing, pagination, and rate limit handling."""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
from googleapiclient.errors import HttpError
import httplib2
import base64

from app.services.gmail_fetcher import parse_message_payload, with_exponential_backoff, fetch_recent_emails
from app.models.user import User

class TestGmailFetcher(unittest.TestCase):
    def test_parse_message_payload(self):
        """Test extraction of fields from a mocked Gmail payload."""
        payload = {
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Test Subject"},
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "To", "value": "recipient@example.com"},
                    {"name": "Date", "value": "Fri, 21 Aug 2026 12:00:00 +0000"}
                ],
                "mimeType": "text/plain",
                "body": {
                    "data": base64.urlsafe_b64encode(b"Hello world").decode('utf-8')
                }
            }
        }
        
        parsed = parse_message_payload(payload)
        
        self.assertEqual(parsed['subject'], "Test Subject")
        self.assertEqual(parsed['sender'], "sender@example.com")
        self.assertEqual(parsed['recipient'], "recipient@example.com")
        self.assertEqual(parsed['body'], "Hello world")
        self.assertIsNotNone(parsed['sent_at'])
        self.assertEqual(parsed['sent_at'].year, 2026)

    @patch('app.services.gmail_fetcher.time.sleep')
    def test_exponential_backoff_retry(self, mock_sleep):
        """Test that exponential backoff correctly catches 429 and retries."""
        
        mock_response = httplib2.Response({'status': 429})
        mock_error = HttpError(mock_response, b'Too Many Requests')
        
        call_count = [0]
        
        @with_exponential_backoff(max_retries=2, base_delay=0.1)
        def mock_failing_function():
            call_count[0] += 1
            if call_count[0] <= 2:
                raise mock_error
            return "success"
            
        result = mock_failing_function()
        
        self.assertEqual(result, "success")
        self.assertEqual(call_count[0], 3)
        self.assertEqual(mock_sleep.call_count, 2)
        # Check that delay backed off (0.1, 0.2)
        mock_sleep.assert_any_call(0.1)
        mock_sleep.assert_any_call(0.2)

    @patch('app.services.gmail_fetcher.execute_request')
    @patch('app.services.gmail_fetcher.build')
    @patch('app.services.gmail_fetcher._get_user_credentials')
    def test_fetch_recent_emails_pagination(self, mock_creds, mock_build, mock_execute):
        """Test that fetching follows nextPageToken."""
        mock_user = User(id="user1")
        mock_db = MagicMock()
        mock_db.query().filter().first.return_value = None  # Mock no existing emails
        
        # Mock responses
        page1_list = {"messages": [{"id": "msg1"}, {"id": "msg2"}], "nextPageToken": "token2"}
        page2_list = {"messages": [{"id": "msg3"}], "nextPageToken": None}
        
        msg_payload = {
            "threadId": "t1",
            "payload": {
                "headers": [{"name": "Date", "value": "Fri, 21 Aug 2026 12:00:00 +0000"}],
                "mimeType": "text/plain",
                "body": {"data": base64.urlsafe_b64encode(b"body").decode('utf-8')}
            }
        }

        # Sequence of execute_request returns:
        # 1. list page 1
        # 2. get msg1
        # 3. get msg2
        # 4. list page 2
        # 5. get msg3
        mock_execute.side_effect = [
            page1_list,
            msg_payload,
            msg_payload,
            page2_list,
            msg_payload
        ]
        
        fetched = fetch_recent_emails(mock_user, mock_db, max_emails=10)
        
        self.assertEqual(fetched, 3)
        # db.add should be called 3 times
        self.assertEqual(mock_db.add.call_count, 3)
        # db.commit should be called twice (once per page)
        self.assertEqual(mock_db.commit.call_count, 2)

if __name__ == '__main__':
    unittest.main()
