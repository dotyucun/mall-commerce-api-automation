class PerformanceRepository:
    def __init__(self, db):
        self.db = db

    def snapshot(self) -> dict[str, int]:
        rows = self.db.query_all(
            """
            SHOW GLOBAL STATUS WHERE Variable_name IN (
                'Threads_connected', 'Threads_running', 'Slow_queries', 'Questions',
                'Innodb_row_lock_waits', 'Innodb_row_lock_time',
                'Innodb_buffer_pool_reads', 'Innodb_buffer_pool_read_requests'
            )
            """
        )
        return {row["Variable_name"]: int(row["Value"]) for row in rows}
