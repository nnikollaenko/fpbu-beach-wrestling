bind = "0.0.0.0:" + str(int(__import__('os').environ.get('PORT', 8000)))
workers = 2
worker_class = "sync"
timeout = 120
keepalive = 5
accesslog = "-"
errorlog = "-"
loglevel = "info"
