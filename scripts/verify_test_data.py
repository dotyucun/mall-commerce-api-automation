import json

from mall_api_test.common.db import MallDb
from mall_api_test.config.settings import SETTINGS
from mall_api_test.repositories.test_data_manager import TestDataManager


def main() -> None:
    SETTINGS.require_credentials()
    database = MallDb(SETTINGS.database)
    try:
        baseline = TestDataManager(database, SETTINGS).verify_baseline()
    finally:
        database.close()
    print(json.dumps(baseline, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
