from mall_api_test.common.db import MallDb
from mall_api_test.config.settings import SETTINGS
from mall_api_test.repositories.test_data_manager import TestDataManager


def main() -> None:
    SETTINGS.require_credentials()
    database = MallDb(SETTINGS.database)
    try:
        manager = TestDataManager(database, SETTINGS)
        manager.prepare_credentials()
        manager.reset()
    finally:
        database.close()
    print("Dedicated test accounts and baseline data are ready")


if __name__ == "__main__":
    main()
