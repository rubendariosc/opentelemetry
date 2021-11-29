"""`data_ingestion.py` is a Dataflow pipeline which reads a file and writes its
contents to a BigQuery table.
This example does not do any transformation on the data.
"""
import argparse
import logging
import re
import sys
import time
import psutil

from functools import wraps

# OpenTelemetry
from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
#from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Apache Beam
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions

# Cloud GCP
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.trace import Link
"""
# OTLP
trace.set_tracer_provider(
    TracerProvider(
        resource=Resource.create({SERVICE_NAME: "dataflow"})
    )
)

otlp_exporter = OTLPSpanExporter(endpoint='0.0.0.0:4317', insecure=True)
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))
"""

tracer_provider = TracerProvider()
cloud_trace_exporter = CloudTraceSpanExporter()
tracer_provider.add_span_processor(
    BatchSpanProcessor(cloud_trace_exporter)
)
trace.set_tracer_provider(tracer_provider)

tracer = trace.get_tracer(__name__)


class Counter:
    counter = 0


count = Counter()


def execution_metrics(f):
    @wraps(f)
    def wrap(*args):
        with tracer.start_as_current_span('execution'):
            with tracer.start_as_current_span('execution.info') as span:
                span.set_attribute('method.name', f'{f.__name__}')
                with tracer.start_as_current_span('execution.time.seconds') as span_child:
                    start = time.time()
                    function = f(*args)
                    end = time.time()
                    seconds = (end - start)
                    total, percent = 0.0, psutil.cpu_percent(interval=seconds, percpu=True)
                    for _ in percent:
                        total += _
                    span.set_attribute('method.cpu', float(total / len(percent)))
                    span.set_attribute('method.cpus', len(percent))
                    span_child.set_attribute('seconds', float('{:.6f}'.format(seconds)))
                    #time.sleep(.05)
            return function
    return wrap


def row_counter(f):
    @wraps(f)
    def wrap(*args):
        function = f(*args)
        count.counter += 1
        return function
    return wrap


@row_counter
def parse_method(string_input):
    with tracer.start_as_current_span('execution'):
        values = re.split(",", re.sub('\r\n', '', re.sub('"', '',
                                                         string_input)))
        row = dict(
            zip(('id', 'firstname', 'lastname', 'email', 'age'),
                values))
    return row


@execution_metrics
def split_text_row(string_input):
    row = dict(string_input)
    domain = row.__getitem__('email').split('@')[-1]
    row['domain'] = domain
    return row


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

    with tracer.start_as_current_span('counter_row') as span:
        span.set_attribute('rows', count.counter)


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    run(sys.argv)
