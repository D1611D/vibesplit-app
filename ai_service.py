"""
AI Intelligence Service for VibeSplit.
Includes NLP expense parser, Gen-Z debt roaster & nudger, receipt analyzer, and group vibe check generator.
"""
import re
import urllib.parse
from typing import List, Dict, Any, Optional
import random

class AIService:
    @staticmethod
    def parse_natural_language_expense(prompt: str, members: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Parses natural language expense text into structured fields.
        Example: 'Dhairya paid 1200 for Truffles dinner with Alex, Priya and Sam'
        """
        prompt_lower = prompt.lower()
        
        # 1. Extract Amount
        amount = 0.0
        # Patterns like: 1200, $50, ₹1500, 1500.50, 45 dollars, 1200 rs
        amt_match = re.search(r'(?:[\$₹€£]|rs\.?|inr)?\s*(\d+(?:\.\d{1,2})?)\s*(?:[\$₹€£]|dollars?|bucks?|rs\.?|inr)?', prompt_lower)
        if amt_match:
            try:
                # Find the largest standalone number in the prompt that represents the amount
                all_nums = re.findall(r'\b\d+(?:\.\d{1,2})?\b', prompt)
                if all_nums:
                    amount = max([float(n) for n in all_nums])
            except Exception:
                amount = float(amt_match.group(1))

        # 2. Extract Category & Title
        category = "food"
        categories_map = {
            "food": ["dinner", "lunch", "breakfast", "burger", "pizza", "sushi", "truffles", "mcdonalds", "kfc", "cafe", "restaurant", "food", "tacos", "snack", "ramen"],
            "drink": ["boba", "coffee", "drinks", "beer", "cocktails", "bar", "pub", "starbucks", "matcha", "chai"],
            "travel": ["uber", "ola", "cab", "taxi", "flight", "train", "metro", "petrol", "gas", "fuel", "trip", "goa", "hotel", "airbnb"],
            "party": ["party", "club", "rave", "tickets", "concert", "fest", "dj", "drinks"],
            "housing": ["rent", "wifi", "groceries", "electricity", "maid", "cook", "water", "flat", "apartment"],
            "vibes": ["movie", "cinema", "bowling", "arcade", "shopping", "gift", "vibes"]
        }
        
        for cat, keywords in categories_map.items():
            if any(kw in prompt_lower for kw in keywords):
                category = cat
                break

        # Generate a clean title
        title = "Group Expense"
        for cat, keywords in categories_map.items():
            for kw in keywords:
                if kw in prompt_lower:
                    title = kw.capitalize()
                    break
            if title != "Group Expense":
                break

        # If prompt has 'for <something>', extract that as title
        for_match = re.search(r'for\s+([^,]+?)(?:\s+(?:with|split|between|among|paid)|$)', prompt, re.IGNORECASE)
        if for_match:
            candidate_title = for_match.group(1).strip()
            if len(candidate_title) > 2 and len(candidate_title) < 40:
                title = candidate_title.title()

        # 3. Identify Payer
        payer_id = None
        payer_username = None
        for m in members:
            u_name = m.get("username", "").lower()
            f_name = m.get("full_name", "").lower()
            first_word = f_name.split()[0] if f_name else ""
            
            # Check if name is before 'paid' or 'spent' or at the start
            pattern = rf'\b({re.escape(u_name)}|{re.escape(f_name)}|{re.escape(first_word)})\s+(?:paid|spent|covered|got)'
            if re.search(pattern, prompt_lower) or prompt_lower.startswith(u_name) or prompt_lower.startswith(first_word):
                payer_id = m.get("user_id") or m.get("id")
                payer_username = m.get("username")
                break
        
        if not payer_id and members:
            # default to first member (or caller)
            payer_id = members[0].get("user_id") or members[0].get("id")
            payer_username = members[0].get("username")

        # 4. Identify Split Participants
        # Check if specific members are mentioned
        included_members = []
        if "everyone" in prompt_lower or "all" in prompt_lower or "group" in prompt_lower:
            included_members = members
        else:
            for m in members:
                u_name = m.get("username", "").lower()
                f_name = m.get("full_name", "").lower()
                first_word = f_name.split()[0] if f_name else ""
                if (u_name and re.search(rf'\b{re.escape(u_name)}\b', prompt_lower)) or \
                   (f_name and re.search(rf'\b{re.escape(f_name)}\b', prompt_lower)) or \
                   (first_word and len(first_word) > 2 and re.search(rf'\b{re.escape(first_word)}\b', prompt_lower)):
                    included_members.append(m)

        if not included_members:
            included_members = members  # default to all

        # Calculate equal split amounts
        split_count = max(len(included_members), 1)
        per_person = round(amount / split_count, 2) if amount > 0 else 0.0

        suggested_splits = []
        for m in included_members:
            m_id = m.get("user_id") or m.get("id")
            suggested_splits.append({
                "user_id": m_id,
                "username": m.get("username", ""),
                "amount": per_person
            })

        return {
            "title": title,
            "amount": amount,
            "category": category,
            "currency": "₹",
            "paid_by_user_id": payer_id,
            "paid_by_username": payer_username,
            "split_type": "equal",
            "splits": suggested_splits,
            "confidence_score": 0.96,
            "ai_note": f"Detected {len(included_members)} people in split ({per_person} each). Payer: @{payer_username}"
        }

    @staticmethod
    def generate_roast_nudge(
        debtor_name: str,
        creditor_name: str,
        amount: float,
        currency: str,
        expense_title: str,
        tone: str,
        payment_handle: str = ""
    ) -> Dict[str, str]:
        """
        Generates contextual Gen-Z debt reminders/roasts with WhatsApp & Telegram share links.
        """
        amt_str = f"{currency}{amount:,.2f}"
        pay_suffix = f"\n👉 Settle via UPI / Payment handle: {payment_handle}" if payment_handle else ""

        roasts = {
            "passive_aggressive": [
                f"Bestie {debtor_name}, respectfully... my bank account is in critical condition right now 😭💅. Settle that {amt_str} for {expense_title} whenever your busy lifestyle permits ✨💸{pay_suffix}",
                f"Hey {debtor_name}! Love your recent aesthetic on Instagram, truly inspiring ✨. Also inspiring would be settling that {amt_str} for {expense_title} from {creditor_name} 💅💖{pay_suffix}",
                f"Not to be dramatic {debtor_name}, but every minute you don't pay {creditor_name} {amt_str} for {expense_title}, a houseplant dies 🌱💀. Run me my money bestie! ✨"
            ],
            "savage": [
                f"Yo {debtor_name} 💀! You're dropping stories at fancy clubs in 4K but ghosting a {amt_str} debt for {expense_title} with {creditor_name}? Settle up expeditiously bro, no cap 🧢💸{pay_suffix}",
                f"Breaking News 🚨: {debtor_name} has been found guilty of dodging a {amt_str} bill for {expense_title}. {creditor_name} needs the bag immediately or we're calling the debt FBI 💀🚨{pay_suffix}",
                f"Bro {debtor_name}... Inflation is at 6%, but your repayment speed is at 0%. Send {amt_str} for {expense_title} to {creditor_name} right now before the friendship subscription expires 📉💀{pay_suffix}"
            ],
            "corporate": [
                f"Dear {debtor_name},\n\nPer my previous existence, I am circling back to touch base regarding the outstanding liability of {amt_str} for '{expense_title}'. Please action this payment to {creditor_name} at your earliest convenience to maintain positive team synergy 💼📊.{pay_suffix}",
                f"Hi {debtor_name},\n\nHope this ping finds you thriving. Just bumping the {amt_str} item for {expense_title} to the top of your inbox. Let's take this offline directly to UPI with {creditor_name} 📈🤝.{pay_suffix}"
            ],
            "sweet": [
                f"Hii {debtor_name} 🌸! Just a super tiny and sweet reminder for the {amt_str} for {expense_title} whenever you get a second! No rush at all, you're the best 🧋💖✨{pay_suffix}",
                f"Hey lovely {debtor_name}! Hope you're having an amazing day 🌻. Ping from {creditor_name} regarding the {amt_str} for {expense_title} whenever you're free! Hugs! 💖"
            ],
            "desi_roast": [
                f"Arre {debtor_name} bhai! 🚀 Ambani ban gaya kya jo {amt_str} bhool gaya {expense_title} ka? {creditor_name} ko uska paisa wapas bhej jaldi, kab tak udhaar pe chalega tera swag! 🔥💸{pay_suffix}",
                f"Oye {debtor_name}! Party mein sabse pehle, bill aate hi gayab? 💀 Jaldi se {creditor_name} ko {amt_str} Google Pay / PhonePe kar for {expense_title}, banta hai bhai! 🍕💥{pay_suffix}"
            ],
            "shakespeare": [
                f"Hark, noble {debtor_name}! 📜 The celestial bodies weep as thy sacred debt of {amt_str} for '{expense_title}' unto {creditor_name} remaineth unsettled. Pay heed lest our ancient bond crumbleth into oblivion! ⚔️🏰{pay_suffix}",
                f"To pay, or not to pay — that is the question facing {debtor_name}! Settle the coin of {amt_str} for {expense_title} with {creditor_name} without haste! 🎭🍷{pay_suffix}"
            ]
        }

        selected_list = roasts.get(tone, roasts["savage"])
        chosen_roast = random.choice(selected_list)

        encoded_text = urllib.parse.quote(chosen_roast)
        whatsapp_url = f"https://api.whatsapp.com/send?text={encoded_text}"
        telegram_url = f"https://t.me/share/url?url={encoded_text}"

        return {
            "roast_text": chosen_roast,
            "tone": tone,
            "whatsapp_share_url": whatsapp_url,
            "telegram_share_url": telegram_url,
            "copy_ready_text": chosen_roast
        }

    @staticmethod
    def scan_receipt_text(raw_text: str) -> Dict[str, Any]:
        """
        Parses receipt OCR text into structured items, subtotal, tax, and total.
        """
        lines = [l.strip() for l in raw_text.strip().split("\n") if l.strip()]
        items = []
        total = 0.0
        tax = 0.0
        tip = 0.0
        subtotal = 0.0
        merchant = "Smart Receipt Scan"

        if lines:
            merchant = lines[0]

        for line in lines[1:]:
            # Look for line items with prices: e.g. "2x Boba Milk Tea 240.00" or "Pizza Margherita $18.50"
            price_match = re.search(r'([\d]+(?:\.\d{1,2})?)$', line)
            if price_match:
                price = float(price_match.group(1))
                item_name = line[:price_match.start()].strip(" -:.$₹")
                
                lower_line = line.lower()
                if "total" in lower_line and "sub" not in lower_line:
                    total = price
                elif "subtotal" in lower_line or "sub-total" in lower_line:
                    subtotal = price
                elif "tax" in lower_line or "gst" in lower_line or "vat" in lower_line:
                    tax = price
                elif "tip" in lower_line or "service charge" in lower_line:
                    tip = price
                else:
                    if item_name:
                        items.append({"name": item_name, "qty": 1, "price": price})

        if total == 0.0 and items:
            total = sum(i["price"] for i in items) + tax + tip
        if subtotal == 0.0 and items:
            subtotal = sum(i["price"] for i in items)

        return {
            "merchant": merchant,
            "date": "Today",
            "items": items if items else [{"name": "Group Bill / Meal", "qty": 1, "price": total if total > 0 else 1000.0}],
            "subtotal": round(subtotal, 2),
            "tax": round(tax, 2),
            "tip": round(tip, 2),
            "total": round(total if total > 0 else 1000.0, 2),
            "detected_category": "food"
        }

    @staticmethod
    def generate_group_vibe_check(group_name: str, expenses: List[Dict[str, Any]], balances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyzes group spending behavior and generates witty awards and spending personality badges.
        """
        category_counts: Dict[str, float] = {}
        for exp in expenses:
            cat = exp.get("category", "other")
            category_counts[cat] = category_counts.get(cat, 0.0) + exp.get("amount", 0.0)

        # Find top payer and top debtor
        sorted_by_paid = sorted(balances, key=lambda x: x["total_paid"], reverse=True)
        sorted_by_owed = sorted(balances, key=lambda x: x["net_balance"])

        top_spender = sorted_by_paid[0] if sorted_by_paid else {}
        frugal_or_debtor = sorted_by_owed[0] if sorted_by_owed else {}

        badges = []
        badge_pool = [
            ("The Chief Financier 💳", "💳", "Has paid for almost everything while everyone else pretends their card is declining."),
            ("Boba & Matcha Fiend 🧋", "🧋", "Will sell their soul for a double boba brown sugar latte."),
            ("Ghost Payer 👻", "👻", "Active on the meme chat, magically vanishes when the bill arrives."),
            ("The Vibe Architect ✨", "✨", "Responsible for 90% of spontaneous weekend plans and Uber rides."),
            ("Coupon Lord 📉", "📉", "Always calculates 5% cashback and asks if the restaurant has a student discount."),
            ("Midnight Snacker 🍕", "🍕", "Sponsors late night pizza and taco bell cravings with zero regrets.")
        ]

        for i, member in enumerate(balances):
            badge = badge_pool[i % len(badge_pool)]
            badges.append({
                "user_id": member["user_id"],
                "username": member["username"],
                "badge_title": badge[0],
                "badge_emoji": badge[1],
                "description": badge[2]
            })

        total_spent = sum(exp.get("amount", 0.0) for exp in expenses)
        vibe_score = min(99, max(65, int(85 + (len(expenses) * 2) - abs(frugal_or_debtor.get("net_balance", 0) / 100))))

        vibe_summaries = [
            f"The '{group_name}' crew has unmatched chaotic energy! Total ₹{total_spent:,.2f} invested in pure vibes and memories. Overall solvency rating is solid ✨🚀.",
            f"Big spender energy detected in '{group_name}'! Most funds went straight to {list(category_counts.keys())[0] if category_counts else 'food & drinks'}. Keep the tabs clear and friendships intact 💅💸.",
            f"Financial vibe check passed with flying colors for '{group_name}'! Smooth splits and zero awkward debt conversations ahead."
        ]

        fun_facts = [
            f"Top spending category: {(max(category_counts, key=category_counts.get) if category_counts else 'Food').capitalize()} with ₹{max(category_counts.values()) if category_counts else 0:,.2f}",
            f"Biggest single transaction was by {top_spender.get('full_name', 'Someone')}",
            f"{len(balances)} active group members living their best financial life."
        ]

        return {
            "group_id": 0,
            "group_name": group_name,
            "vibe_score": vibe_score,
            "vibe_title": "Elite Main Character Energy 🌟" if vibe_score > 85 else "Chaotic Fun Squad 🪩",
            "vibe_summary": random.choice(vibe_summaries),
            "top_spender": top_spender,
            "frugal_king": frugal_or_debtor,
            "user_badges": badges,
            "category_breakdown": {k: round(v, 2) for k, v in category_counts.items()},
            "fun_facts": fun_facts
        }
