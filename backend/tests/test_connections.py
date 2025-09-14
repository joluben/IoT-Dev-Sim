import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.connection_clients import KafkaClient, ConnectionClientFactory
from app.models import Connection

class TestKafkaClient(unittest.TestCase):

    @patch('app.connection_clients.Producer')
    def test_kafka_client_send_message(self, MockProducer):
        """Test that KafkaClient.send produces a message correctly.""" 
        # Arrange
        mock_producer_instance = MockProducer.return_value
        mock_producer_instance.flush.return_value = 0  # Simulate successful flush

        connection_config = {
            'host': 'fake.kafka:9092',
            'endpoint': 'test-topic',
            'client_id': 'test-producer'
        }
        
        client = KafkaClient(connection_config)

        test_data = {'sensor_id': 'sensor-123', 'value': 42}

        # Act
        success, message = client.send(test_data)

        # Assert
        self.assertTrue(success)
        self.assertEqual(message, "Mensaje enviado al topic test-topic")
        mock_producer_instance.produce.assert_called_once()
        mock_producer_instance.flush.assert_called_once_with(10)

    @patch('app.connection_clients.Producer')
    def test_kafka_client_test_connection_success(self, MockProducer):
        """Test that KafkaClient.test_connection handles success correctly."""
        # Arrange
        mock_producer_instance = MockProducer.return_value
        mock_producer_instance.list_topics.return_value = {}  # Simulate success

        connection_config = {'host': 'fake.kafka:9092'}
        client = KafkaClient(connection_config)

        # Act
        result = client.test_connection()

        # Assert
        self.assertTrue(result['success'])
        self.assertEqual(result['message'], 'Conexión con el broker de Kafka exitosa.')
        mock_producer_instance.list_topics.assert_called_once_with(timeout=5)


class TestConnectionClientFactory(unittest.TestCase):

    @patch('app.connection_clients.KafkaClient')
    @patch('app.connection_clients.json')
    def test_factory_creates_kafka_client(self, mock_json, MockKafkaClient):
        """Test that the factory creates a KafkaClient for the KAFKA type."""
        # Arrange
        mock_connection = MagicMock(spec=Connection)
        mock_connection.type = 'KAFKA'
        mock_connection.host = 'kafka:9092'
        mock_connection.port = 9092
        mock_connection.endpoint = 'test-topic'
        mock_connection.auth_type = 'NONE'
        mock_connection.connection_config = '{}'
        mock_connection.get_decrypted_auth_config.return_value = {}
        
        mock_json.loads.return_value = {}

        # Act
        client = ConnectionClientFactory.create_client(mock_connection)

        # Assert
        MockKafkaClient.assert_called_once()
        # Verify the client is the mocked instance
        self.assertEqual(client, MockKafkaClient.return_value)

if __name__ == '__main__':
    unittest.main()
