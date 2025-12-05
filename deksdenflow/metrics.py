from prometheus_client import Counter, generate_latest

requests_total = Counter("requests_total", "Total HTTP requests")
jobs_processed_total = Counter("jobs_processed_total", "Total jobs processed", ["job_type", "status"])
webhooks_total = Counter("webhooks_total", "Total webhooks received", ["provider"])


class Metrics:
    def inc_request(self) -> None:
        requests_total.inc()

    def inc_job(self, job_type: str, status: str) -> None:
        jobs_processed_total.labels(job_type=job_type, status=status).inc()

    def inc_webhook(self, provider: str) -> None:
        webhooks_total.labels(provider=provider).inc()

    def to_prometheus(self) -> bytes:
        return generate_latest()


metrics = Metrics()
