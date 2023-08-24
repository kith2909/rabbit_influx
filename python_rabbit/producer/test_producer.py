import unittest
from unittest.mock import Mock, patch
from producer import \
    RabbitMQProducer  # Replace 'your_module' with the actual module name containing the RabbitMQProducer class


class TestRabbitMQProducer(unittest.TestCase):

    def setUp(self):
        self.df_mock = Mock()
        self.connection_mock = Mock()
        self.channel_mock = Mock()
        self.connection_mock.channel.return_value = self.channel_mock
        self.pika_mock = Mock()
        self.pika_mock.BlockingConnection.return_value = self.connection_mock

        self.exchange_name = 'test-exchange'

        self.producer = RabbitMQProducer('localhost', self.exchange_name, self.df_mock)
        self.producer.connection = self.connection_mock
        self.producer.channel = self.channel_mock

    @patch('producer.pika', new_callable=Mock)
    def test_init(self, pika_mock):
        pika_mock.ConnectionParameters.return_value = 'connection_params'
        self.assertEqual(self.producer.exchange_name, self.exchange_name)
        pika_mock.BlockingConnection.assert_called_once_with('connection_params')
        self.channel_mock.exchange_declare.assert_called_once_with(exchange=self.exchange_name, exchange_type='fanout')

    @patch('producer.json.dumps', return_value='{"key": "value"}')
    @patch('producer.pika', new_callable=Mock)
    def test_send_data(self, pika_mock, json_mock):
        index = 3
        data_mock = Mock()
        data_dict_mock = {'key': 'value'}
        self.df_mock.iloc.return_value = data_mock
        data_mock.to_dict.return_value = data_dict_mock
        self.producer.current_index = index

        self.producer.send_data()

        self.df_mock.iloc.assert_called_once_with(index)
        data_mock.to_dict.assert_called_once()
        json_mock.assert_called_once_with(data_dict_mock)
        self.channel_mock.basic_publish.assert_called_once_with(exchange=self.exchange_name, routing_key='',
                                                                body=json_mock.return_value)
        self.assertEqual(self.producer.current_index, index + 1)

    @patch('producer.time.sleep')
    @patch('producer.random.uniform', return_value=0.5)
    def test_run(self, uniform_mock, sleep_mock):
        self.producer.send_data = Mock(side_effect=[None, KeyboardInterrupt])

        with self.assertRaises(KeyboardInterrupt):
            self.producer.run()

        self.assertEqual(self.producer.send_data.call_count, 2)
        uniform_mock.assert_called_with(0, 1)
        sleep_mock.assert_called_with(0.5)

    @patch('producer.pika', new_callable=Mock)
    def test_connection_close_on_interrupt(self, pika_mock):
        with self.assertRaises(KeyboardInterrupt):
            self.producer.run()

        self.connection_mock.close.assert_called_once()

    def test_send_data_reset_index(self):
        self.producer.current_index = 5
        self.producer.send_data()
        self.assertEqual(self.producer.current_index, 0)