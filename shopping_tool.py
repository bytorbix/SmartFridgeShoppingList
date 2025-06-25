import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Any
import uuid
from agno.tools import Toolkit
from agno.utils.log import logger


class ShoppingListToolkit(Toolkit):
    """Agno toolkit for managing smart shopping lists with category tags and real-time synchronization"""

    def __init__(self, file_path: str = "static/shopping_list.json"):
        super().__init__(name="shopping_list_toolkit")
        self.file_path = file_path

        # Available categories for smart categorization
        self.available_categories = [
            "חלב ומוצרי חלב",
            "בשר ודגים",
            "ירקות",
            "פירות",
            "לחם ומאפים",
            "משקאות",
            "חטיפים וממתקים",
            "מוצרי בית",
            "קפואים",
            "תבלינים ורטבים",
            "דגנים וקטניות",
            "אחר"
        ]

        self.ensure_file_exists()
        self.register(self.add_item)
        self.register(self.add_item_with_smart_category)
        self.register(self.clear_completed_items)
        self.register(self.clear_shopping_list)
        self.register(self.get_available_categories)
        self.register(self.get_items_by_category)
        self.register(self.mark_item_completed)
        self.register(self.get_shopping_stats)
        self.register(self.remove_item_by_name)
        self.register(self.search_items)
        self.register(self.update_item_category)
        self.register(self.update_item_quantity)

    def ensure_file_exists(self):
        """Ensure the shopping list file exists"""
        if not os.path.exists(self.file_path):
            dir_path = os.path.dirname(self.file_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)

            empty_list = {
                "items": [],
                "last_modified": datetime.now().isoformat()
            }
            self._save_data(empty_list)

    def _load_data(self) -> Dict:
        """Load data from JSON file"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Ensure all items have tags
                for item in data.get("items", []):
                    if "tag" not in item:
                        item["tag"] = "אחר"
                return data
        except Exception as e:
            logger.error(f"Error loading shopping list data: {e}")
            return {
                "items": [],
                "last_modified": datetime.now().isoformat()
            }

    def _save_data(self, data: Dict) -> bool:
        """Save data to JSON file"""
        try:
            data["last_modified"] = datetime.now().isoformat()
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info("Shopping list data saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving shopping list data: {e}")
            return False

    def get_available_categories(self) -> str:
        """Get list of available categories for categorization

        Returns:
            str: List of available categories in Hebrew
        """
        categories_text = "הקטגוריות הזמינות הן:\n"
        for i, category in enumerate(self.available_categories, 1):
            categories_text += f"{i}. {category}\n"

        return categories_text

    def get_shopping_list(self) -> str:
        """Get all items in the shopping list grouped by categories

        Returns:
            str: JSON string containing all shopping list items organized by categories
        """
        try:
            data = self._load_data()
            items = data.get("items", [])

            if not items:
                return "הרשימה ריקה כרגע. אין פריטים ברשימת הקניות."

            # Group items by category
            categories = {}
            for item in items:
                category = item.get("tag", "אחר")
                if category not in categories:
                    categories[category] = {"pending": [], "completed": []}

                status = "completed" if item.get("completed", False) else "pending"
                item_text = f"• {item['name']} - כמות: {item['quantity']}"
                categories[category][status].append(item_text)

            # Format the response
            response = f"רשימת הקניות מכילה {len(items)} פריטים:\n\n"

            for category, category_items in categories.items():
                if category_items["pending"] or category_items["completed"]:
                    response += f"📂 {category}:\n"

                    if category_items["pending"]:
                        response += "   ⏳ ממתינים:\n"
                        for item in category_items["pending"]:
                            response += f"   {item}\n"

                    if category_items["completed"]:
                        response += "   ✅ הושלמו:\n"
                        for item in category_items["completed"]:
                            response += f"   {item}\n"

                    response += "\n"

            return response

        except Exception as e:
            logger.error(f"Error getting shopping list: {e}")
            return f"שגיאה בקבלת רשימת הקניות: {str(e)}"

    def add_item_with_smart_category(self, name: str, quantity: str = "1", suggested_category: str = None) -> str:
        """Add a new item to the shopping list with intelligent category assignment

        Args:
            name (str): Name of the item to add
            quantity (str): Quantity of the item (default: "1")
            suggested_category (str): AI-suggested category based on item analysis

        Returns:
            str: Success or error message in Hebrew with category information
        """
        try:
            if not name or not name.strip():
                return "שגיאה: שם הפריט לא יכול להיות ריק"

            data = self._load_data()

            # Check if item already exists
            existing_item = None
            for item in data["items"]:
                if item["name"].lower().strip() == name.lower().strip():
                    existing_item = item
                    break

            if existing_item:
                return f"הפריט '{name}' כבר קיים ברשימה בקטגוריה '{existing_item.get('tag', 'אחר')}' עם כמות: {existing_item['quantity']}"

            # Determine category - prioritize AI suggestion
            category = "אחר"  # default
            if suggested_category and suggested_category in self.available_categories:
                category = suggested_category

            # If no valid suggestion provided, the agent should determine this
            # by analyzing the product name in the context of available categories

            new_item = {
                "id": str(uuid.uuid4()),
                "name": name.strip(),
                "quantity": quantity.strip(),
                "completed": False,
                "created_at": datetime.now().isoformat(),
                "tag": category
            }

            data["items"].append(new_item)

            if self._save_data(data):
                logger.info(f"Added item to shopping list: {name} in category: {category}")
                return f"✅ הפריט '{name}' נוסף בהצלחה לרשימת הקניות בקטגוריה '{category}' עם כמות: {quantity}"
            else:
                return "שגיאה בשמירת רשימת הקניות"

        except Exception as e:
            logger.error(f"Error adding item {name}: {e}")
            return f"שגיאה בהוספת הפריט: {str(e)}"

    def add_item(self, name: str, quantity: str = "1") -> str:
        """Add a new item to the shopping list (wrapper for backward compatibility)

        Args:
            name (str): Name of the item to add
            quantity (str): Quantity of the item (default: "1")

        Returns:
            str: Success or error message in Hebrew
        """
        return self.add_item_with_smart_category(name, quantity)

    def get_items_by_category(self, category: str) -> str:
        """Get all items in a specific category

        Args:
            category (str): Category name to filter by

        Returns:
            str: Items in the specified category
        """
        try:
            if category not in self.available_categories:
                return f"קטגוריה לא חוקית: '{category}'. הקטגוריות הזמינות: {', '.join(self.available_categories)}"

            data = self._load_data()
            items = data.get("items", [])

            category_items = [item for item in items if item.get("tag", "אחר") == category]

            if not category_items:
                return f"אין פריטים בקטגוריה '{category}'"

            response = f"פריטים בקטגוריה '{category}' ({len(category_items)} פריטים):\n\n"

            pending_items = []
            completed_items = []

            for item in category_items:
                status = "✅ הושלם" if item.get("completed", False) else "⏳ ממתין"
                item_text = f"• {item['name']} - כמות: {item['quantity']} ({status})"

                if item.get("completed", False):
                    completed_items.append(item_text)
                else:
                    pending_items.append(item_text)

            if pending_items:
                response += "פריטים ממתינים:\n" + "\n".join(pending_items) + "\n\n"

            if completed_items:
                response += "פריטים שהושלמו:\n" + "\n".join(completed_items)

            return response

        except Exception as e:
            logger.error(f"Error getting items by category {category}: {e}")
            return f"שגיאה בקבלת פריטים לפי קטגוריה: {str(e)}"

    def get_category_statistics(self) -> str:
        """Get statistics about items per category

        Returns:
            str: Category statistics in Hebrew
        """
        try:
            data = self._load_data()
            items = data.get("items", [])

            if not items:
                return "רשימת הקניות ריקה - אין סטטיסטיקות קטגוריות להציג"

            category_stats = {}
            for category in self.available_categories:
                category_stats[category] = {"total": 0, "completed": 0, "pending": 0}

            for item in items:
                category = item.get("tag", "אחר")
                if category not in category_stats:
                    category_stats[category] = {"total": 0, "completed": 0, "pending": 0}

                category_stats[category]["total"] += 1
                if item.get("completed", False):
                    category_stats[category]["completed"] += 1
                else:
                    category_stats[category]["pending"] += 1

            response = "📊 סטטיסטיקות לפי קטגוריות:\n\n"

            for category, stats in category_stats.items():
                if stats["total"] > 0:
                    completion_rate = (stats["completed"] / stats["total"] * 100) if stats["total"] > 0 else 0
                    response += f"📂 {category}: {stats['total']} פריטים (✅ {stats['completed']} הושלמו, ⏳ {stats['pending']} ממתינים) - {completion_rate:.1f}% הושלם\n"

            return response

        except Exception as e:
            logger.error(f"Error getting category statistics: {e}")
            return f"שגיאה בקבלת סטטיסטיקות קטגוריות: {str(e)}"

    def remove_item_by_name(self, name: str) -> str:
        """Remove an item from the shopping list by name

        Args:
            name (str): Name of the item to remove

        Returns:
            str: Success or error message in Hebrew
        """
        try:
            if not name or not name.strip():
                return "שגיאה: שם הפריט לא יכול להיות ריק"

            data = self._load_data()
            original_length = len(data["items"])

            # Find and remove the item
            removed_item = None
            for item in data["items"]:
                if item["name"].lower().strip() == name.lower().strip():
                    removed_item = item
                    break

            data["items"] = [item for item in data["items"]
                             if item["name"].lower().strip() != name.lower().strip()]

            if len(data["items"]) == original_length:
                return f"הפריט '{name}' לא נמצא ברשימת הקניות"

            if self._save_data(data):
                category = removed_item.get("tag", "אחר") if removed_item else "לא ידוע"
                logger.info(f"Removed item from shopping list: {name}")
                return f"✅ הפריט '{name}' הוסר בהצלחה מרשימת הקניות (קטגוריה: {category})"
            else:
                return "שגיאה בשמירת רשימת הקניות"

        except Exception as e:
            logger.error(f"Error removing item {name}: {e}")
            return f"שגיאה בהסרת הפריט: {str(e)}"

    def mark_item_completed(self, name: str) -> str:
        """Mark an item as completed in the shopping list

        Args:
            name (str): Name of the item to mark as completed

        Returns:
            str: Success or error message in Hebrew
        """
        try:
            if not name or not name.strip():
                return "שגיאה: שם הפריט לא יכול להיות ריק"

            data = self._load_data()

            for item in data["items"]:
                if item["name"].lower().strip() == name.lower().strip():
                    if item["completed"]:
                        return f"הפריט '{name}' כבר מסומן כהושלם"

                    item["completed"] = True
                    if self._save_data(data):
                        category = item.get("tag", "אחר")
                        logger.info(f"Marked item as completed: {name}")
                        return f"✅ הפריט '{name}' סומן כהושלם (קטגוריה: {category})"
                    else:
                        return "שגיאה בשמירת רשימת הקניות"

            return f"הפריט '{name}' לא נמצא ברשימת הקניות"

        except Exception as e:
            logger.error(f"Error marking item completed {name}: {e}")
            return f"שגיאה בסימון הפריט כהושלם: {str(e)}"

    def mark_item_pending(self, name: str) -> str:
        """Mark an item as pending (not completed) in the shopping list

        Args:
            name (str): Name of the item to mark as pending

        Returns:
            str: Success or error message in Hebrew
        """
        try:
            if not name or not name.strip():
                return "שגיאה: שם הפריט לא יכול להיות ריק"

            data = self._load_data()

            for item in data["items"]:
                if item["name"].lower().strip() == name.lower().strip():
                    if not item["completed"]:
                        return f"הפריט '{name}' כבר מסומן כממתין"

                    item["completed"] = False
                    if self._save_data(data):
                        category = item.get("tag", "אחר")
                        logger.info(f"Marked item as pending: {name}")
                        return f"✅ הפריט '{name}' סומן כממתין (קטגוריה: {category})"
                    else:
                        return "שגיאה בשמירת רשימת הקניות"

            return f"הפריט '{name}' לא נמצא ברשימת הקניות"

        except Exception as e:
            logger.error(f"Error marking item pending {name}: {e}")
            return f"שגיאה בסימון הפריט כממתין: {str(e)}"

    def update_item_category(self, name: str, new_category: str) -> str:
        """Update the category of an existing item

        Args:
            name (str): Name of the item to update
            new_category (str): New category for the item

        Returns:
            str: Success or error message in Hebrew
        """
        try:
            if not name or not name.strip():
                return "שגיאה: שם הפריט לא יכול להיות ריק"

            if new_category not in self.available_categories:
                return f"קטגוריה לא חוקית: '{new_category}'. הקטגוריות הזמינות: {', '.join(self.available_categories)}"

            data = self._load_data()

            for item in data["items"]:
                if item["name"].lower().strip() == name.lower().strip():
                    old_category = item.get("tag", "אחר")
                    item["tag"] = new_category

                    if self._save_data(data):
                        logger.info(f"Updated item category: {name} from {old_category} to {new_category}")
                        return f"✅ הקטגוריה של '{name}' עודכנה מ-'{old_category}' ל-'{new_category}'"
                    else:
                        return "שגיאה בשמירת רשימת הקניות"

            return f"הפריט '{name}' לא נמצא ברשימת הקניות"

        except Exception as e:
            logger.error(f"Error updating item category {name}: {e}")
            return f"שגיאה בעדכון קטגוריית הפריט: {str(e)}"

    def clear_shopping_list(self) -> str:
        """Clear all items from the shopping list

        Returns:
            str: Success or error message in Hebrew
        """
        try:
            data = self._load_data()
            items_count = len(data["items"])

            if items_count == 0:
                return "רשימת הקניות כבר ריקה"

            data = {
                "items": [],
                "last_modified": datetime.now().isoformat()
            }

            if self._save_data(data):
                logger.info(f"Cleared shopping list with {items_count} items")
                return f"✅ רשימת הקניות נוקתה בהצלחה. הוסרו {items_count} פריטים"
            else:
                return "שגיאה בניקוי רשימת הקניות"

        except Exception as e:
            logger.error(f"Error clearing shopping list: {e}")
            return f"שגיאה בניקוי רשימת הקניות: {str(e)}"

    def clear_completed_items(self) -> str:
        """Remove all completed items from the shopping list

        Returns:
            str: Success message with count of removed items in Hebrew
        """
        try:
            data = self._load_data()
            original_length = len(data["items"])

            data["items"] = [item for item in data["items"] if not item.get("completed", False)]
            removed_count = original_length - len(data["items"])

            if removed_count == 0:
                return "אין פריטים מושלמים להסרה"

            if self._save_data(data):
                logger.info(f"Cleared {removed_count} completed items")
                return f"✅ הוסרו {removed_count} פריטים מושלמים מרשימת הקניות"
            else:
                return "שגיאה בהסרת הפריטים המושלמים"

        except Exception as e:
            logger.error(f"Error clearing completed items: {e}")
            return f"שגיאה בהסרת פריטים מושלמים: {str(e)}"

    def search_items(self, query: str) -> str:
        """Search for items in the shopping list by name

        Args:
            query (str): Search query

        Returns:
            str: Search results in Hebrew
        """
        try:
            if not query or not query.strip():
                return "שגיאה: שאילתת החיפוש לא יכולה להיות ריקה"

            data = self._load_data()
            items = data.get("items", [])
            query_lower = query.lower().strip()

            matching_items = [item for item in items
                              if query_lower in item["name"].lower()]

            if not matching_items:
                return f"לא נמצאו פריטים התואמים לחיפוש: '{query}'"

            response = f"נמצאו {len(matching_items)} פריטים התואמים לחיפוש '{query}':\n\n"

            # Group by category
            categories = {}
            for item in matching_items:
                category = item.get("tag", "אחר")
                if category not in categories:
                    categories[category] = []

                status = "✅ הושלם" if item.get("completed", False) else "⏳ ממתין"
                categories[category].append(f"• {item['name']} - כמות: {item['quantity']} ({status})")

            for category, items_list in categories.items():
                response += f"📂 {category}:\n"
                for item_text in items_list:
                    response += f"   {item_text}\n"
                response += "\n"

            return response

        except Exception as e:
            logger.error(f"Error searching items with query {query}: {e}")
            return f"שגיאה בחיפוש פריטים: {str(e)}"

    def get_shopping_stats(self) -> str:
        """Get statistics about the shopping list

        Returns:
            str: Statistics in Hebrew
        """
        try:
            data = self._load_data()
            items = data.get("items", [])
            total_items = len(items)

            if total_items == 0:
                return "רשימת הקניות ריקה - אין סטטיסטיקות להציג"

            completed_items = len([item for item in items if item.get("completed", False)])
            pending_items = total_items - completed_items
            completion_rate = (completed_items / total_items * 100) if total_items > 0 else 0

            # Category breakdown
            category_counts = {}
            for item in items:
                category = item.get("tag", "אחר")
                category_counts[category] = category_counts.get(category, 0) + 1

            response = f"""📊 סטטיסטיקות רשימת הקניות:

📝 סה״כ פריטים: {total_items}
✅ פריטים מושלמים: {completed_items}
⏳ פריטים ממתינים: {pending_items}
📈 אחוז השלמה: {completion_rate:.1f}%

📂 פירוט לפי קטגוריות:"""

            for category, count in sorted(category_counts.items()):
                response += f"\n• {category}: {count} פריטים"

            response += f"\n\nעדכון אחרון: {data.get('last_modified', 'לא ידוע')}"

            return response

        except Exception as e:
            logger.error(f"Error getting shopping stats: {e}")
            return f"שגיאה בקבלת סטטיסטיקות: {str(e)}"

    def update_item_quantity(self, name: str, new_quantity: str) -> str:
        """Update the quantity of an existing item

        Args:
            name (str): Name of the item to update
            new_quantity (str): New quantity for the item

        Returns:
            str: Success or error message in Hebrew
        """
        try:
            if not name or not name.strip():
                return "שגיאה: שם הפריט לא יכול להיות ריק"

            if not new_quantity or not new_quantity.strip():
                return "שגיאה: הכמות החדשה לא יכולה להיות ריקה"

            data = self._load_data()

            for item in data["items"]:
                if item["name"].lower().strip() == name.lower().strip():
                    old_quantity = item["quantity"]
                    item["quantity"] = new_quantity.strip()

                    if self._save_data(data):
                        category = item.get("tag", "אחר")
                        logger.info(f"Updated item quantity: {name} from {old_quantity} to {new_quantity}")
                        return f"✅ הכמות של '{name}' עודכנה מ-{old_quantity} ל-{new_quantity} (קטגוריה: {category})"
                    else:
                        return "שגיאה בשמירת רשימת הקניות"

            return f"הפריט '{name}' לא נמצא ברשימת הקניות"

        except Exception as e:
            logger.error(f"Error updating item quantity {name}: {e}")
            return f"שגיאה בעדכון כמות הפריט: {str(e)}"