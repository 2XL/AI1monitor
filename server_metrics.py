import json
import psutil
import pika
import time
import urlparse
import socket
import calendar

'''
git clone https://github.com/2XL/AI1monitor.git
cd AI1monitor
python admin.py rabbit_ip # rabbit_ip=10.30.236.141
'''


class ServerMetrics(object):

    def __init__(self, exchange='sync_server', hostname=None, rmq_user="benchbox", rmq_pass="benchbox", rmq_ip="10.30.236.141", rmq_vh=""):
        print "Constructor"

        # rabbit_url="amqp://benchbox:benchbox@10.30.236.141/"
        rabbit_url = "amqp://{}:{}@{}/{}".format(rmq_user, rmq_pass, rmq_ip, rmq_vh)
        url = urlparse.urlparse(rabbit_url)

        if hostname is None:
            self.hostname = socket.gethostname()
        else:
            self.hostname = hostname
        #
        # l = psutil.cpu_percent(interval=0, percpu=True)
        # cpu_percent = reduce(lambda x, y: x + y, l) / len(l)
        # print l, cpu_percent
        self.metric_old = {
            'cpu': psutil.cpu_percent(),
            'ram': psutil.virtual_memory().percent,
            'hdd': psutil.disk_usage('/').percent,
            'hdd_read': psutil.disk_io_counters().read_bytes,
            'hdd_write': psutil.disk_io_counters().write_bytes,
            'net_in': psutil.net_io_counters(pernic=True)['eth0'].bytes_recv,
            'net_out': psutil.net_io_counters(pernic=True)['eth0'].bytes_sent,
            'time': calendar.timegm(time.gmtime()) * 1000
        }

        self.exchange = exchange
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
                host=url.hostname,
                heartbeat_interval=5,
                virtual_host=url.path[1:],
                credentials=pika.PlainCredentials(url.username, url.password)
        ))
        #
        self.channel = self.connection.channel()
        self.channel.exchange_declare(exchange=self.exchange, type='fanout')
        # preinvocar el psutil?


    def emit(self):
        # just emit the general cpu, ram, disk, network and whatever usage it has.

        tags = {
            'hostname': self.hostname
        }

        # l = psutil.cpu_percent(interval=0, percpu=True)
        # cpu_percent = reduce(lambda x, y: x + y, l) / len(l)
        # print l, cpu_percent
        curr_metrics = {
            'cpu': psutil.cpu_percent(),
            'ram': psutil.virtual_memory().percent,
            'hdd': psutil.disk_usage('/').percent,
            'hdd_read': psutil.disk_io_counters().read_bytes,
            'hdd_write': psutil.disk_io_counters().write_bytes,
            'net_in': psutil.net_io_counters(pernic=True)['eth0'].bytes_recv,
            'net_out': psutil.net_io_counters(pernic=True)['eth0'].bytes_sent,
            'time': calendar.timegm(time.gmtime()) * 1000
        }

        # ara fer la resta
        send_metrics = {
            'cpu': curr_metrics['cpu'],
            'ram': curr_metrics['ram'],
            'hdd': curr_metrics['hdd'],
            'hdd_read': psutil.disk_io_counters().read_bytes - self.metric_old['hdd_read'],
            'hdd_write': psutil.disk_io_counters().write_bytes - self.metric_old['hdd_write'],
            'net_in': psutil.net_io_counters(pernic=True)['eth0'].bytes_recv - self.metric_old['net_in'],
            'net_out': psutil.net_io_counters(pernic=True)['eth0'].bytes_sent - self.metric_old['net_out'],
            'time': calendar.timegm(time.gmtime()) * 1000
        }

        self.metric_old = curr_metrics
        data = {
            'metrics': send_metrics,
            'tags': tags
        }
        msg = json.dumps(data)

        print msg

        self.channel.basic_publish(
            exchange=self.exchange,
            routing_key=self.hostname,
            body=msg
        )


if __name__ == "__main__":

    print "SyncServer Monitor"
    # usage:

    sm = ServerMetrics(rmq_ip='10.50.240.146')
    while True:
        time.sleep(1)  # one emit each second
        sm.emit()





