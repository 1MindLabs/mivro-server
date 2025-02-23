from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from flask import Blueprint, Response

# Blueprint for the metrics route
metrics_blueprint = Blueprint("metrics", __name__)

# Define Prometheus metrics
REQUEST_COUNT = Counter(
    "request_count", "Total number of requests", ["method", "endpoint", "http_status"]
)


@metrics_blueprint.route("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
