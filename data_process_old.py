
# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""`data_ingestion.py` is a Dataflow pipeline which reads a file and writes its
contents to a BigQuery table.
This example does not do any transformation on the data.

docker run --name jaeger \
    -p 16686:16686 \        # Puerto de la UI
    -p 14269:14269 \        # Puerto por donde sirve las metricas
    -p 6831:6831/udp \      # Puerto por donde recibe metricas
    jaegertracing/all-in-one

./jaeger-all-in-one --metrics-backend prometheus \
    --processor.jaeger-compact.server-max-packet-size 80000 \
    --processor.jaeger-compact.server-host-port 0.0.0.0:6831 \
    --metrics-http-route /metrics

https://www.jaegertracing.io/docs/1.19/client-libraries/#emsgsize-and-udp-buffer-limits
"""
import argparse
import logging
import re
import sys
import time
import psutil

from functools import wraps
from typing import Dict
from dataclasses import dataclass

# Prometheus
from prometheus_client import Counter, Gauge, CollectorRegistry, write_to_textfile, push_to_gateway
from prometheus_client.exposition import basic_auth_handler

# OpenTelemetry
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Apache Beam
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions

# def auth_handler(url, method, timeout, headers, data):
#    username = 'admin'
#    password = 'admin'
#    return basic_auth_handler(url, method, timeout, headers, data, username, password)

# registry = CollectorRegistry()
# time_process = Gauge('time_process_function', '', labelnames=['name_function'], registry=registry)

# FUNCTION_COUNTERS = {
#    'parse_method': 0.0,
#    'split_text_row': 0.0
# }


# @dataclass(init=True)
# class RESCounter:
#    counters: Dict


#r_counter = RESCounter(FUNCTION_COUNTERS)


trace.set_tracer_provider(
    TracerProvider(
        resource=Resource.create({SERVICE_NAME: "dataflow"})
    )
)
# Jaeger
#jaeger_exporter = JaegerExporter(
#    agent_host_name="localhost",
#    agent_port=6831,
#    max_tag_value_length=200
#)

otlp_exporter = OTLPSpanExporter(endpoint='0.0.0.0:4317', insecure=True)

# Jaeger
#trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(jaeger_exporter))
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))

tracer = trace.get_tracer(__name__)

"""
Prometheus
def timings(f):
    @wraps(f)
    def wrap(*args):
        start = time.time()
        result = f(*args)
        end = time.time()
        times = (end - start)
        if r_counter.counters[f.__name__] == 0:
            pass
        elif r_counter.counters[f.__name__] > times:
            time_process.labels(f.__name__).dec(float('{:.5f}'.format(times)))
        elif times > r_counter.counters[f.__name__]:
            time_process.labels(f.__name__).inc(float('{:.5f}'.format(times)))
        r_counter.counters[f.__name__] = times
        return result
    return wrap
"""


def execution_metrics_old(f):
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
                    total, percent = 0, psutil.cpu_percent(interval=seconds, percpu=True)
                    for _ in percent:
                        total += _
                    span.set_attribute('method.cpu', total / len(percent))
                    span.set_attribute('method.cpus', len(percent))
                    span_child.set_attribute('seconds', float('{:.6f}'.format(seconds)))
                    time.sleep(.2)
            return function
    return wrap


@execution_metrics
def parse_method(string_input):
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


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    run(sys.argv)
