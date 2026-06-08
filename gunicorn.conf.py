bind = "127.0.0.1:8000"
workers = 3
worker_class = "sync"
timeout = 120
keepalive = 5
accesslog = "/var/log/beach-wrestling/access.log"
errorlog = "/var/log/beach-wrestling/error.log"
loglevel = "info"
