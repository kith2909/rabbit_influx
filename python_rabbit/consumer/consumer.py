import time
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import pika
import json
import threading

switch_event = threading.Event()


class InfluxDBManager:
    """
    DataBase Manager class, realise Flux queries and updates database in a thread
    """
    def __init__(self, url, token, org, bucket, base):
        self.url = url
        self.token = token
        self.org = org
        self.bucket = bucket
        self.base = base
        self.client = self.start_client()
        self.write_api = self.setup_write_api()

    def start_client(self):
        """
        :return: client for Influx database
        """
        return InfluxDBClient(url=self.url, token=self.token, org=self.org)

    def setup_write_api(self):
        """
        :return: API connector for updates
        """
        return self.client.write_api(write_options=SYNCHRONOUS)

    def write_data(self, data):
        """
        :param data: Prepared data from json to Line Protocol
        :return:  output in a DataBase
        """

        self.write_api.write(bucket=self.bucket, org=self.org, record=data)
        print(f"InfluxDBManager - Added to InfluxDB: {data}")

    def read_all_data(self):
        """
        Request to InfluxDB by API protocol in Flux for updates in a second
        :return: printed output total mean updates in a second
        """

        query = f'''from(bucket: "{self.bucket}")
            |> range(start: -24h)
            |> filter(fn: (r) => r._measurement == "{self.base}")
            |> window(every: 1s)
            |> count()
        '''

        tables = self.client.query_api().query(query, org=self.org)
        total = 0
        sum_records = 0
        for table in tables:
            for record in table.records:
                sum_records += record['_value']
                total += 1
        print("Total mean updates in a second: ", sum_records / total)

    def read_wiki_data(self, wiki):
        """
        Request to InfluxDB by API protocol in Flux for updates in a second
        :param wiki: Deutschland updates
        :return: printed output total mean updates in a second for DE region
        """
        query = f'''from(bucket: "{self.bucket}")
            |> range(start: -24h)
            |> filter(fn: (r) => r._measurement == "{self.base}" )
            |> filter(fn: (r) => r["tag_wiki"] == "{wiki}")
            |> window(every: 1s)
            |> count() '''
        tables = self.client.query_api().query(query, org=self.org)

        total = 0
        sum_records = 0
        for table in tables:
            for record in table.records:
                sum_records += record['_value']
                total += 1
        print(f"Mean updates in a minute for {wiki}:", sum_records / total)


class RabbitMQConsumer:
    """
    RabbitMQ Tread Customer
    Initiates and uses influxdb_client for data storage
    """
    def __init__(self, host, db_url, org, bucket, token, exchange_name, influxdb_database):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host))
        self.channel = self.connection.channel()
        self.database = influxdb_database
        self.exchange_name = exchange_name
        self.channel.exchange_declare(exchange=exchange_name, exchange_type='fanout')

        self.influxdb_client = InfluxDBManager(url=db_url,
                                               token=token,
                                               org=org,
                                               bucket=bucket,
                                               base=influxdb_database)
        self.channel.queue_declare(queue='', exclusive=True)
        result = self.channel.queue_declare(queue='', exclusive=True)
        self.queue_name = result.method.queue
        self.channel.queue_bind(exchange=exchange_name, queue=self.queue_name)

    def influxdb_write(self, data):
        """
        Data preprocessing in a Line Protocol
        :param data: json format from exchange
        :return: RabbitMQConsumer - Added line to InfluxDB
        """
        influxdb_data = Point(self.database)
        influxdb_data.tag("tag_wiki", data['wiki'])
        for key, value in data.items():
            if key != 'wiki':
                influxdb_data.field(key, value)

        self.influxdb_client.write_data(influxdb_data)
        # print(f"RabbitMQConsumer - Added to InfluxDB: {influxdb_data}")

    def callback(self, ch, method, properties, body):
        """
        Recieving and sending data to a storage
        :param body: exchange result
        """
        data = json.loads(body)
        self.influxdb_write(data)

    def start_consuming(self):
        """

        :return:
        """
        self.channel.basic_consume(queue=self.queue_name, on_message_callback=self.callback, auto_ack=True)
        print('Waiting for messages. To exit press CTRL+C')
        self.channel.start_consuming()


def main(user):
    """
    With more time I would create a more friendly interface
    :param user: Client API for a Influx DB
    :return: printed output
    """
    while True:
        user.influxdb_client.read_all_data()
        user.influxdb_client.read_wiki_data('dewiki')
        time.sleep(5)


def user_questions(user):
    """
    Not used
    :param user:  Client API for a Influx DB
    :return: printed output with a simple
    """
    user_input = input("Input 1 - Total updates in a second.\n"
                       "Input 2 - Deutsch wiki updates in a second.\n"
                       "Input 3 - exit\n")
    match user_input:
        case '1':
            print("Input is 1.")
            user.influxdb_client.read_all_data()
        case '2':
            print("Input is 2.")
            user.influxdb_client.read_wiki_data('dewiki')
        case '3':
            print("Thank you for your attention. Best wishes.")
            exit()
        case _:
            print("Input is not 1, 2, or 3")


def wait_for_rabbitmq(host, port, timeout=90):
    start_time = time.time()
    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host, port))
            connection.close()
            break  # Выход из цикла, если соединение успешно установлено
        except pika.exceptions.AMQPConnectionError:
            if time.time() - start_time > timeout:
                raise TimeoutError("Timed out waiting for RabbitMQ to become available")
            print(f"Waiting for RabbitMQ at {host}:{port}...")
            time.sleep(5)
    return connection


if __name__ == "__main__":
    # Define connection details and initialize RabbitMQConsumer instance
    url = "http://localhost:8086"
    org = "time"
    bucket = "rabbit_bucket"
    base = "wiki_base"
    token = "rtQPLt8YiIP9J2hAo33BEyhgOC8ZF1aiDjSCy38gsbBghfvi7ao9O-kIX-dC2mcjof-bkEc5sEBatjJKGvU-8Q=="

    
    wait_for_rabbitmq('localhost', 5672)

    consumer = RabbitMQConsumer(host='localhost',
                                db_url=url,
                                org=org,
                                token=token,
                                bucket=bucket,
                                exchange_name='wiki-exchange',
                                influxdb_database=base)

    # Create and start the background processes for data consumption and user interaction
    data_process = threading.Thread(target=consumer.start_consuming)
    data_process.start()

    # Create and start second background process
    user_process = threading.Thread(target=main(consumer))
    user_process.start()

    # Wait for the threads to finish
    data_process.join()
    user_process.join()
