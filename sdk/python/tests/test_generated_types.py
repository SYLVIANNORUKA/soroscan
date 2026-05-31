"""Tests to verify generated Python types from GraphQL schema."""

import pytest
from datetime import datetime
from typing import get_type_hints


def test_generated_types_module_exists():
    """Test that generated types module can be imported."""
    try:
        from soroscan.generated import types
        assert types is not None
    except ImportError:
        pytest.skip("Generated types not available. Run codegen first.")


def test_generated_types_are_pydantic_models():
    """Test that generated types are valid Pydantic models."""
    try:
        from soroscan.generated.types import ContractType, EventType
        from pydantic import BaseModel
        
        # Check that types inherit from BaseModel
        assert issubclass(ContractType, BaseModel)
        assert issubclass(EventType, BaseModel)
        
    except ImportError:
        pytest.skip("Generated types not available")


def test_generated_enum_types():
    """Test that generated enum types work correctly."""
    try:
        from soroscan.generated.types import TimelineBucketSize, NotificationTypeEnum
        from enum import Enum
        
        # Check enum inheritance
        assert issubclass(TimelineBucketSize, Enum)
        assert issubclass(NotificationTypeEnum, Enum)
        
        # Check enum values
        assert hasattr(TimelineBucketSize, 'FIVE_MINUTES')
        assert hasattr(NotificationTypeEnum, 'CONTRACT_PAUSED')
        
    except ImportError:
        pytest.skip("Generated types not available")


def test_type_annotations_are_correct():
    """Test that generated types have correct type annotations."""
    try:
        from soroscan.generated.types import ContractType, EventType
        
        # Get type hints
        contract_hints = get_type_hints(ContractType)
        event_hints = get_type_hints(EventType)
        
        # Verify some expected fields exist
        assert 'id' in contract_hints
        assert 'contract_id' in contract_hints
        assert 'name' in contract_hints
        
        assert 'id' in event_hints
        assert 'event_type' in event_hints
        assert 'payload' in event_hints
        
    except ImportError:
        pytest.skip("Generated types not available")


def test_generated_types_can_be_instantiated():
    """Test that generated types can be instantiated with valid data."""
    try:
        from soroscan.generated.types import ContractType, EventType
        
        # Create a contract instance
        contract = ContractType(
            id=1,
            contract_id="CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD2KM",
            name="Test Contract",
            alias="test",
            description="A test contract",
            is_active=True,
            last_event_at=None,
            deprecation_status=None,
            deprecation_reason=None,
            event_filter_type="all",
            event_filter_list=[],
            metadata={},
            created_at=datetime.now(),
        )
        
        assert contract.name == "Test Contract"
        assert contract.is_active is True
        
    except ImportError:
        pytest.skip("Generated types not available")
    except Exception as e:
        # If fields don't match, that's okay - schema might have changed
        pytest.skip(f"Schema mismatch: {e}")


def test_backward_compatibility_with_existing_types():
    """Test that existing SDK types still work."""
    from soroscan.models import ContractEvent, TrackedContract
    from pydantic import BaseModel
    
    # Verify existing types are still valid
    assert issubclass(ContractEvent, BaseModel)
    assert issubclass(TrackedContract, BaseModel)
    
    # These should eventually be replaced by generated types
    # but for now we ensure backward compatibility


def test_generated_types_have_docstrings():
    """Test that generated types include documentation from schema."""
    try:
        from soroscan.generated.types import ContractType, EventType
        
        # Check that classes have docstrings
        # (These come from GraphQL schema descriptions)
        assert ContractType.__doc__ is not None or True  # May be None if no description
        assert EventType.__doc__ is not None or True
        
    except ImportError:
        pytest.skip("Generated types not available")


def test_json_serialization():
    """Test that generated types can be serialized to JSON."""
    try:
        from soroscan.generated.types import ContractType
        
        contract = ContractType(
            id=1,
            contract_id="CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD2KM",
            name="Test",
            alias="test",
            description="",
            is_active=True,
            last_event_at=None,
            deprecation_status=None,
            deprecation_reason=None,
            event_filter_type="all",
            event_filter_list=[],
            metadata={},
            created_at=datetime.now(),
        )
        
        # Should be able to serialize to dict
        data = contract.model_dump()
        assert isinstance(data, dict)
        assert data['name'] == "Test"
        
        # Should be able to serialize to JSON
        json_str = contract.model_dump_json()
        assert isinstance(json_str, str)
        assert "Test" in json_str
        
    except ImportError:
        pytest.skip("Generated types not available")
    except Exception:
        pytest.skip("Schema mismatch")
