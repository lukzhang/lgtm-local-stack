# app.py
from flask import Flask
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import and configure OpenTelemetry
from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor

# ----------------------------------------------------
# Configuration
# NOTE: The endpoint is set to localhost:4318 for the OTel Collector
resource = Resource.create({"service.name": "lgtm-test-app"})

# 1. Traces Setup
trace.set_tracer_provider(TracerProvider(resource=resource))
otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4318/v1/traces")
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))
tracer = trace.get_tracer(__name__)

# 2. Metrics Setup
metric_reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(endpoint="http://localhost:4318/v1/metrics")
)
metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[metric_reader]))
meter = metrics.get_meter("app.metric.generator")
request_counter = meter.create_counter("requests.made", unit="1", description="Counts total requests")

# ----------------------------------------------------

app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)

@app.route("/")
def hello_world():
    # Get the current active trace span
    current_span = trace.get_current_span()

    # 1. Generate Log
    logger.info("Test request received and being processed.",
                extra={'trace_id': hex(current_span.context.trace_id)})

    # 2. Update Metric
    request_counter.add(1, {"route": "/"})

    # 3. Create Custom Span (for the Trace)
    with tracer.start_as_current_span("custom-work"):
        import time
        time.sleep(0.05) # Simulate work

    return "Hello from the LGTM test app!\n"

if __name__ == "__main__":
    app.run(port=8080)
