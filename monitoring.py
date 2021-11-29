import os
import time

from google.cloud import monitoring_v3
from google.auth import credentials


PROJECT_ID = 'metrics-streaming-poc'
METRIC_ID = 'dataflow.googleapis.com/job/current_num_vcpus'
types = monitoring_v3.types.GetMetricDescriptorRequest(name=f'projects/{PROJECT_ID}/metricDescriptors/{METRIC_ID}')

print(f'projects/{PROJECT_ID}/metricDescriptors/{METRIC_ID}')
json_account_service = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

client = monitoring_v3.services.metric_service.MetricServiceClient()
client.from_service_account_json(filename=json_account_service)

_ = client.get_metric_descriptor(request=types)
print(_)


with open('metricas.txt', 'w') as f:
    for element in client.list_metric_descriptors(name=f'projects/{PROJECT_ID}'):
        f.write(f'{element.name}\n')

with open('metricas_monitored.txt', 'w') as f:
    for element in client.list_monitored_resource_descriptors(name=f'projects/{PROJECT_ID}'):
        f.write(f'Typo: {element.type!s} \nmetric: {element.name} \nlabels:{element.labels}\n\n')

services = monitoring_v3.services.service_monitoring_service.ServiceMonitoringServiceClient()
services.from_service_account_json(filename=json_account_service)
service = services.list_services(parent=f'projects/{PROJECT_ID}')


queries = monitoring_v3.services.query_service.QueryServiceClient()
queries.from_service_account_file(filename=json_account_service)

types = monitoring_v3.types.QueryTimeSeriesRequest()
types.name = 'projects/'+PROJECT_ID
types.query = """
                fetch global
                | metric 'custom.googleapis.com/OpenTelemetry/rows_counter'
                | align rate(30m)
                | every 30m
              """

for q in queries.query_time_series(request=types):
    print(q)
