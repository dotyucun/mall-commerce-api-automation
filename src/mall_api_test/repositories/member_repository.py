class MemberRepository:
    def __init__(self, db):
        self.db = db

    def get_by_username(self, username: str) -> dict | None:
        return self.db.query_one(
            """
            SELECT id, username, status, integration
            FROM ums_member
            WHERE username = %s
            """,
            (username,),
        )
