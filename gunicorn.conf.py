bind = "0.0.0.0:8000"

workers = 1
worker_class = "gthread"
threads = 8

timeout = 180
graceful_timeout = 30
keepalive = 5
max_requests = 1000
max_requests_jitter = 100

preload_app = False

accesslog = "-"
errorlog = "-"
loglevel = "info"
