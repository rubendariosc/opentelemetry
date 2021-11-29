python cloud_data_process.py --runner='DirectRunner' \
      --project='metrics-streaming-poc' \
      --region='us-central1' \
      --temp_location gs://poc_mstr_dataflow_run/tmp \
      --input=users2.csv \
      --service_account_email='poc-mstr-developer@metrics-streaming-poc.iam.gserviceaccount.com' \
      --experiment use_unsupported_python_version
      # --streaming
