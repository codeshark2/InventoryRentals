import logging
from livekit.agents import llm

from ..services.google_sheets_service import GoogleSheetsDataService
from ..services.verification_service import VerificationService
from ..utils.conversation_state import ConversationState, WorkflowStage
from ..utils.prompts import get_system_prompt
from ..utils.function_tools import format_equipment_for_context

logger = logging.getLogger("rental-agent")
logger.setLevel(logging.INFO)


class RentalAgent:
    """Main voice agent for equipment rental system."""
    
    def __init__(self):
        self.data_service = GoogleSheetsDataService()
        self.verification_service = VerificationService()
        self.state = ConversationState()
        self.agent = None
        
    def set_agent(self, agent):
        """Store reference to the Agent instance."""
        self.agent = agent
    
    def get_current_instructions(self) -> str:
        """Get current stage instructions."""
        context = self._get_stage_context()
        return get_system_prompt(self.state.stage, context)
    
    def _get_stage_context(self) -> dict:
        """Get context data for current stage."""
        context = {}
        
        if self.state.stage == WorkflowStage.REQUIREMENTS_CONFIRMATION:
            if self.state.selected_equipment:
                eq = self.state.selected_equipment
                context['selected_equipment'] = eq['Equipment Name']
                context['cert_required'] = eq['Operator Cert Required']
                context['weight_class'] = eq['Weight Class']
        
        elif self.state.stage == WorkflowStage.PRICING_NEGOTIATION:
            if self.state.selected_equipment:
                eq = self.state.selected_equipment
                context['daily_rate'] = eq['Daily Rate']
                context['max_rate'] = eq['Max Rate']
                context['negotiation_attempts'] = self.state.negotiation_attempts
                context['max_attempts'] = self.state.max_negotiation_attempts
        
        elif self.state.stage == WorkflowStage.OPERATOR_CERTIFICATION:
            if self.state.selected_equipment:
                context['cert_required'] = self.state.selected_equipment['Operator Cert Required']
        
        elif self.state.stage == WorkflowStage.INSURANCE_VERIFICATION:
            if self.state.selected_equipment:
                context['min_insurance'] = self.state.selected_equipment['Min Insurance']
        
        return context
    
    async def _update_instructions(self):
        """Update agent instructions for new stage."""
        if not self.agent:
            return
        
        new_instructions = self.get_current_instructions()
        
        # Update agent instructions using the update_instructions method
        await self.agent.update_instructions(new_instructions)
        
        logger.info(f"Updated instructions for stage: {self.state.stage.value}")
    
    # Tool functions with @llm.function_tool decorator
    
    @llm.function_tool()
    async def verify_business_license(self, license_number: str):
        """
        Verify customer's business license with state authorities.
        
        Args:
            license_number: The business license number provided by the customer
        """
        
        logger.info(f"Verifying business license: {license_number}")
        
        success, message = await self.verification_service.verify_business_license(license_number)
        
        if success:
            self.state.business_license = license_number
            self.state.customer_verified = True
            self.state.business_name = "Metro Construction LLC"
            self.state.advance_stage()
            
            await self._update_instructions()
            
            return f"Business license verified. Customer: {self.state.business_name}"
        else:
            self.state.end_call("failed_license_verification")
            return "License verification failed. Cannot proceed with rental."
    
    @llm.function_tool()
    async def search_available_equipment(self, search_query: str):
        """
        Search for available equipment based on customer needs.
        
        Args:
            search_query: Natural language search query from customer (e.g., 'excavator for foundation work', 'forklift under $400')
        """
        
        logger.info(f"Searching equipment: {search_query}")
        
        available_equipment = await self.data_service.get_available_equipment()
        formatted = format_equipment_for_context(available_equipment)
        
        return f"Found {len(available_equipment)} available equipment:\n\n{formatted}"
    
    @llm.function_tool()
    async def select_equipment(self, equipment_id: str):
        """
        Select specific equipment by ID after customer chooses.
        
        Args:
            equipment_id: The equipment ID (e.g., EQ001)
        """
        
        logger.info(f"Selecting equipment: {equipment_id}")
        
        equipment = await self.data_service.get_equipment_by_id(equipment_id)
        
        if not equipment:
            return f"Equipment {equipment_id} not found."
        
        if equipment['Status'] != 'AVAILABLE':
            return f"Equipment {equipment_id} is not available (Status: {equipment['Status']})."
        
        self.state.selected_equipment = equipment
        self.state.equipment_id = equipment_id
        self.state.advance_stage()
        
        await self._update_instructions()
        
        return f"Selected: {equipment['Equipment Name']} at ${equipment['Daily Rate']}/day. Location: {equipment['Storage Location']}"
    
    @llm.function_tool()
    async def verify_site_safety(self, job_address: str):
        """
        Verify job site can safely accommodate selected equipment.
        
        Args:
            job_address: The job site address provided by customer
        """
        
        logger.info(f"Verifying site safety: {job_address}")
        
        if not self.state.selected_equipment:
            return "No equipment selected yet."
        
        equipment = self.state.selected_equipment
        
        success, message = await self.verification_service.verify_site_safety(
            job_address,
            equipment['Category'],
            equipment['Weight Class']
        )
        
        if success:
            self.state.job_address = job_address
            self.state.site_verified = True
            self.state.advance_stage()
            
            await self._update_instructions()
            
            return f"Site verified for {equipment['Weight Class']} equipment at {job_address}."
        else:
            self.state.end_call("failed_site_verification")
            return "Site does not meet safety requirements. Cannot proceed."
    
    @llm.function_tool()
    async def propose_price(self, proposed_daily_rate: float, rental_days: int = 1):
        """
        Propose a negotiated price for the equipment rental.
        
        Args:
            proposed_daily_rate: The proposed daily rental rate
            rental_days: Number of days for rental (default: 1)
        """
        
        logger.info(f"Price proposal: ${proposed_daily_rate}/day for {rental_days} days")
        
        if not self.state.selected_equipment:
            return "No equipment selected."
        
        equipment = self.state.selected_equipment
        min_rate = float(equipment['Daily Rate'])
        max_rate = float(equipment['Max Rate'])
        
        self.state.negotiation_attempts += 1
        self.state.rental_days = rental_days
        
        if proposed_daily_rate < min_rate:
            if self.state.negotiation_attempts >= self.state.max_negotiation_attempts:
                self.state.end_call("failed_negotiation")
                return f"Cannot negotiate below ${min_rate}/day. Maximum attempts reached. Thank you for your interest."
            return f"Rate ${proposed_daily_rate}/day is below our minimum of ${min_rate}/day. Can you work with a higher rate?"
        
        if proposed_daily_rate > max_rate:
            return f"Rate ${proposed_daily_rate}/day exceeds our maximum of ${max_rate}/day."
        
        # Price within range
        self.state.agreed_daily_rate = proposed_daily_rate
        
        return f"Rate of ${proposed_daily_rate}/day for {rental_days} days is acceptable. Total would be ${proposed_daily_rate * rental_days}. Please confirm this rate to proceed."
    
    @llm.function_tool()
    async def accept_price(self, confirmed_daily_rate: float):
        """
        Accept the agreed price and move to operator verification.
        
        Args:
            confirmed_daily_rate: The confirmed daily rental rate
        """
        
        logger.info(f"Price accepted: ${confirmed_daily_rate}/day")
        
        self.state.agreed_daily_rate = confirmed_daily_rate
        self.state.advance_stage()
        
        await self._update_instructions()
        
        total = confirmed_daily_rate * (self.state.rental_days or 1)
        
        return f"Price confirmed at ${confirmed_daily_rate}/day. Total cost: ${total}. Now let's verify your operator credentials."
    
    @llm.function_tool()
    async def verify_operator_credentials(self, operator_name: str, operator_license: str, operator_phone: str):
        """
        Verify operator has proper certifications for selected equipment.
        
        Args:
            operator_name: Name of the equipment operator
            operator_license: Operator's license/certification number
            operator_phone: Operator's contact phone number
        """
        
        logger.info(f"Verifying operator: {operator_name}, license: {operator_license}")
        
        if not self.state.selected_equipment:
            return "No equipment selected."
        
        equipment = self.state.selected_equipment
        required_cert = equipment['Operator Cert Required']
        
        success, message = await self.verification_service.verify_operator_credentials(
            operator_license,
            required_cert
        )
        
        if success:
            self.state.operator_name = operator_name
            self.state.operator_license = operator_license
            self.state.operator_phone = operator_phone
            self.state.operator_verified = True
            self.state.advance_stage()
            
            await self._update_instructions()
            
            return f"Operator {operator_name} verified for {required_cert}. Phone: {operator_phone}"
        else:
            self.state.end_call("failed_operator_verification")
            return "Operator credentials could not be verified. Cannot proceed with rental."
    
    @llm.function_tool()
    async def verify_insurance_coverage(self, policy_number: str):
        """
        Verify customer's insurance meets minimum requirements for selected equipment.
        
        Args:
            policy_number: Insurance policy number
        """
        
        logger.info(f"Verifying insurance: {policy_number}")
        
        if not self.state.selected_equipment:
            return "No equipment selected."
        
        equipment = self.state.selected_equipment
        required_amount = equipment['Min Insurance']
        equipment_value = str(int(float(equipment['Daily Rate']) * 100))
        
        success, message = await self.verification_service.verify_insurance_coverage(
            policy_number,
            required_amount,
            equipment_value
        )
        
        if success:
            self.state.insurance_policy = policy_number
            self.state.insurance_verified = True
            self.state.advance_stage()
            
            await self._update_instructions()
            
            return f"Insurance policy {policy_number} verified with ${required_amount} coverage."
        else:
            self.state.end_call("failed_insurance_verification")
            return "Insurance coverage is insufficient. Cannot proceed with rental."
    
    @llm.function_tool()
    async def complete_booking(self):
        """Finalize the rental booking and update inventory."""
        
        logger.info("Completing booking...")
        
        if not self.state.selected_equipment:
            return "No equipment selected."
        
        equipment_id = self.state.equipment_id
        
        # Atomic check-and-update
        success = await self.data_service.update_equipment_status(equipment_id, "RENTED")
        
        if not success:
            return f"Sorry, {self.state.selected_equipment['Equipment Name']} was just booked by another customer. Let me show you alternatives."
        
        # Booking successful
        self.state.booking_confirmed = True
        self.state.booking_reference = f"BK{equipment_id}-{self.state.business_license}"
        
        equipment = self.state.selected_equipment
        total_cost = self.state.agreed_daily_rate * (self.state.rental_days or 1)
        
        return f"""Booking confirmed!

Reference Number: {self.state.booking_reference}
Equipment: {equipment['Equipment Name']} ({equipment_id})
Daily Rate: ${self.state.agreed_daily_rate}
Rental Period: {self.state.rental_days or 1} days
Total Cost: ${total_cost}
Pickup Location: {equipment['Storage Location']}
Operator Required: {equipment['Operator Cert Required']}

You'll receive email confirmation shortly. Is there anything else I can help you with?"""
    
    @llm.function_tool()
    async def end_call(self, reason: str = "completed"):
        """
        End the call gracefully with a reason.
        
        Args:
            reason: Reason for ending the call (e.g., 'completed', 'failed_verification', 'no_equipment')
        """
        
        logger.info(f"Ending call: {reason}")
        
        self.state.end_call(reason)
        
        return "Thank you for contacting Metro Equipment Rentals. Have a great day!"
