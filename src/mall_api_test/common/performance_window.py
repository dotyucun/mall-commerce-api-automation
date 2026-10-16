class RequestWindow:
    """Track starts/completions with one monotonic clock, including unfinished requests."""

    def __init__(self):
        self.start = None
        self.deadline = None
        self.started_requests = 0
        self.pending = set()

    def begin(self, now: float, duration: float) -> None:
        if self.start is not None or duration <= 0:
            raise ValueError("The window must be started once with positive duration")
        self.start = now
        self.deadline = now + duration

    def start_request(self, now: float) -> int | None:
        if self.start is None or not self.start <= now < self.deadline:
            return None
        token = self.started_requests
        self.started_requests += 1
        self.pending.add(token)
        return token

    def finish_request(self, token: int | None, now: float) -> str | None:
        if token is None:
            return None
        if token not in self.pending:
            raise ValueError("Unknown or duplicate request completion")
        self.pending.remove(token)
        return "steady" if now < self.deadline else "tail"
