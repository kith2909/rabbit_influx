import pika  # Import the pika library for RabbitMQ interaction
import pandas as pd  # Import the pandas library for data manipulation
import json  # Import the json library for JSON serialization and deserialization
import time  # Import the time library for adding time delays
import random  # Import the random library for generating random values


class RabbitMQProducer:
    """
    A class representing a RabbitMQ message producer.
    """

    def __init__(self, host, exchange_name, dataframe):
        """
        Initialize the RabbitMQProducer.

        :param host: The hostname where RabbitMQ is running.
        :param exchange_name: The name of the exchange to publish messages to.
        :param dataframe: The pandas DataFrame containing data to be sent.
        """
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host))
        self.channel = self.connection.channel()
        self.exchange_name = exchange_name
        self.channel.exchange_declare(exchange=exchange_name, exchange_type='fanout')
        self.dataframe = dataframe
        self.current_index = 0

    def send_data(self):
        """
        Send data from the DataFrame to the RabbitMQ exchange.
        """

        self.current_index = 0
        data = self.dataframe.iloc[self.current_index].to_dict()
        json_data = json.dumps(data)
        self.channel.basic_publish(exchange=self.exchange_name, routing_key='', body=json_data)
        print(f"Sent: {json_data}")
        self.current_index += 1

    def run(self):
        """
        Start sending data in a loop until interrupted.
        """
        try:
            while True:
                self.send_data()
                time_interval = random.uniform(0, 1)  # Generate a random time interval
                time.sleep(time_interval)  # Sleep for the generated time interval
        except KeyboardInterrupt:
            self.connection.close()  # Close the connection on keyboard interrupt


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

if __name__ == '__main__':
    # Load data from a CSV file and filter as needed
    df = pd.read_csv('de_challenge_sample_data.csv')
    wait_for_rabbitmq('localhost', 5672)
    # Create and run the RabbitMQProducer
    producer = RabbitMQProducer('localhost', 'wiki-exchange', df)
    producer.run()