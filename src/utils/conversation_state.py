from enum import Enum
from typing import Optional, Dict
from dataclasses import dataclass, field


class WorkflowStage(Enum):
    """Stages of the rental workflow."""
    GREETING = "greeting"
    CUSTOMER_VERIFICATION = "customer_verification"
    EQUIPMENT_DISCOVERY = "equipment_discovery"
    REQUIREMENTS_CONFIRMATION = "requirements_confirmation"
    PRICING_NEGOTIATION = "pricing_negotiation"
    OPERATOR_CERTIFICATION = "operator_certification"
    INSURANCE_VERIFICATION = "insurance_verification"
    BOOKING_COMPLETION = "booking_completion"
    CALL_ENDED = "call_ended"


@dataclass
class ConversationState:
    """Tracks the state of the rental conversation."""
    
    # Current stage
    stage: WorkflowStage = WorkflowStage.GREETING
    
    # Customer information
    business_license: Optional[str] = None
    business_name: Optional[str] = None
    customer_verified: bool = False
    
    # Equipment selection
    selected_equipment: Optional[Dict] = None
    equipment_id: Optional[str] = None
    
    # Requirements
    job_address: Optional[str] = None
    site_verified: bool = False
    
    # Pricing
    agreed_daily_rate: Optional[float] = None
    rental_days: Optional[int] = None
    negotiation_attempts: int = 0
    max_negotiation_attempts: int = 3
    
    # Operator information
    operator_name: Optional[str] = None
    operator_license: Optional[str] = None
    operator_phone: Optional[str] = None
    operator_verified: bool = False
    
    # Insurance
    insurance_policy: Optional[str] = None
    insurance_verified: bool = False
    
    # Booking
    booking_confirmed: bool = False
    booking_reference: Optional[str] = None
    
    # Conversation context
    context_data: Dict = field(default_factory=dict)
    
    def can_proceed_to_next_stage(self) -> bool:
        """Check if current stage requirements are met."""
        if self.stage == WorkflowStage.GREETING:
            return True
        
        elif self.stage == WorkflowStage.CUSTOMER_VERIFICATION:
            return self.customer_verified
        
        elif self.stage == WorkflowStage.EQUIPMENT_DISCOVERY:
            return self.selected_equipment is not None
        
        elif self.stage == WorkflowStage.REQUIREMENTS_CONFIRMATION:
            return self.site_verified
        
        elif self.stage == WorkflowStage.PRICING_NEGOTIATION:
            return self.agreed_daily_rate is not None
        
        elif self.stage == WorkflowStage.OPERATOR_CERTIFICATION:
            return self.operator_verified
        
        elif self.stage == WorkflowStage.INSURANCE_VERIFICATION:
            return self.insurance_verified
        
        return False
    
    def advance_stage(self) -> bool:
        """Move to next workflow stage if requirements are met."""
        if not self.can_proceed_to_next_stage():
            return False
        
        stage_order = [
            WorkflowStage.GREETING,
            WorkflowStage.CUSTOMER_VERIFICATION,
            WorkflowStage.EQUIPMENT_DISCOVERY,
            WorkflowStage.REQUIREMENTS_CONFIRMATION,
            WorkflowStage.PRICING_NEGOTIATION,
            WorkflowStage.OPERATOR_CERTIFICATION,
            WorkflowStage.INSURANCE_VERIFICATION,
            WorkflowStage.BOOKING_COMPLETION,
        ]
        
        current_index = stage_order.index(self.stage)
        if current_index < len(stage_order) - 1:
            self.stage = stage_order[current_index + 1]
            return True
        
        return False
    
    def end_call(self, reason: str = "completed"):
        """Mark the call as ended."""
        self.stage = WorkflowStage.CALL_ENDED
        self.context_data['end_reason'] = reason

