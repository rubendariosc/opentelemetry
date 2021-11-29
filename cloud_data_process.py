"""
`data_ingestion.py` is a Dataflow pipeline which reads a file and writes its
contents to a BigQuery table.
This example does not do any transformation on the data.
"""
import argparse
import logging
import re
import sys
import time
from functools import wraps, reduce
from dataclasses import dataclass
from pymitter import EventEmitter

# OpenTelemetry
from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider

# Apache Beam
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions

# Cloud GCP
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.exporter.cloud_monitoring import CloudMonitoringMetricsExporter


PROJECT_ID = 'metrics-streaming-poc'
event_emitter = EventEmitter()


# Traces config
trace.set_tracer_provider(TracerProvider(resource=Resource.create({SERVICE_NAME: "dataflow"})))
cloud_trace_exporter = CloudTraceSpanExporter(project_id=PROJECT_ID)
trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(cloud_trace_exporter))
tracer = trace.get_tracer(__name__)

# Metrics config
metrics.set_meter_provider(MeterProvider(resource=Resource.create({SERVICE_NAME: "dataflow"})))
meter = metrics.get_meter(__name__)
metrics.get_meter_provider().start_pipeline(meter, CloudMonitoringMetricsExporter(project_id=PROJECT_ID), 5)

# Metrics
rows_count = meter.create_counter(
    name="rows_counter",
    description="number of rows",
    unit="1",
    value_type=int,
)


@dataclass
class CustomMetric:
    labels: dict
    methods: dict


custom_metrics = CustomMetric({}, {})
custom_metrics.labels = {
    "environment": "dev",
    "rows": 0
}


@event_emitter.on('counter_receiver')
def handler_row_counter(*args):
    global custom_metrics
    rows = custom_metrics.methods[f'{args[0].__name__}']
    custom_metrics.methods[f'{args[0].__name__}'] = rows  # |= {f'{args[0].__name__}': rows}


@event_emitter.on('times_receiver')
def handler_execution_times(*args):
    with tracer.start_as_current_span('execution'):
        with tracer.start_as_current_span('execution.info') as span:
            span.set_attribute('method.name', f'{args[0].__name__}')
            with tracer.start_as_current_span('execution.time.seconds') as span_child:
                span_child.set_attribute('seconds', float('{:.6f}'.format(args[1])))


def row_counter(f):
    @wraps(f)
    def wrap(*args):
        global custom_metrics
        if f.__name__ not in custom_metrics.methods:
            custom_metrics.methods[f'{f.__name__}'] = 1
        custom_metrics.methods[f'{f.__name__}'] += 1
        custom_metrics.methods[f'{f.__name__}'] = custom_metrics.methods[f'{f.__name__}']
        event_emitter.emit('counter_receiver', f)
        return f(*args)
    return wrap


def execution_times(f):
    @wraps(f)
    def wrap(*args):
        start = time.time()
        _ = f(*args)
        end = time.time()
        seconds = (end - start)
        event_emitter.emit('times_receiver', f, seconds)
        return _
    return wrap


@row_counter
@execution_times
def parse_method(string_input):
    values = re.split(",", re.sub('\r\n', '', re.sub('"', '', string_input)))
    row = dict(
        zip(('id', 'firstname', 'lastname', 'email', 'age'),
            values))
    return row


@row_counter
@execution_times
def split_text_row(string_input):
    row = dict(string_input)
    domain = row.__getitem__('email').split('@')[-1]
    row['domain'] = domain
    return row


def push_metrics(list_metrics):
    # custom_metrics.labels |= custom_metrics.methods
    if list_metrics.methods:
        rows = reduce(lambda n, m: n + m, list_metrics.methods.values())
        list_metrics.labels["rows"] = rows
        rows_count.add(rows, list_metrics.labels)


def run(argv=None):
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--input',
        dest='input',
        required=False,
        default='gs://python-dataflow-example/data_files/head_usa_names.csv')

    parser.add_argument('--output',
                        dest='output',
                        required=False,
                        default='example.test')

    known_args, pipeline_args = parser.parse_known_args(argv)

    p = beam.Pipeline(options=PipelineOptions(pipeline_args))
    p | 'Read from a File' >> beam.io.ReadFromText(known_args.input, skip_header_lines=1) | \
        'Process Row' >> beam.Map(lambda row: parse_method(row)) | \
        'Split text email' >> beam.ParDo(lambda row: split_text_row(row))

    p.run().wait_until_finish()

    global custom_metrics
    push_metrics(custom_metrics)


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    run(sys.argv)
