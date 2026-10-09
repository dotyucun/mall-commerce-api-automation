from dataclasses import replace
from unittest.mock import Mock

import bcrypt
import pytest

from mall_api_test.config.settings import SETTINGS, AccountSettings
from mall_api_test.repositories.test_data_manager import TestDataManager as DataManager


@pytest.mark.parametrize("username", ["admin", "customer", "autotest_other"])
def test_cleanup_refuses_non_dedicated_accounts(username):
    database = Mock()
    settings = replace(SETTINGS, user_a=AccountSettings(username, "placeholder"))
    with pytest.raises(RuntimeError, match="Refusing database writes"):
        DataManager(database, settings).reset()
    database.execute.assert_not_called()


def test_credentials_are_initialized_from_configuration_not_a_fixed_password():
    database = Mock()
    accounts = {
        "admin": AccountSettings("admin", "admin-qa-password"),
        "autotest_a": AccountSettings("autotest_a", "user-a-qa-password"),
        "autotest_b": AccountSettings("autotest_b", "user-b-qa-password"),
    }
    settings = replace(
        SETTINGS,
        admin_account=accounts["admin"],
        user_a=accounts["autotest_a"],
        user_b=accounts["autotest_b"],
    )

    def query(sql, params):
        if "SELECT product_id" in sql:
            return {"product_id": 26}
        if "SELECT password" in sql:
            return {"password": "INITIALIZED_BY_BOOTSTRAP"}
        return {"id": {"autotest_a": 9001, "autotest_b": 9002}[params[0]]}

    database.query_one.side_effect = query
    DataManager(database, settings).prepare_credentials()
    assert database.execute.call_count == 3
    for call in database.execute.call_args_list:
        password_hash, username = call.args[1]
        assert bcrypt.checkpw(accounts[username].password.encode(), password_hash.encode())


def test_missing_seed_member_prevents_any_cleanup_write():
    database = Mock()
    database.query_one.return_value = None
    with pytest.raises(RuntimeError, match="Dedicated test member"):
        DataManager(database, SETTINGS).reset()
    database.execute.assert_not_called()
