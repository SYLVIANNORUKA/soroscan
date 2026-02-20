import pytest
import responses
from unittest.mock import MagicMock, patch

from soroscan.ingest.stellar_client import SorobanClient, TransactionResult


@pytest.fixture
def client():
    return SorobanClient(
        rpc_url="https://soroban-testnet.stellar.org",
        network_passphrase="Test SDF Network ; September 2015",
        contract_id="C" + "A" * 55,
        secret_key="SBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
    )


class TestSorobanClient:
    def test_client_initialization(self, client):
        assert client.rpc_url == "https://soroban-testnet.stellar.org"
        assert client.network_passphrase == "Test SDF Network ; September 2015"
        assert client.contract_id.startswith("C")
        assert client.keypair is not None

    def test_client_initialization_no_secret(self):
        client = SorobanClient(secret_key=None)
        assert client.keypair is None

    def test_address_to_sc_val_account(self, client):
        address = "GAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAWHF"
        sc_val = client._address_to_sc_val(address)
        assert sc_val is not None

    def test_address_to_sc_val_contract(self, client):
        address = "C" + "A" * 55
        sc_val = client._address_to_sc_val(address)
        assert sc_val is not None

    def test_address_to_sc_val_invalid(self, client):
        with pytest.raises(ValueError):
            client._address_to_sc_val("INVALID")

    def test_symbol_to_sc_val(self, client):
        sc_val = client._symbol_to_sc_val("test_symbol")
        assert sc_val is not None

    def test_bytes_to_sc_val(self, client):
        data = b"test data"
        sc_val = client._bytes_to_sc_val(data)
        assert sc_val is not None

    @patch("soroscan.ingest.stellar_client.SorobanServer")
    def test_record_event_no_keypair(self, mock_server):
        client = SorobanClient(secret_key=None)
        result = client.record_event(
            target_contract_id="C" + "A" * 55,
            event_type="swap",
            payload_hash_hex="a" * 64,
        )

        assert result.success is False
        assert result.error == "No keypair configured"

    @patch("soroscan.ingest.stellar_client.SorobanServer")
    def test_record_event_invalid_hash_length(self, mock_server, client):
        result = client.record_event(
            target_contract_id="C" + "A" * 55,
            event_type="swap",
            payload_hash_hex="aa",
        )

        assert result.success is False
        assert "32 bytes" in result.error

    @patch("soroscan.ingest.stellar_client.SorobanServer")
    def test_record_event_success(self, mock_server, client):
        mock_account = MagicMock()
        mock_account.sequence = 1

        mock_simulate_response = MagicMock()
        mock_simulate_response.error = None

        mock_send_response = MagicMock()
        mock_send_response.status = "PENDING"
        mock_send_response.hash = "tx123"

        mock_server_instance = mock_server.return_value
        mock_server_instance.load_account.return_value = mock_account
        mock_server_instance.simulate_transaction.return_value = mock_simulate_response
        mock_server_instance.prepare_transaction.return_value = MagicMock()
        mock_server_instance.send_transaction.return_value = mock_send_response

        result = client.record_event(
            target_contract_id="C" + "A" * 55,
            event_type="swap",
            payload_hash_hex="a" * 64,
        )

        assert result.success is True
        assert result.tx_hash == "tx123"
        assert result.status == "PENDING"

    @patch("soroscan.ingest.stellar_client.SorobanServer")
    def test_record_event_simulation_failed(self, mock_server, client):
        mock_account = MagicMock()
        mock_account.sequence = 1

        mock_simulate_response = MagicMock()
        mock_simulate_response.error = "Simulation error"

        mock_server_instance = mock_server.return_value
        mock_server_instance.load_account.return_value = mock_account
        mock_server_instance.simulate_transaction.return_value = mock_simulate_response

        result = client.record_event(
            target_contract_id="C" + "A" * 55,
            event_type="swap",
            payload_hash_hex="a" * 64,
        )

        assert result.success is False
        assert result.status == "simulation_failed"
        assert result.error == "Simulation error"

    @patch("sorosban.ingest.stellar_client.SorobanServer")
    def test_record_event_exception(self, mock_server, client):
        mock_server_instance = mock_server.return_value
        mock_server_instance.load_account.side_effect = Exception("Network error")

        result = client.record_event(
            target_contract_id="C" + "A" * 55,
            event_type="swap",
            payload_hash_hex="a" * 64,
        )

        assert result.success is False
        assert result.status == "error"
        assert "Network error" in result.error

    @patch("soroscan.ingest.stellar_client.SorobanServer")
    def test_get_total_events(self, mock_server, client):
        mock_account = MagicMock()
        mock_account.sequence = 1

        mock_server_instance = mock_server.return_value
        mock_server_instance.load_account.return_value = mock_account

        result = client.get_total_events()

        assert result is None
