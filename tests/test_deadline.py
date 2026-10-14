import io
import json
import os
from pathlib import Path
import runpy
import unittest
from contextlib import ExitStack, redirect_stdout
from datetime import datetime
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import requests
import main
from util.http_help import request_with_retry
from util.daily_success import DailySuccess


class StepTargetTests(unittest.TestCase):
    def test_existing_8000_config_exceeds_target_at_every_hour(self):
        with patch.object(main, 'config', {'MIN_STEP': '8000', 'MAX_STEP': '10000'}, create=True):
            for hour in range(24):
                with self.subTest(hour=hour), patch.object(main, 'time_bj', datetime(2026, 10, 14, hour), create=True):
                    low, high = main.get_min_max_steps()
                    self.assertGreater(low, 8000)
                    self.assertEqual(high, 10000)

    def test_low_upper_bound_cannot_drop_below_target(self):
        with patch.object(main, 'config', {'MIN_STEP': '1000', 'MAX_STEP': '7000'}, create=True):
            self.assertEqual(main.get_min_max_steps(), (8001, 8001))

    def test_higher_configured_range_is_preserved(self):
        with patch.object(main, 'config', {'MIN_STEP': '18000', 'MAX_STEP': '25000'}, create=True):
            self.assertEqual(main.get_min_max_steps(), (18000, 25000))


class RequestRetryTests(unittest.TestCase):
    def response(self, code, headers=None):
        return Mock(status_code=code, headers=headers or {})

    def test_disconnected_upload_retries_same_payload(self):
        payload = 'same-daily-step-total'
        ok = self.response(200)
        with patch('util.http_help.requests.request', side_effect=[requests.exceptions.ConnectionError(), ok]) as send, patch('util.http_help.time.sleep'):
            self.assertIs(request_with_retry('POST', 'https://example.test/data', data=payload), ok)
            self.assertEqual(send.call_count, 2)
            for call in send.call_args_list:
                self.assertEqual(call.kwargs['data'], payload)
                self.assertEqual(call.kwargs['timeout'], (10, 30))

    def test_rate_limit_honors_bounded_retry_after(self):
        with patch('util.http_help.requests.request', side_effect=[self.response(429, {'Retry-After': '120'}), self.response(200)]), patch('util.http_help.time.sleep') as sleep:
            self.assertEqual(request_with_retry('GET', 'https://example.test').status_code, 200)
            sleep.assert_called_once_with(60)

    def test_server_error_attempts_are_bounded(self):
        with patch('util.http_help.requests.request', return_value=self.response(503)) as send, patch('util.http_help.time.sleep') as sleep:
            self.assertEqual(request_with_retry('GET', 'https://example.test').status_code, 503)
            self.assertEqual(send.call_count, 3)
            self.assertEqual(sleep.call_count, 2)

    def test_timeout_is_reported_after_three_attempts(self):
        with patch('util.http_help.requests.request', side_effect=requests.exceptions.Timeout()) as send, patch('util.http_help.time.sleep'):
            with self.assertRaises(requests.exceptions.Timeout):
                request_with_retry('GET', 'https://example.test')
            self.assertEqual(send.call_count, 3)

    def test_invalid_credentials_are_not_retried(self):
        with patch('util.http_help.requests.request', return_value=self.response(401)) as send:
            self.assertEqual(request_with_retry('GET', 'https://example.test').status_code, 401)
            send.assert_called_once()

    def test_retry_errors_do_not_expose_login_token(self):
        output = io.StringIO()
        with patch('util.http_help.requests.request', side_effect=requests.exceptions.Timeout('login_token=private-value')), patch('util.http_help.time.sleep'), redirect_stdout(output):
            with self.assertRaises(requests.exceptions.Timeout) as failure:
                request_with_retry('GET', 'https://example.test?login_token=private-value')
        self.assertNotIn('private-value', output.getvalue() + str(failure.exception))


class ScriptResultTests(unittest.TestCase):
    def run_script(self, upload_result=(True, 'success'), login_result=('test-access', None), accounts=1, state_dir=None, date='2026-10-14', concurrent=False, user_list=None):
        config = {
            'USER': '#'.join(user_list or [f'test{i}@example.test' for i in range(accounts)]),
            'PWD': '#'.join(['test-password'] * accounts),
            'MIN_STEP': '8000', 'MAX_STEP': '10000', 'SLEEP_GAP': '0',
            'USE_CONCURRENT': 'True' if concurrent else 'False',
        }
        output = io.StringIO()
        with ExitStack() as stack:
            if state_dir is None:
                state_dir = stack.enter_context(TemporaryDirectory())
            stack.enter_context(patch.dict(os.environ, {'CONFIG': json.dumps(config), 'AES_KEY': ''}, clear=True))
            stack.enter_context(patch('util.daily_success.DailySuccess', side_effect=lambda day: DailySuccess(day, Path(state_dir) / 'daily_success.json')))
            clock = stack.enter_context(patch('datetime.datetime', wraps=datetime))
            clock.now.return_value = datetime.fromisoformat(date + 'T15:17:00+08:00')
            stack.enter_context(patch('util.zepp_helper.login_access_token', return_value=login_result))
            stack.enter_context(patch('util.zepp_helper.grant_login_tokens', return_value=('test-login', 'test-app', 'test-user', None)))
            stack.enter_context(patch('util.zepp_helper.check_app_token', return_value=(True, None)))
            upload = stack.enter_context(patch('util.zepp_helper.post_fake_brand_data', side_effect=upload_result if isinstance(upload_result, list) else None, return_value=upload_result))
            stack.enter_context(redirect_stdout(output))
            with self.assertRaises(SystemExit) as exit_result:
                runpy.run_path(str(Path(main.__file__)), run_name='__main__')
        return exit_result.exception.code, upload, output.getvalue()

    def test_success_upload_exceeds_8000_and_exits_zero(self):
        code, upload, output = self.run_script()
        self.assertEqual(code, 0)
        self.assertGreater(int(upload.call_args.args[0]), 8000)
        self.assertIn('成功：1，失败：0', output)

    def test_login_failure_exits_nonzero(self):
        code, upload, output = self.run_script(login_result=(None, 'test failure'))
        self.assertEqual(code, 1)
        upload.assert_not_called()
        self.assertIn('成功：0，失败：1', output)

    def test_partial_account_failure_exits_nonzero(self):
        code, upload, output = self.run_script(upload_result=[(True, 'success'), (False, 'rejected')], accounts=2)
        self.assertEqual(code, 1)
        self.assertEqual(upload.call_count, 2)
        self.assertIn('成功：1，失败：1', output)

    def test_later_run_skips_after_daily_success(self):
        with TemporaryDirectory() as state_dir:
            first, first_upload, _ = self.run_script(state_dir=state_dir)
            second, second_upload, output = self.run_script(state_dir=state_dir)
            self.assertEqual((first, second), (0, 0))
            first_upload.assert_called_once()
            second_upload.assert_not_called()
            self.assertIn('跳过登录和步数修改', output)

    def test_failed_first_run_is_retried_then_stops(self):
        with TemporaryDirectory() as state_dir:
            failed, first_upload, _ = self.run_script(upload_result=(False, 'rejected'), state_dir=state_dir)
            recovered, second_upload, _ = self.run_script(state_dir=state_dir)
            skipped, third_upload, _ = self.run_script(state_dir=state_dir)
            self.assertEqual((failed, recovered, skipped), (1, 0, 0))
            first_upload.assert_called_once()
            second_upload.assert_called_once()
            third_upload.assert_not_called()

    def test_partial_failure_retries_only_failed_account(self):
        with TemporaryDirectory() as state_dir:
            first, first_upload, _ = self.run_script(upload_result=[(True, 'success'), (False, 'rejected')], accounts=2, state_dir=state_dir)
            second, second_upload, output = self.run_script(accounts=2, state_dir=state_dir)
            self.assertEqual((first, second), (1, 0))
            self.assertEqual(first_upload.call_count, 2)
            second_upload.assert_called_once()
            self.assertIn('跳过重复修改', output)

    def test_next_beijing_day_runs_again(self):
        with TemporaryDirectory() as state_dir:
            self.run_script(state_dir=state_dir, date='2026-10-14')
            code, upload, _ = self.run_script(state_dir=state_dir, date='2026-10-15')
            self.assertEqual(code, 0)
            upload.assert_called_once()

    def test_duplicate_concurrent_account_uploads_only_once(self):
        with TemporaryDirectory() as state_dir:
            code, upload, _ = self.run_script(accounts=2, state_dir=state_dir, concurrent=True, user_list=['same@example.test'] * 2)
            self.assertEqual(code, 0)
            upload.assert_called_once()

    def test_existing_success_checkpoint_skips_today(self):
        with TemporaryDirectory() as state_dir:
            Path(state_dir, 'daily_success.json').write_text(json.dumps({'date': '2026-10-14', 'completed': True, 'accounts': {}}))
            code, upload, _ = self.run_script(state_dir=state_dir)
            self.assertEqual(code, 0)
            upload.assert_not_called()


class DailyRecordTests(unittest.TestCase):
    def test_phone_prefixes_share_record_without_exposing_account(self):
        with TemporaryDirectory() as directory:
            path = Path(directory, 'daily_success.json')
            state = DailySuccess('2026-10-14', path)
            state.record('13800138000', 9000)
            reloaded = DailySuccess('2026-10-14', path)
            self.assertEqual(reloaded.get_step('+8613800138000'), 9000)
            self.assertNotIn('13800138000', path.read_text())

    def test_malformed_record_stops_instead_of_reuploading(self):
        with TemporaryDirectory() as directory:
            path = Path(directory, 'daily_success.json')
            path.write_text('{}')
            with self.assertRaises(ValueError):
                DailySuccess('2026-10-14', path)


if __name__ == '__main__':
    unittest.main()
