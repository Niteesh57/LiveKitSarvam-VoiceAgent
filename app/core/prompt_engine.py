"""
Prompt engine — loads and hydrates the system prompt with runtime variables.
Supports multi-language instructions for Hindi, English, Marathi, and mixed modes.
Injects customer memory context for personalized conversations.
"""

from pathlib import Path

from .context import get_runtime_context

PROMPT_FILE = Path(__file__).parent.parent.parent / "prompts" / "system_prompt.md"


class PromptEngine:
    """Loads the system prompt template and injects runtime variables."""

    @staticmethod
    def get_prompt(customer_name: str, customer_phone: str, customer_memory: str = "") -> str:
        """
        Build the fully hydrated system prompt for a specific customer call.

        Args:
            customer_name: Customer's display name
            customer_phone: Customer's phone number with country code
            customer_memory: Formatted previous conversation history (optional)

        Returns:
            Complete system prompt string with all variables replaced
        """
        if not PROMPT_FILE.exists():
            raise FileNotFoundError(
                f"System prompt not found at {PROMPT_FILE}. "
                "Ensure prompts/system_prompt.md exists."
            )

        template = PROMPT_FILE.read_text(encoding="utf-8")
        ctx = get_runtime_context()

        # Format customer memory section
        if customer_memory:
            memory_section = (
                f"This is a returning customer. Previous interaction details:\n{customer_memory}\n"
                "Use this context to personalize the conversation — reference what they mentioned before."
            )
        else:
            memory_section = "This is the first call with this customer. No previous history available."

        replacements = {
            "{{customer_name}}": customer_name,
            "{{customer_phone}}": customer_phone,
            "{{broker_name}}": ctx["broker_name"],
            "{{agency_name}}": ctx["agency_name"],
            "{{office_address}}": ctx["office_address"],
            "{{broker_phone}}": ctx["broker_phone"],
            "{{slot_1}}": ctx["slot_1"],
            "{{slot_2}}": ctx["slot_2"],
            "{{today_human}}": ctx["today_human"],
            "{{customer_memory}}": memory_section,
        }

        prompt = template
        for placeholder, value in replacements.items():
            prompt = prompt.replace(placeholder, value)

        return prompt
