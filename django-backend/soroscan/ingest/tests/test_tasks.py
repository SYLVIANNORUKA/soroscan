import pytest
import responses
from celery.exceptions import Retry

from soroscan.ingest.tasks import (
    dispatch_webhook,
    process_new_event,
    validate_event_payload,
)

from .factories import (
    EventSchemaFactory,
    TrackedContractFactory,
    UserFactory,
    WebhookSubscriptionFactory,
)


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def contract(user):
    return TrackedContractFactory(owner=user)


@pytest.mark.django_db
class TestValidateEventPayload:
    def test_validation_success(self, contract):
        schema = EventSchemaFactory(
            contract=contract,
            event_type="swap",
            json_schema={
                "type": "object",
                "properties": {"amount": {"type": "number"}},
                "required": ["amount"],
            },
        )
        payload = {"amount": 100}

        passed, version = validate_event_payload(contract, "swap", payload, ledger=1000)

        assert passed is True
        assert version == schema.version

    def test_validation_failure(self, contract):
        EventSchemaFactory(
            contract=contract,
            event_type="swap",
            json_schema={
                "type": "object",
                "properties": {"amount": {"type": "number"}},
                "required": ["amount"],
            },
        )
        payload = {"wrong_field": "value"}

        passed, version = validate_event_payload(contract, "swap", payload, ledger=1000)

        assert passed is False
        assert version is not None

    def test_no_schema_passes(self, contract):
        payload = {"any": "data"}

        passed, version = validate_event_payload(contract, "unknown_event", payload)

        assert passed is True
        assert version is None

    def test_invalid_payload_type(self, contract):
        passed, version = validate_event_payload(contract, "test", None)

        assert passed is True
        assert version is None


@pytest.mark.django_db
class TestDispatchWebhook:
    @responses.activate
    def test_webhook_dispatch_success(self, contract):
        webhook = WebhookSubscriptionFactory(contract=contract, failure_count=0)
        responses.add(responses.POST, webhook.target_url, status=200)

        event_data = {
            "event_type": "swap",
            "contract_id": contract.contract_id,
            "payload": {"amount": 100},
        }

        result = dispatch_webhook.apply(args=[event_data, webhook.id])

        assert result.successful()
        assert result.result is True

        webhook.refresh_from_db()
        assert webhook.failure_count == 0
        assert webhook.last_triggered is not None

    @responses.activate
    def test_webhook_dispatch_failure_retry(self, contract):
        webhook = WebhookSubscriptionFactory(contract=contract, failure_count=2)
        responses.add(responses.POST, webhook.target_url, status=500)

        event_data = {"event_type": "test", "contract_id": contract.contract_id}

        with pytest.raises(Retry):
            dispatch_webhook.apply(args=[event_data, webhook.id], throw=True)

        webhook.refresh_from_db()
        assert webhook.failure_count == 3

    @responses.activate
    def test_webhook_disabled_after_max_failures(self, contract):
        webhook = WebhookSubscriptionFactory(contract=contract, failure_count=9, is_active=True)
        responses.add(responses.POST, webhook.target_url, status=500)

        event_data = {"event_type": "test", "contract_id": contract.contract_id}

        result = dispatch_webhook.apply(args=[event_data, webhook.id])

        webhook.refresh_from_db()
        assert webhook.failure_count == 10
        assert webhook.is_active is False
        assert result.result is False

    def test_webhook_not_found(self):
        event_data = {"event_type": "test"}

        result = dispatch_webhook.apply(args=[event_data, 99999])

        assert result.result is False

    def test_webhook_inactive(self, contract):
        webhook = WebhookSubscriptionFactory(contract=contract, is_active=False)
        event_data = {"event_type": "test"}

        result = dispatch_webhook.apply(args=[event_data, webhook.id])

        assert result.result is False


@pytest.mark.django_db
class TestProcessNewEvent:
    @responses.activate
    def test_process_event_dispatches_webhooks(self, contract):
        webhook1 = WebhookSubscriptionFactory(
            contract=contract, event_type="swap", is_active=True
        )
        webhook2 = WebhookSubscriptionFactory(
            contract=contract, event_type="", is_active=True
        )
        WebhookSubscriptionFactory(
            contract=contract, event_type="transfer", is_active=True
        )

        responses.add(responses.POST, webhook1.target_url, status=200)
        responses.add(responses.POST, webhook2.target_url, status=200)

        event_data = {
            "contract_id": contract.contract_id,
            "event_type": "swap",
            "payload": {"amount": 100},
        }

        process_new_event.apply(args=[event_data])

        assert len(responses.calls) == 2

    def test_process_event_no_contract_id(self):
        event_data = {"event_type": "swap"}

        result = process_new_event.apply(args=[event_data])

        assert result.successful()

    @responses.activate
    def test_process_event_no_matching_webhooks(self, contract):
        event_data = {
            "contract_id": contract.contract_id,
            "event_type": "swap",
        }

        result = process_new_event.apply(args=[event_data])

        assert result.successful()
        assert len(responses.calls) == 0
