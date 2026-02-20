import pytest
from django.utils import timezone
from strawberry.test import BaseGraphQLTestClient

from soroscan.ingest.schema import schema

from .factories import ContractEventFactory, TrackedContractFactory, UserFactory


@pytest.fixture
def graphql_client():
    return BaseGraphQLTestClient(schema)


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def contract(user):
    return TrackedContractFactory(owner=user)


@pytest.mark.django_db
class TestGraphQLQueries:
    def test_query_contracts(self, graphql_client, contract):
        query = """
            query {
                contracts {
                    id
                    contractId
                    name
                    isActive
                }
            }
        """
        result = graphql_client.query(query)

        assert result.errors is None
        assert len(result.data["contracts"]) == 1
        assert result.data["contracts"][0]["contractId"] == contract.contract_id

    def test_query_contracts_filter_active(self, graphql_client, user):
        active = TrackedContractFactory(owner=user, is_active=True)
        TrackedContractFactory(owner=user, is_active=False)

        query = """
            query {
                contracts(isActive: true) {
                    contractId
                    isActive
                }
            }
        """
        result = graphql_client.query(query)

        assert result.errors is None
        assert len(result.data["contracts"]) == 1
        assert result.data["contracts"][0]["contractId"] == active.contract_id

    def test_query_contract_by_id(self, graphql_client, contract):
        query = """
            query($contractId: String!) {
                contract(contractId: $contractId) {
                    id
                    contractId
                    name
                }
            }
        """
        result = graphql_client.query(query, variables={"contractId": contract.contract_id})

        assert result.errors is None
        assert result.data["contract"]["contractId"] == contract.contract_id

    def test_query_contract_not_found(self, graphql_client):
        query = """
            query {
                contract(contractId: "nonexistent") {
                    id
                }
            }
        """
        result = graphql_client.query(query)

        assert result.errors is None
        assert result.data["contract"] is None

    def test_query_events(self, graphql_client, contract):
        ContractEventFactory.create_batch(3, contract=contract)

        query = """
            query {
                events(limit: 10) {
                    id
                    eventType
                    contractId
                    ledger
                }
            }
        """
        result = graphql_client.query(query)

        assert result.errors is None
        assert len(result.data["events"]) == 3

    def test_query_events_filter_by_contract(self, graphql_client, contract, user):
        other_contract = TrackedContractFactory(owner=user)
        ContractEventFactory.create_batch(2, contract=contract)
        ContractEventFactory.create_batch(3, contract=other_contract)

        query = """
            query($contractId: String!) {
                events(contractId: $contractId) {
                    contractId
                }
            }
        """
        result = graphql_client.query(query, variables={"contractId": contract.contract_id})

        assert result.errors is None
        assert len(result.data["events"]) == 2

    def test_query_events_filter_by_type(self, graphql_client, contract):
        ContractEventFactory.create_batch(2, contract=contract, event_type="swap")
        ContractEventFactory.create_batch(3, contract=contract, event_type="transfer")

        query = """
            query {
                events(eventType: "swap") {
                    eventType
                }
            }
        """
        result = graphql_client.query(query)

        assert result.errors is None
        assert len(result.data["events"]) == 2
        assert all(e["eventType"] == "swap" for e in result.data["events"])

    def test_query_events_pagination(self, graphql_client, contract):
        ContractEventFactory.create_batch(10, contract=contract)

        query = """
            query {
                events(limit: 3, offset: 2) {
                    id
                }
            }
        """
        result = graphql_client.query(query)

        assert result.errors is None
        assert len(result.data["events"]) == 3

    def test_query_events_limit_enforced(self, graphql_client, contract):
        ContractEventFactory.create_batch(1001, contract=contract)

        query = """
            query {
                events(limit: 2000) {
                    id
                }
            }
        """
        result = graphql_client.query(query)

        assert result.errors is None
        assert len(result.data["events"]) <= 1000

    def test_query_events_time_range(self, graphql_client, contract):
        past = timezone.now() - timezone.timedelta(days=10)
        recent = timezone.now() - timezone.timedelta(days=1)

        ContractEventFactory(contract=contract, timestamp=past)
        ContractEventFactory(contract=contract, timestamp=recent)

        query = """
            query($since: DateTime!) {
                events(since: $since) {
                    id
                }
            }
        """
        since = (timezone.now() - timezone.timedelta(days=5)).isoformat()
        result = graphql_client.query(query, variables={"since": since})

        assert result.errors is None
        assert len(result.data["events"]) == 1

    def test_query_event_by_id(self, graphql_client, contract):
        event = ContractEventFactory(contract=contract)

        query = """
            query($id: Int!) {
                event(id: $id) {
                    id
                    eventType
                }
            }
        """
        result = graphql_client.query(query, variables={"id": event.id})

        assert result.errors is None
        assert result.data["event"]["id"] == str(event.id)

    def test_query_contract_stats(self, graphql_client, contract):
        ContractEventFactory.create_batch(5, contract=contract, event_type="swap")
        ContractEventFactory.create_batch(3, contract=contract, event_type="transfer")

        query = """
            query($contractId: String!) {
                contractStats(contractId: $contractId) {
                    contractId
                    name
                    totalEvents
                    uniqueEventTypes
                }
            }
        """
        result = graphql_client.query(query, variables={"contractId": contract.contract_id})

        assert result.errors is None
        assert result.data["contractStats"]["totalEvents"] == 8
        assert result.data["contractStats"]["uniqueEventTypes"] == 2

    def test_query_event_types(self, graphql_client, contract):
        ContractEventFactory(contract=contract, event_type="swap")
        ContractEventFactory(contract=contract, event_type="transfer")
        ContractEventFactory(contract=contract, event_type="swap")

        query = """
            query($contractId: String!) {
                eventTypes(contractId: $contractId)
            }
        """
        result = graphql_client.query(query, variables={"contractId": contract.contract_id})

        assert result.errors is None
        assert set(result.data["eventTypes"]) == {"swap", "transfer"}


@pytest.mark.django_db
class TestGraphQLMutations:
    def test_register_contract(self, graphql_client, user):
        mutation = """
            mutation {
                registerContract(
                    contractId: "CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                    name: "Test Contract"
                    description: "Test"
                ) {
                    contractId
                    name
                }
            }
        """
        result = graphql_client.query(mutation)

        assert result.errors is None
        assert result.data["registerContract"]["name"] == "Test Contract"

    def test_update_contract(self, graphql_client, contract):
        mutation = """
            mutation($contractId: String!) {
                updateContract(
                    contractId: $contractId
                    name: "Updated Name"
                    isActive: false
                ) {
                    contractId
                    name
                    isActive
                }
            }
        """
        result = graphql_client.query(mutation, variables={"contractId": contract.contract_id})

        assert result.errors is None
        assert result.data["updateContract"]["name"] == "Updated Name"
        assert result.data["updateContract"]["isActive"] is False

    def test_update_nonexistent_contract(self, graphql_client):
        mutation = """
            mutation {
                updateContract(
                    contractId: "nonexistent"
                    name: "New Name"
                ) {
                    contractId
                }
            }
        """
        result = graphql_client.query(mutation)

        assert result.errors is None
        assert result.data["updateContract"] is None
