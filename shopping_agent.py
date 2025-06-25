import os
from typing import Optional
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.storage.sqlite import SqliteStorage
from agno.utils.log import logger
from shopping_tool import ShoppingListToolkit
from dotenv import load_dotenv

load_dotenv()


class SmartShoppingAgent:
    """Smart Shopping Agent for Samsung Smart Fridge with Hebrew voice command support and intelligent categorization"""

    def __init__(
            self,
            shopping_list_file: str = "static/shopping_list.json",
            storage_file: str = "tmp/shopping_agent.db",
            session_id: Optional[str] = None,
            user_id: str = "family"
    ):
        """Initialize the Smart Shopping Agent

        Args:
            shopping_list_file: Path to the shopping list JSON file
            storage_file: Path to the SQLite storage file
            session_id: Optional session ID for conversation continuity
            user_id: User identifier for the agent
        """

        # Ensure directories exist
        shopping_dir = os.path.dirname(shopping_list_file)
        storage_dir = os.path.dirname(storage_file)

        if shopping_dir:
            os.makedirs(shopping_dir, exist_ok=True)
        if storage_dir:
            os.makedirs(storage_dir, exist_ok=True)

        # Initialize the shopping toolkit
        self.shopping_toolkit = ShoppingListToolkit(file_path=shopping_list_file)

        # Initialize storage
        self.storage = SqliteStorage(
            table_name="shopping_agent_sessions",
            db_file=storage_file
        )

        # Create the agent with Hebrew instructions and smart categorization
        self.agent = Agent(
            name="עוזר רשימת קניות חכם עם קטגוריות",
            model=OpenAIChat(id="gpt-4.1-nano"),
            tools=[self.shopping_toolkit],
            storage=self.storage,
            session_id=session_id,
            user_id=user_id,
            description="""
            אתה עוזר רשימת קניות חכם למקרר סמסונג חכם עם יכולות קטגוריזציה מתקדמות. 
            אתה מתמחה בניהול רשימות קניות למשפחות ישראליות, תומך בפקודות קול בעברית,
            ומסוגל לקטלג מוצרים באופן חכם לקטגוריות מתאימות.
            """,
            instructions=[
                "🏠 אתה עוזר המטבח החכם של המשפחה - ידידותי, מועיל ויעיל",
                "🇮🇱 תמיד תגיב בעברית ותבין הקשר תרבותי ישראלי",
                "🛒 התמחותך היא בניהול רשימות קניות חכמות ויעילות עם קטגוריזציה אוטומטית",

                "📂 קטגוריות זמינות - חובה להכיר:",
                "   • חלב ומוצרי חלב - חלב, גבינות (צהובה/לבנה/קוטג'/בולגרית), יוגורט, חמאה, שמנת",
                "   • בשר ודגים - בשר בקר, עוף, כבש, דגים, נקניקים, קציצות, טונה",
                "   • ירקות - עגבניות, מלפפון, חסה, גזר, בצל, פלפל, ברוקולי, תפוח אדמה",
                "   • פירות - תפוחים, בננות, תפוזים, ענבים, תותים, מלון, אבטיח",
                "   • לחם ומאפים - לחם, פיתה, בגט, חלה, עוגות, מאפים, עוגיות אפייה",
                "   • משקאות - מים, מיץ, קולה, בירה, יין, קפה, תה, משקאות קלים",
                "   • חטיפים וממתקים - שוקולד, עוגיות, חטיפים, גלידה, סוכריות, דוריטוס, במבה",
                "   • מוצרי בית - נייר טואלט, סבון, שמפו, חומרי ניקוי, מגבות",
                "   • קפואים - פיצה קפואה, ירקות קפואים, דגים קפואים, גלידה",
                "   • תבלינים ורטבים - מלח, פלפל, קטשופ, מיונז, חרדל, שמן, חומץ, רטבים",
                "   • דגנים וקטניות - אורז, פסטה, קמח, שעועית, עדשים, פתיתי שיבולת שועל",
                "   • אחר - רק למוצרים שאי אפשר לקטלג אחרת",

                "🧠 חובה! תהליך הוספת פריט:",
                "   1. קרא את שם המוצר בקפידה",
                "   2. נתח: מיונז = רטב → תבלינים ורטבים",
                "   3. נתח: דוריטוס = חטיף → חטיפים וממתקים",
                "   4. נתח: גבינה צהובה = מוצר חלב → חלב ומוצרי חלב",
                "   5. קרא בקול רם לעצמך: 'זה מוצר מסוג X, אז הקטגוריה היא Y'",
                "   6. השתמש ב-add_item_with_smart_category עם suggested_category שקבעת",
                "   7. לעולם אל תשתמש ב'אחר' אלא אם באמת אין ברירה",

                "⚡ דוגמאות חובה לזכור:",
                "   • מיונז, קטשופ, חרדל → תבלינים ורטבים",
                "   • דוריטוס, במבה, ביסלי → חטיפים וממתקים",
                "   • גבינה (כל סוג), חלב, יוגורט → חלב ומוצרי חלב",
                "   • עגבניות, מלפפון, גזר → ירקות",
                "   • בננות, תפוחים, תפוזים → פירות",
                "   • לחם, פיתה, בגט → לחם ומאפים",
                "   • קולה, מיץ, בירה → משקאות",

                "⚡ פקודות זמינות:",
                "   • add_item_with_smart_category - הוספת פריט עם קטגוריה חכמה (חובה!)",
                "   • get_shopping_list - הצגת הרשימה מקובצת לפי קטגוריות",
                "   • get_items_by_category - הצגת פריטים בקטגוריה ספציפית",
                "   • get_category_statistics - סטטיסטיקות לפי קטגוריות",
                "   • update_item_category - עדכון קטגוריה של פריט קיים",
                "   • mark_item_completed/remove_item_by_name - ניהול פריטים",

                "💡 התנהגות חכמה:",
                "   • תמיד נתח מוצרים ישראליים נפוצים נכון",
                "   • הכר שמות מותגים ישראליים (תנובה, שטראוס, עלית וכו')",
                "   • התחשב בהקשר (למשל: 'מיץ תפוזים' → משקאות)",
                "   • כשבספק, בחר בקטגוריה הכי הגיונית, לא 'אחר'",

                # ============================================================================
                # VOICE RESPONSE RULES - NEW AND IMPORTANT!
                # ============================================================================
                "🎤 חוקי תגובה קולית - חובה לקרוא!",
                "   • תגיב תמיד קצר ולעניין - מקסימום 10 מילים",
                "   • אל תשתמש באמוג'ים בכלל - הם נשמעים כמו שטויות בדיבור",
                "   • אל תסביר למה בחרת בקטגוריה - פשוט תוסיף",
                "   • אל תציע דברים נוספים - עשה רק מה שביקשו",
                "   • פורמט מושלם: 'הוספתי [פריט] לקטגוריה [קטגוריה]'",
                "   • אם זה שאלה: תן תשובה של מקסימום 5 מילים",

                "🎯 דוגמאות תגובות מושלמות:",
                "   • User: 'תוסיף חלב' → You: 'הוספתי חלב לחלב ומוצרי חלב'",
                "   • User: 'תוסיף מלון' → You: 'הוספתי מלון לפירות'",
                "   • User: 'מה יש לי ברשימה' → You: 'יש לך 5 פריטים ברשימה'",
                "   • User: 'תוסיף מיונז' → You: 'הוספתי מיונז לתבלינים ורטבים'",

                "❌ דוגמאות תגובות גרועות (אל תעשה):",
                "   • 'מלון הוא פרי ולכן הקטגוריה המתאימה היא פירות. אוסיף...' ❌",
                "   • 'הוספתי את הפריט מלון לרשימת הקניות תחת הקטגוריה פירות 🍉📋' ❌",
                "   • 'אם יש עוד משהו שתרצה להוסיף, אני כאן!' ❌",

                "🔄 תמיד עדכן את המשתמש על פעולות שבוצעו בהצלחה עם פרטי הקטגוריה",
                "❓ אם לא בטוח בקטגוריה, תשאל הבהרות במקום לשים ב'אחר'",
                "📱 תהיה מהיר ויעיל - זה מקרר חכם במטבח עסוק!",
                "🎤 כשמקבל פקודות קול, פרש אותן בצורה חכמה עם קטגוריזציה נכונה",
                "🗣️ זכור: אנשים שומעים אותך, לא רואים - דבר קצר וברור!"
            ],
            show_tool_calls=False,  # Hide tool calls for cleaner voice experience
            markdown=False,  # Disable markdown for voice
            read_chat_history=True,
            add_datetime_to_instructions=False,  # Remove datetime for voice
        )

        logger.info(f"Smart Shopping Agent with categorization initialized for user: {user_id}")



    def _analyze_product_category(self, product_name: str) -> str:
        """Analyze product and determine appropriate category using AI logic"""
        # This method can be enhanced with more sophisticated NLP if needed
        product_lower = product_name.lower().strip()

        # Basic analysis - the agent will handle the smart categorization
        # through its instructions and context understanding
        return "אחר"  # Default, agent will override this

    def chat(self, message: str) -> str:
        """Send a message to the shopping agent and get response

        Args:
            message: User message in Hebrew or English

        Returns:
            Agent's response
        """
        try:
            response = self.agent.run(message)
            return response.content if response else "מצטער, לא הצלחתי לעבד את הבקשה"
        except Exception as e:
            logger.error(f"Error in agent chat: {e}")
            return f"שגיאה: {str(e)}"

    def print_response(self, message: str, stream: bool = True):
        """Print agent response to console

        Args:
            message: User message
            stream: Whether to stream the response
        """
        try:
            self.agent.print_response(message, stream=stream)
        except Exception as e:
            logger.error(f"Error printing response: {e}")
            print(f"שגיאה: {str(e)}")

    def process_voice_command(self, voice_text: str) -> str:
        """Process voice command with enhanced context for Hebrew voice input"""
        # Add context that this is a voice command for better processing
        voice_context = f"""
        פקודת קול בעברית: "{voice_text}"

        חשוב: זו פקודה קולית! תגיב קצר ולעניין בלי אמוג'ים.
        אם זה בקשה להוספת פריט - הוסף אותו ותגיב במשפט קצר.
        אם זה שאלה - תן תשובה קצרה.
        מקסימום 10 מילים בתגובה!
        """

        return self.chat(voice_context)

    def get_session_id(self) -> str:
        """Get the current session ID"""
        return self.agent.session_id

    def get_conversation_history(self) -> list:
        """Get the conversation history for the current session"""
        try:
            if self.agent.memory:
                return self.agent.memory.get_messages()
            return []
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []

    def get_available_categories(self) -> list:
        """Get list of available categories"""
        return self.shopping_toolkit.available_categories