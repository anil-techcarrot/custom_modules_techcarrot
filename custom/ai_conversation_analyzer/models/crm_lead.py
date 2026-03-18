# from odoo import models, fields
# import requests
# import json
#
# class CrmLead(models.Model):
#     _inherit = 'crm.lead'
#
#     conversation_summary = fields.Text("Conversation Summary")
#
#     sentiment = fields.Selection([
#         ('positive', 'Positive'),
#         ('negative', 'Negative'),
#         ('neutral', 'Neutral')
#     ])
#
#     meeting_required = fields.Boolean()
#     client_visit = fields.Boolean()
#
#     def _call_groq_api(self, text):
#         api_key = self.env['ir.config_parameter'].sudo().get_param('ai.api.key')
#
#         url = "https://api.groq.com/openai/v1/chat/completions"
#
#         headers = {
#             "Authorization": f"Bearer {api_key}",
#             "Content-Type": "application/json"
#         }
#
#         payload = {
#             "model": "llama-3.3-70b-versatile",
#             "temperature": 0,
#             "messages": [
#                 {
#                     "role": "system",
#                     "content": "You are a strict AI classifier. Return ONLY JSON."
#                 },
#                 {
#                     "role": "user",
#                     "content": f"""
# Analyze and return ONLY JSON:
# {{
#   "sentiment": "positive | negative | neutral",
#   "meeting_required": true/false,
#   "client_visit": true/false
# }}
#
# Rules:
# - Only true if explicitly mentioned
# - No assumptions
#
# Conversation:
# {text}
# """
#                 }
#             ]
#         }
#
#         response = requests.post(url, headers=headers, json=payload)
#
#         if response.status_code != 200:
#             return {}
#
#         result = response.json()
#         content = result['choices'][0]['message']['content']
#
#         cleaned = content.replace('```json', '').replace('```', '').strip()
#
#         try:
#             return json.loads(cleaned)
#         except:
#             return {}
#
#     def action_analyze_conversation(self):
#         for record in self:
#             if not record.conversation_summary:
#                 continue
#
#             result = record._call_groq_api(record.conversation_summary)
#
#             record.sentiment = result.get('sentiment')
#             record.meeting_required = result.get('meeting_required', False)
#             record.client_visit = result.get('client_visit', False)
#
#             # Rule-based fix
#             text = record.conversation_summary.lower()
#
#             if "visit" not in text:
#                 record.client_visit = False
#
#             if "meet" not in text:
#                 record.meeting_required = False
#
#             # Create meeting
#             if record.meeting_required:
#                 self.env['calendar.event'].create({
#                     'name': f"Meeting with {record.name}",
#                     'start': fields.Datetime.now(),
#                     'stop': fields.Datetime.now(),
#                 })

#
# from odoo import models, fields
# import requests
# import json
# import re
#
# class CrmLead(models.Model):
#     _inherit = 'crm.lead'
#
#     conversation_summary = fields.Text("Conversation Summary")
#
#     sentiment = fields.Selection([
#         ('positive', 'Positive'),
#         ('negative', 'Negative'),
#         ('neutral', 'Neutral')
#     ])
#
#     meeting_required = fields.Boolean()
#     client_visit = fields.Boolean()
#
#     def _call_groq_api(self, text):
#         api_key = self.env['ir.config_parameter'].sudo().get_param('ai.api.key')
#
#         url = "https://api.groq.com/openai/v1/chat/completions"
#
#         headers = {
#             "Authorization": f"Bearer {api_key}",
#             "Content-Type": "application/json"
#         }
#
#         payload = {
#             "model": "llama-3.3-70b-versatile",
#             "temperature": 0,
#             "messages": [
#                 {
#                     "role": "system",
#                     "content": (
#                         "You are a strict JSON classifier for customer-agent conversations. "
#                         "Return ONLY a raw JSON object with no explanation, no markdown, no code fences."
#                     )
#                 },
#                 {
#                     "role": "user",
#                     "content": f"""Analyze the conversation below and return ONLY this JSON:
# {{
#   "sentiment": "positive | negative | neutral",
#   "meeting_required": true | false,
#   "client_visit": true | false
# }}
#
# CLASSIFICATION RULES — follow in strict priority order:
#
# 1. client_visit = true ONLY when the customer explicitly says they will come to / visit the company's office.
#    Examples that set client_visit=true (and meeting_required=false):
#    - "I will come to your office"
#    - "I'll visit your office on Monday"
#    - "Can I come in person to your office?"
#    - "Let's meet at your office" / "Let's have a meeting at your office"
#
# 2. meeting_required = true ONLY when both parties agree to a scheduled call, video meeting, or remote session — with NO mention of visiting the office.
#    Examples that set meeting_required=true (and client_visit=false):
#    - "Let's schedule a call"
#    - "Can we set up a Zoom/Teams meeting?"
#    - "Let's have a meeting" (with no office mention)
#
# 3. MUTUAL EXCLUSION RULE — these two fields must NEVER both be true at the same time.
#    - If the conversation mentions meeting AT / IN the office → client_visit=true, meeting_required=false
#    - If the conversation mentions a remote/virtual/phone meeting → meeting_required=true, client_visit=false
#    - If both are mentioned, prefer whichever is more recent or more explicit in the conversation.
#
# 4. If neither is clearly mentioned → both are false.
#
# 5. sentiment: Evaluate the overall emotional tone of the customer's messages.
#    - positive: satisfied, happy, enthusiastic
#    - negative: frustrated, angry, dissatisfied
#    - neutral: factual, no strong emotion
#
# CONVERSATION:
# {text}"""
#                 }
#             ]
#         }
#
#         response = requests.post(url, headers=headers, json=payload)
#
#         if response.status_code != 200:
#             return {}
#
#         result = response.json()
#         content = result['choices'][0]['message']['content']
#         cleaned = content.replace('```json', '').replace('```', '').strip()
#
#         try:
#             return json.loads(cleaned)
#         except Exception:
#             return {}
#
#     def _post_process_flags(self, result, text):
#         """
#         Safety-net rule engine to fix mutual exclusion after AI response.
#         Runs AFTER the AI call to catch edge cases the model may still get wrong.
#         """
#         text_lower = text.lower()
#
#         # --- Detect office-visit signals ---
#         OFFICE_VISIT_PATTERNS = [
#             r'\b(come|visit|drop\s*by|stop\s*by|walk\s*in|in[ -]person)\b.{0,40}\b(office|branch|location|premises|store)\b',
#             r'\b(office|branch|location|premises|store)\b.{0,40}\b(visit|come|in[ -]person)\b',
#             r'\bmeet\b.{0,30}\b(at|in)\b.{0,20}\b(your|the|our)\b.{0,10}\b(office|branch|location)\b',
#             r'\bhave\s+a\s+meet(ing)?\b.{0,30}\b(at|in)\b.{0,20}\b(office|branch|location)\b',
#         ]
#
#         # --- Detect remote-meeting signals ---
#         REMOTE_MEETING_PATTERNS = [
#             r'\b(schedule|set\s*up|arrange|book)\b.{0,30}\b(call|meeting|session|zoom|teams|meet|video)\b',
#             r'\b(zoom|google\s*meet|teams|webex|skype)\b',
#             r'\b(phone\s*call|video\s*call|conference\s*call)\b',
#             r'\b(virtual|remote|online)\b.{0,20}\b(meeting|session|call)\b',
#             r'\bmeet(ing)?\b.{0,30}\b(over\s*(the\s*)?(phone|video|call|zoom))\b',
#         ]
#
#         office_visit_detected = any(
#             re.search(p, text_lower) for p in OFFICE_VISIT_PATTERNS
#         )
#         remote_meeting_detected = any(
#             re.search(p, text_lower) for p in REMOTE_MEETING_PATTERNS
#         )
#
#         meeting_required = result.get('meeting_required', False)
#         client_visit = result.get('client_visit', False)
#
#         # Apply mutual exclusion
#         if client_visit and meeting_required:
#             # Both true — resolve conflict
#             if office_visit_detected and not remote_meeting_detected:
#                 meeting_required = False
#             elif remote_meeting_detected and not office_visit_detected:
#                 client_visit = False
#             elif office_visit_detected and remote_meeting_detected:
#                 # Both pattern types found — trust AI's original answer
#                 # but log for review (you can extend this to flag for manual review)
#                 pass
#             else:
#                 # AI said both true but no patterns found — conservative default
#                 meeting_required = False
#                 client_visit = False
#
#         # Sanity checks: if AI said true but zero keyword signals exist
#         if client_visit and not office_visit_detected:
#             client_visit = False
#
#         if meeting_required and not remote_meeting_detected:
#             # Don't kill it entirely — "let's meet" alone is valid
#             generic_meet = re.search(r'\bmeet(ing)?\b', text_lower)
#             if not generic_meet:
#                 meeting_required = False
#
#         result['meeting_required'] = meeting_required
#         result['client_visit'] = client_visit
#         return result
#
#     def action_analyze_conversation(self):
#         for record in self:
#             if not record.conversation_summary:
#                 continue
#
#             result = record._call_groq_api(record.conversation_summary)
#
#             if not result:
#                 continue
#
#             # Apply rule-based post-processing for mutual exclusion safety net
#             result = record._post_process_flags(result, record.conversation_summary)
#
#             record.sentiment = result.get('sentiment')
#             record.meeting_required = result.get('meeting_required', False)
#             record.client_visit = result.get('client_visit', False)
#
#             # Auto-schedule meeting in calendar if required
#             if record.meeting_required:
#                 meeting_start = fields.Datetime.now()
#                 # Default to 1-hour slot; extend as needed
#                 from datetime import timedelta
#                 meeting_stop = meeting_start + timedelta(hours=1)
#
#                 self.env['calendar.event'].create({
#                     'name': f"Meeting with {record.partner_id.name or record.name}",
#                     'start': meeting_start,
#                     'stop': meeting_stop,
#                     'partner_ids': [(4, record.partner_id.id)] if record.partner_id else [],
#                     'user_id': record.user_id.id if record.user_id else self.env.uid,
#                     'description': f"Auto-scheduled from AI analysis.\n\nSummary:\n{record.conversation_summary}",
#                 })





#
# from odoo import models, fields
# import requests
# import json
# import re
# from datetime import timedelta
#
#
# class CrmLead(models.Model):
#     _inherit = 'crm.lead'
#
#     conversation_summary = fields.Text("Conversation Summary")
#
#     sentiment = fields.Selection([
#         ('positive', 'Positive'),
#         ('negative', 'Negative'),
#         ('neutral', 'Neutral')
#     ])
#
#     meeting_required = fields.Boolean("Meeting Required")
#     client_visit = fields.Boolean("Client Will Visit Office")
#
#     # ─────────────────────────────────────────────
#     # 1. GROQ API CALL
#     # ─────────────────────────────────────────────
#     def _call_groq_api(self, text):
#         api_key = self.env['ir.config_parameter'].sudo().get_param('ai.api.key')
#
#         url = "https://api.groq.com/openai/v1/chat/completions"
#
#         headers = {
#             "Authorization": f"Bearer {api_key}",
#             "Content-Type": "application/json"
#         }
#
#         payload = {
#             "model": "llama-3.3-70b-versatile",
#             "temperature": 0,
#             "messages": [
#                 {
#                     "role": "system",
#                     "content": (
#                         "You are a strict JSON classifier for customer-agent conversations. "
#                         "Return ONLY a raw JSON object with no explanation, no markdown, no code fences."
#                     )
#                 },
#                 {
#                     "role": "user",
#                     "content": f"""Analyze the conversation below and return ONLY this JSON:
# {{
#   "sentiment": "positive | negative | neutral",
#   "meeting_required": true | false,
#   "client_visit": true | false
# }}
#
# CLASSIFICATION RULES:
#
# 1. Read the FULL conversation as a single context, not line by line.
#    The meaning of words like "meeting", "meet", "set up a meeting" depends
#    on what was already established earlier in the conversation.
#
# 2. client_visit = true when the conversation collectively establishes that
#    the meeting will happen physically at the office — regardless of WHO
#    proposed it (agent or customer) and regardless of whether the customer
#    repeats the word "office" in their reply.
#
#    Examples that set client_visit=true, meeting_required=false:
#    - Agent: "Shall we meet in office?" → Customer: "Yes, let's set up a meeting on Wednesday"
#      (customer confirmed the office context, so "meeting" means office visit)
#    - Agent: "You can come to our office" → Customer: "Sure, I'll be there Friday"
#    - Customer: "I will come to your office on Monday"
#    - Customer: "Let's meet at your office"
#    - Customer: "Can I visit your branch?"
#
# 3. meeting_required = true ONLY when the meeting is clearly remote —
#    phone call, video call, Zoom, Teams, Google Meet, Skype, or online session,
#    AND there is NO prior office context established in the conversation.
#
#    Examples that set meeting_required=true, client_visit=false:
#    - "Let's get on a Zoom call"
#    - "Can we do a phone call tomorrow?"
#    - "Schedule a Teams meeting"
#    - "Let's have a video call"
#    - "Can we meet over the phone?"
#
# 4. Generic "meeting" or "meet" with NO location or medium mentioned:
#    - If office was already mentioned anywhere in the conversation → client_visit=true
#    - If no office or remote medium was mentioned → meeting_required=true, client_visit=false
#
# 5. MUTUAL EXCLUSION — meeting_required and client_visit must NEVER both be true
#    UNLESS two clearly separate future events are explicitly mentioned.
#    Example of valid both=true:
#    - "Let's do a quick Zoom call first, and then I will come to your office to sign the papers"
#
# 6. sentiment — evaluate the overall emotional tone of the customer's messages only:
#    - positive : satisfied, happy, enthusiastic, appreciative
#    - negative : frustrated, angry, dissatisfied, complaining
#    - neutral  : factual, informational, no strong emotion
#
# CONVERSATION:
# {text}"""
#                 }
#             ]
#         }
#
#         try:
#             response = requests.post(url, headers=headers, json=payload, timeout=15)
#             if response.status_code != 200:
#                 return {}
#
#             result = response.json()
#             content = result['choices'][0]['message']['content']
#             cleaned = content.replace('```json', '').replace('```', '').strip()
#             return json.loads(cleaned)
#
#         except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError):
#             return {}
#
#     # ─────────────────────────────────────────────
#     # 2. AGENT OFFICE PROPOSAL + CUSTOMER AGREEMENT
#     # ─────────────────────────────────────────────
#     def _detect_office_visit_with_agreement(self, text):
#         """
#         Detects when the agent proposes an office meeting and
#         the customer agrees — even if the customer never says 'office'.
#
#         Example:
#             Agent:    "Shall we meet in office this week?"
#             Customer: "Yes absolutely, let's set up a meeting on Wednesday."
#             → client_visit = True
#         """
#         lines = text.split('\n')
#
#         AGENT_OFFICE_PROPOSALS = [
#             r'\bmeet\b.{0,30}\bin\b.{0,20}\boffice\b',
#             r'\bmeet\b.{0,30}\bat\b.{0,20}\b(our|the|your)\b.{0,10}\boffice\b',
#             r'\b(shall|should|can|could|would)\s+we\b.{0,40}\b(meet|come)\b.{0,30}\boffice\b',
#             r'\bin\s+(the\s+)?office\b.{0,40}\b(meet|discuss|finalize|catch\s*up)\b',
#             r'\b(meet|discuss|finalize|catch\s*up)\b.{0,40}\bin\s+(the\s+)?office\b',
#             r'\bcome\b.{0,30}\bto\b.{0,20}\b(our|the)\b.{0,10}\boffice\b',
#             r'\bvisit\b.{0,30}\b(our|the)\b.{0,10}\boffice\b',
#         ]
#
#         CUSTOMER_AGREEMENT = [
#             r'\b(yes|yeah|yep|sure|absolutely|definitely|agreed|okay|ok|alright)\b',
#             r'\bsounds\s+(good|great|perfect|fine)\b',
#             r'\b(perfect|great|wonderful|excellent|fantastic)\b',
#             r"\blet'?s\b.{0,30}\b(set\s*up|schedule|do|have|arrange|fix)\b",
#             r'\b(works\s+for\s+me|that\s+works|looking\s+forward)\b',
#             r"\bi'?ll\s+be\s+there\b",
#             r'\bi\s+can\s+(come|make\s+it)\b',
#         ]
#
#         CUSTOMER_REJECTION = [
#             r'\b(no|nope|cannot|can\'t|prefer\s+not|rather\s+not|instead|prefer\s+a\s+call)\b',
#             r'\b(video\s+call|phone\s+call|zoom|teams|remotely|virtually|online)\b',
#         ]
#
#         agent_proposed_office = False
#
#         for line in lines:
#             line_lower = line.lower().strip()
#
#             if not line_lower:
#                 continue
#
#             is_agent = line_lower.startswith('agent:')
#             is_customer = line_lower.startswith('customer:')
#
#             if is_agent:
#                 if any(re.search(p, line_lower) for p in AGENT_OFFICE_PROPOSALS):
#                     agent_proposed_office = True
#
#             elif is_customer and agent_proposed_office:
#                 # Customer rejected the office proposal
#                 if any(re.search(p, line_lower) for p in CUSTOMER_REJECTION):
#                     agent_proposed_office = False
#                 # Customer agreed
#                 elif any(re.search(p, line_lower) for p in CUSTOMER_AGREEMENT):
#                     return True
#
#         return False
#
#     # ─────────────────────────────────────────────
#     # 3. POST-PROCESSING SAFETY NET
#     # ─────────────────────────────────────────────
#     def _post_process_flags(self, result, text):
#         """
#         Rule-based safety net that runs after the AI response.
#         Fixes mutual exclusion conflicts and catches missed patterns.
#         """
#         text_lower = text.lower()
#
#         # --- Office visit signals (direct) ---
#         OFFICE_VISIT_PATTERNS = [
#             # Customer says they'll come
#             r'\b(come|visit|drop\s*by|stop\s*by|walk\s*in)\b.{0,40}\b(office|branch|location|premises)\b',
#             r'\b(office|branch|location|premises)\b.{0,40}\b(visit|come|drop\s*by|in[ -]person)\b',
#             # Anyone says "meet in/at office"
#             r'\bmeet\b.{0,30}\b(at|in)\b.{0,20}\b(your|the|our)\b.{0,10}\b(office|branch|location)\b',
#             r'\bhave\s+a\s+meet(ing)?\b.{0,30}\b(at|in)\b.{0,20}\b(office|branch|location)\b',
#             r'\bmeet\b.{0,20}\bin\b.{0,20}\boffice\b',
#             r'\b(meeting|meet|discuss|finalize)\b.{0,40}\bin\s+(the\s+)?office\b',
#             r'\bin\s+(the\s+)?office\b.{0,40}\b(meeting|meet|discuss|finalize)\b',
#             # Agent proposes, any form
#             r'\b(shall|should|can|could|would)\s+we\b.{0,40}\b(meet|come)\b.{0,30}\b(office|in[ -]person)\b',
#         ]
#
#         # --- Remote meeting signals ---
#         REMOTE_MEETING_PATTERNS = [
#             r'\b(schedule|set\s*up|arrange|book)\b.{0,30}\b(call|session|zoom|teams|meet|video)\b',
#             r'\b(zoom|google\s*meet|teams|webex|skype|meet)\b',
#             r'\b(phone\s*call|video\s*call|conference\s*call|voice\s*call)\b',
#             r'\b(virtual|remote|online)\b.{0,20}\b(meeting|session|call)\b',
#             r'\bmeet(ing)?\b.{0,30}\bover\s*(the\s*)?(phone|video|call|zoom)\b',
#         ]
#
#         office_visit_detected = (
#             any(re.search(p, text_lower) for p in OFFICE_VISIT_PATTERNS)
#             or self._detect_office_visit_with_agreement(text)
#         )
#
#         remote_meeting_detected = any(
#             re.search(p, text_lower) for p in REMOTE_MEETING_PATTERNS
#         )
#
#         meeting_required = result.get('meeting_required', False)
#         client_visit = result.get('client_visit', False)
#
#         # ── Resolve mutual exclusion conflict ──
#         if client_visit and meeting_required:
#             if office_visit_detected and not remote_meeting_detected:
#                 meeting_required = False
#             elif remote_meeting_detected and not office_visit_detected:
#                 client_visit = False
#             # Both patterns found = two separate events, keep both true
#             # Neither pattern found = conservative default
#             elif not office_visit_detected and not remote_meeting_detected:
#                 meeting_required = False
#                 client_visit = False
#
#         # ── Sanity: AI said client_visit=true but no office signals found ──
#         if client_visit and not office_visit_detected:
#             client_visit = False
#
#         # ── Sanity: AI said meeting_required=true but no remote signals found ──
#         if meeting_required and not remote_meeting_detected:
#             generic_meet = re.search(r'\bmeet(ing)?\b', text_lower)
#             if not generic_meet:
#                 meeting_required = False
#
#         result['meeting_required'] = meeting_required
#         result['client_visit'] = client_visit
#         return result
#
#     # ─────────────────────────────────────────────
#     # 4. CREATE CALENDAR EVENT
#     # ─────────────────────────────────────────────
#     def _create_calendar_meeting(self, record):
#         """
#         Auto-schedules a calendar event in Odoo linked to
#         the agent and the customer.
#         """
#         now = fields.Datetime.now()
#
#         event_vals = {
#             'name': f"Meeting with {record.partner_id.name or record.name}",
#             'start': now,
#             'stop': now + timedelta(hours=1),
#             'description': (
#                 f"Auto-scheduled from AI conversation analysis.\n\n"
#                 f"Sentiment: {record.sentiment}\n\n"
#                 f"Summary:\n{record.conversation_summary}"
#             ),
#             'user_id': record.user_id.id if record.user_id else self.env.uid,
#         }
#
#         # Link customer if partner exists on the lead
#         if record.partner_id:
#             event_vals['partner_ids'] = [(4, record.partner_id.id)]
#
#         # Also add the responsible agent as attendee
#         if record.user_id and record.user_id.partner_id:
#             event_vals.setdefault('partner_ids', [])
#             event_vals['partner_ids'].append((4, record.user_id.partner_id.id))
#
#         self.env['calendar.event'].create(event_vals)
#
#     # ─────────────────────────────────────────────
#     # 5. MAIN ACTION
#     # ─────────────────────────────────────────────
#     def action_analyze_conversation(self):
#         for record in self:
#             if not record.conversation_summary:
#                 continue
#
#             # Step 1: Call AI
#             result = record._call_groq_api(record.conversation_summary)
#
#             if not result:
#                 continue
#
#             # Step 2: Post-process for safety
#             result = record._post_process_flags(result, record.conversation_summary)
#
#             # Step 3: Write fields
#             record.sentiment = result.get('sentiment')
#             record.meeting_required = result.get('meeting_required', False)
#             record.client_visit = result.get('client_visit', False)
#
#             # Step 4: Auto-schedule if meeting required
#             if record.meeting_required:
#                 record._create_calendar_meeting(record)

from odoo import models, fields
import requests
import json
import re
from datetime import timedelta


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    conversation_summary = fields.Text("Conversation Summary")

    sentiment = fields.Selection([
        ('positive', 'Positive'),
        ('negative', 'Negative'),
        ('neutral', 'Neutral')
    ])

    meeting_required = fields.Boolean("Meeting Required")
    client_visit = fields.Boolean("Client Will Visit Office")

    # ─────────────────────────────────────────────
    # 1. GROQ API CALL
    # ─────────────────────────────────────────────
    def _call_groq_api(self, text):
        api_key = self.env['ir.config_parameter'].sudo().get_param('ai.api.key')

        url = "https://api.groq.com/openai/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "llama-3.3-70b-versatile",
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a strict JSON classifier for customer-agent conversations. "
                        "Return ONLY a raw JSON object with no explanation, no markdown, no code fences."
                    )
                },
                {
                    "role": "user",
                    "content": f"""Analyze the conversation below and return ONLY this JSON:
{{
  "sentiment": "positive | negative | neutral",
  "meeting_required": true | false,
  "client_visit": true | false
}}

CLASSIFICATION RULES:

1. Read the FULL conversation as a single context, not line by line.
   The meaning of words like "meeting", "meet", "set up a meeting" depends
   on what was already established earlier in the conversation.

2. client_visit = true ONLY when the conversation establishes that the
   customer will physically come to the office/branch/location.
   This can be proposed by agent OR customer — what matters is that
   both parties end up agreeing on an in-person visit.

   Examples that set client_visit=true, meeting_required=false:
   - Agent: "Shall we meet in office?" → Customer: "Yes, let's set up a meeting on Wednesday"
     (customer confirmed office context, so "meeting" = office visit)
   - Agent: "You can come to our office" → Customer: "Sure, I will be there Friday"
   - Customer: "I will come to your office on Monday"
   - Customer: "Let's meet at your office"
   - Customer: "Let's schedule an office meeting"
     ("office meeting" compound phrase = physical visit, NOT a remote meeting)
   - Customer: "Can I visit your branch?"
   - Agent: "Come over and we can discuss face to face" → Customer: "I will come over on Tuesday"
   - Customer: "I was thinking of stopping by your branch" → Agent confirms → Customer: "Perfect, see you then"

2b. IMPORTANT — "office" must refer to the customer physically visiting.
    Ignore "office" when used in these contexts — these are NOT visit signals:
   - "Our office team processed your request" → NOT a visit
   - "Office staff will handle it" → NOT a visit
   - "Our office has already sent the documents" → NOT a visit
   - "Office hours are 9 to 5" → NOT a visit
   Only count "office" as a visit signal when it is a DESTINATION the customer is going to.

3. meeting_required = true ONLY when the meeting is clearly remote:
   phone call, video call, Zoom, Teams, Google Meet, Skype, or online session
   AND there is NO office visit context in the conversation.

   Examples that set meeting_required=true, client_visit=false:
   - "Let's get on a Zoom call"
   - "Can we do a phone call tomorrow?"
   - "Schedule a Teams meeting"
   - "Let's have a video call"
   - "I will call you tomorrow at 11 AM"
   - "Can we get on a quick call?"

4. Generic "meeting" or "meet" resolution:
   - If office was already mentioned as a destination → client_visit=true
   - If a remote medium (Zoom/call/Teams) was mentioned → meeting_required=true
   - If NEITHER location nor medium was mentioned → meeting_required=true, client_visit=false

5. Non-committal / vague visit mentions = client_visit=false:
   These phrases indicate thinking about visiting but NOT confirmed:
   - "maybe I should visit sometime"
   - "perhaps I will stop by later"
   - "I might come over someday"
   UNLESS a later turn in the conversation confirms it (e.g., "Perfect, see you then")

6. MUTUAL EXCLUSION — meeting_required and client_visit must NEVER both be true
   UNLESS two clearly separate future events are explicitly confirmed.
   Valid both=true example:
   - "Let's do a quick Zoom call first, and then I will come to your office to sign"

7. sentiment — evaluate the overall emotional tone of the customer messages only:
   - positive : satisfied, happy, enthusiastic, appreciative
   - negative : frustrated, angry, dissatisfied, complaining, sarcastic
   - neutral  : factual, informational, no strong emotion

CONVERSATION:
{text}"""
                }
            ]
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            if response.status_code != 200:
                return {}

            result = response.json()
            content = result['choices'][0]['message']['content']
            cleaned = content.replace('```json', '').replace('```', '').strip()
            return json.loads(cleaned)

        except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError):
            return {}

    # ─────────────────────────────────────────────
    # 2. OFFICE AS DESTINATION CHECK
    # ─────────────────────────────────────────────
    def _is_office_used_as_destination(self, text_lower):
        """
        Returns True only if 'office/branch' is used as a physical
        destination the customer is going to — not as a department/team reference.
        """
        OFFICE_NON_DESTINATION = [
            r'\boffice\s+(team|staff|department|personnel|has|have|will|is|are|was|were)\b',
            r'\b(our|the|your)\s+office\s+(team|staff|has|have|processed|handled|will|already)\b',
            r'\boffice\s+(hours|number|records|copy|address|email|phone)\b',
            r'\bback\s+(to\s+the\s+)?office\b',
            r'\boffice\s+is\s+(open|closed|available)\b',
        ]

        OFFICE_AS_DESTINATION = [
            r'\b(come|visit|stop\s*by|drop\s*by|walk\s*in|head\s+over)\b.{0,40}\b(office|branch|location|premises)\b',
            r'\b(office|branch|location|premises)\b.{0,40}\b(visit|come|drop\s*by|in[ -]person|walk\s*in)\b',
            r'\b(meet|meeting|discuss|finalize|catch\s*up)\b.{0,30}\b(in|at)\b.{0,20}\b(office|branch|location)\b',
            r'\b(in|at)\b.{0,10}\b(our|the|your)\b.{0,10}\b(office|branch)\b.{0,30}\b(meet|discuss|talk|finalize)\b',
            r'\bmeet\b.{0,20}\bin\b.{0,20}\boffice\b',
            r'\boffice\s+meeting\b',
            r'\b(schedule|book|arrange|set\s*up)\b.{0,20}\b(an?\s+)?office\s+meeting\b',
            r'\bcome\s+to\b.{0,20}\b(our|the|your)\b.{0,10}\b(office|branch)\b',
            r'\bto\s+(our|the|your)\s+(office|branch)\b',
        ]

        non_dest = any(re.search(p, text_lower) for p in OFFICE_NON_DESTINATION)
        as_dest = any(re.search(p, text_lower) for p in OFFICE_AS_DESTINATION)

        if non_dest and not as_dest:
            return False
        return as_dest

    # ─────────────────────────────────────────────
    # 3. VISIT COMMITMENT CHECK
    # ─────────────────────────────────────────────
    def _is_visit_committed(self, text_lower, text_original=None):
        """
        Returns True only when the visit is a firm commitment.
        A hedge early on can be overridden by a confirmation in a later turn.
        Checks the last customer turn separately for final confirmations.
        """
        HEDGE_PATTERNS = [
            r'\b(maybe|perhaps|possibly|might\s+come|could\s+be|sometime|someday|some\s+time\s+later)\b',
            r'\b(thinking\s+of|was\s+thinking|considering|not\s+sure|should\s+visit)\b',
            r'\bif\s+.{0,20}\b(possible|convenient|works|okay|fine)\b',
            r'\bwhen\s+i\s+(get\s+a\s+chance|have\s+time|am\s+free)\b',
        ]

        COMMITMENT_PATTERNS = [
            r"\b(i\s+will|i'll|i\s+am\s+coming|i\s+can\s+come|i\s+shall)\b",
            r'\b(see\s+you\s+(then|there|tomorrow|on\s+\w+day))\b',
            r'\b(i\s+will\s+come|coming\s+on|will\s+be\s+there|be\s+there\s+on)\b',
            r'\b(confirmed|booked|scheduled|fixed|done)\b',
            r'\bi\s+will\s+(stop\s*by|drop\s*by|come\s+over|visit|be\s+there|head\s+over)\b',
            r'\b(perfect|sounds\s+good|great|wonderful)\b.{0,30}\b(see\s+you|i\s+will|i\'ll)\b',
            r'\bsee\s+you\s+then\b',
            r'\bwalk\s+in\b',
            r'\bi\s+will\s+come\s+over\b',
            r'\bthat\s+(works|sounds\s+good|is\s+fine)\b',
        ]

        # Check last customer line separately —
        # a final confirmation overrides any earlier hedging
        last_customer_line = ''
        if text_original:
            lines = text_original.split('\n')
            customer_lines = [
                l.lower() for l in lines
                if l.lower().strip().startswith('customer:')
            ]
            if customer_lines:
                last_customer_line = customer_lines[-1]

        # Final customer turn is a clear commitment → always true
        if last_customer_line and any(
            re.search(p, last_customer_line) for p in COMMITMENT_PATTERNS
        ):
            return True

        hedged = any(re.search(p, text_lower) for p in HEDGE_PATTERNS)
        committed = any(re.search(p, text_lower) for p in COMMITMENT_PATTERNS)

        if hedged and not committed:
            return False
        return True

    # ─────────────────────────────────────────────
    # 4. AGENT OFFICE PROPOSAL + CUSTOMER AGREEMENT
    # ─────────────────────────────────────────────
    def _detect_office_visit_with_agreement(self, text):
        """
        Detects when the agent proposes an office meeting and the customer
        agrees — even if the customer never repeats the word 'office'.

        Example:
            Agent:    "Shall we meet in office this week?"
            Customer: "Yes absolutely, let's set up a meeting on Wednesday."
            → client_visit = True
        """
        lines = text.split('\n')

        AGENT_OFFICE_PROPOSALS = [
            r'\bmeet\b.{0,30}\bin\b.{0,20}\boffice\b',
            r'\bmeet\b.{0,30}\bat\b.{0,20}\b(our|the|your)\b.{0,10}\boffice\b',
            r'\b(shall|should|can|could|would)\s+we\b.{0,40}\b(meet|come)\b.{0,30}\boffice\b',
            r'\bin\s+(the\s+)?office\b.{0,40}\b(meet|discuss|finalize|catch\s*up)\b',
            r'\b(meet|discuss|finalize)\b.{0,40}\bin\s+(the\s+)?office\b',
            r'\bcome\b.{0,30}\bto\b.{0,20}\b(our|the)\b.{0,10}\boffice\b',
            r'\bvisit\b.{0,30}\b(our|the)\b.{0,10}\boffice\b',
            r'\bcome\s+over\b.{0,40}\bface\s+to\s+face\b',
            r'\bface\s+to\s+face\b',
            r'\bin\s+person\b',
            r'\b(stop\s*by|drop\s*by|walk\s*in)\b.{0,30}\b(branch|office|location)\b',
            r'\b(branch|office|location)\b.{0,30}\b(open|available|welcome|feel\s+free)\b',
        ]

        CUSTOMER_AGREEMENT = [
            r'\b(yes|yeah|yep|sure|absolutely|definitely|agreed|okay|ok|alright)\b',
            r'\bsounds\s+(good|great|perfect|fine)\b',
            r'\b(perfect|great|wonderful|excellent|fantastic)\b',
            r"\blet'?s\b.{0,30}\b(set\s*up|schedule|do|have|arrange|fix)\b",
            r'\b(works\s+for\s+me|that\s+works|looking\s+forward)\b',
            r"\bi'?ll\s+be\s+there\b",
            r'\bi\s+will\s+(come\s+over|stop\s*by|drop\s*by|be\s+there|head\s+over)\b',
            r'\bi\s+can\s+(come|make\s+it)\b',
            r'\bsee\s+you\s+then\b',
            r'\bthat\s+(works|sounds\s+good|is\s+fine)\b',
            r'\bwednesday|thursday|friday|monday|tuesday|saturday|sunday\b',
        ]

        CUSTOMER_REJECTION = [
            r'\b(no|nope|cannot|can\'t|prefer\s+not|rather\s+not|instead)\b',
            r'\b(video\s+call|phone\s+call|zoom|teams|remotely|virtually|online|over\s+the\s+phone)\b',
            r'\b(travelling|traveling|out\s+of\s+town|not\s+available\s+in\s+person)\b',
        ]

        agent_proposed_office = False

        for line in lines:
            line_lower = line.lower().strip()

            if not line_lower:
                continue

            is_agent = line_lower.startswith('agent:')
            is_customer = line_lower.startswith('customer:')

            if is_agent:
                if any(re.search(p, line_lower) for p in AGENT_OFFICE_PROPOSALS):
                    agent_proposed_office = True

            elif is_customer and agent_proposed_office:
                if any(re.search(p, line_lower) for p in CUSTOMER_REJECTION):
                    agent_proposed_office = False
                elif any(re.search(p, line_lower) for p in CUSTOMER_AGREEMENT):
                    return True

        return False

    # ─────────────────────────────────────────────
    # 5. POST-PROCESSING SAFETY NET
    # ─────────────────────────────────────────────
    def _post_process_flags(self, result, text):
        """
        Rule-based safety net that runs after the AI response.
        Fixes mutual exclusion conflicts and catches missed patterns.
        """
        text_lower = text.lower()

        # --- Office visit signals ---
        OFFICE_VISIT_PATTERNS = [
            # Customer physically coming
            r'\b(come|visit|stop\s*by|drop\s*by|walk\s*in|head\s+over)\b.{0,40}\b(office|branch|location|premises)\b',
            r'\b(office|branch|location|premises)\b.{0,40}\b(visit|come|drop\s*by|in[ -]person|walk\s*in)\b',
            # Meet in/at office
            r'\bmeet\b.{0,30}\b(at|in)\b.{0,20}\b(your|the|our)\b.{0,10}\b(office|branch|location)\b',
            r'\bhave\s+a\s+meet(ing)?\b.{0,30}\b(at|in)\b.{0,20}\b(office|branch|location)\b',
            r'\bmeet\b.{0,20}\bin\b.{0,20}\boffice\b',
            r'\b(meeting|meet|discuss|finalize)\b.{0,40}\bin\s+(the\s+)?office\b',
            r'\bin\s+(the\s+)?office\b.{0,40}\b(meeting|meet|discuss|finalize)\b',
            # Office meeting compound
            r'\boffice\s+meeting\b',
            r'\b(schedule|book|arrange|set\s*up)\b.{0,20}\b(an?\s+)?office\s+meeting\b',
            # Agent proposes
            r'\b(shall|should|can|could|would)\s+we\b.{0,40}\b(meet|come)\b.{0,30}\b(office|in[ -]person)\b',
            # No office keyword but physical intent clear
            r'\bcome\s+over\b',
            r'\bface\s+to\s+face\b',
            r'\bin\s+person\b',
            r'\b(stop\s*by|drop\s*by)\b',
            r'\bi\s+will\s+(come\s+over|stop\s*by|drop\s*by|head\s+over|be\s+there)\b',
            r'\bsee\s+you\s+(then|there|on\s+\w+day)\b',
            # Branch/location visit
            r'\b(stopping|stop)\s+by\b.{0,30}\b(branch|office|location|store)\b',
            r'\bwalk\s+in\b',
        ]

        # --- Remote meeting signals ---
        REMOTE_MEETING_PATTERNS = [
            r'\b(schedule|set\s*up|arrange|book)\b.{0,30}\b(call|session|zoom|teams|video)\b',
            r'\b(zoom|google\s*meet|teams|webex|skype)\b',
            r'\b(phone\s*call|video\s*call|conference\s*call|voice\s*call)\b',
            r'\b(virtual|remote|online)\b.{0,20}\b(meeting|session|call)\b',
            r'\bmeet(ing)?\b.{0,30}\bover\s*(the\s*)?(phone|video|call|zoom)\b',
            r'\bi\s+will\s+call\s+you\b',
            r'\bget\s+on\s+a\s+(quick\s+)?call\b',
            r'\bsend\s+(you\s+a\s+)?(meeting\s+link|zoom\s+link|calendar\s+invite)\b',
        ]

        # Determine signals using smarter destination check
        office_visit_detected = (
            self._is_office_used_as_destination(text_lower)
            or any(re.search(p, text_lower) for p in OFFICE_VISIT_PATTERNS)
            or self._detect_office_visit_with_agreement(text)
        ) and self._is_visit_committed(text_lower, text_original=text)

        remote_meeting_detected = any(
            re.search(p, text_lower) for p in REMOTE_MEETING_PATTERNS
        )

        meeting_required = result.get('meeting_required', False)
        client_visit = result.get('client_visit', False)

        # ── Resolve mutual exclusion conflict ──
        if client_visit and meeting_required:
            if office_visit_detected and not remote_meeting_detected:
                meeting_required = False
            elif remote_meeting_detected and not office_visit_detected:
                client_visit = False
            # Both detected = two separate events, keep both true
            # Neither detected = conservative default
            elif not office_visit_detected and not remote_meeting_detected:
                meeting_required = False
                client_visit = False

        # ── Sanity: AI said client_visit=true but no signals found ──
        if client_visit and not office_visit_detected:
            client_visit = False

        # ── Sanity: AI said meeting_required=true but no remote signals ──
        if meeting_required and not remote_meeting_detected:
            generic_meet = re.search(r'\bmeet(ing)?\b', text_lower)
            if not generic_meet:
                meeting_required = False

        # ── Final: office visit overrides remote if office destination confirmed ──
        if office_visit_detected and not remote_meeting_detected:
            client_visit = True
            meeting_required = False

        result['meeting_required'] = meeting_required
        result['client_visit'] = client_visit
        return result

    # ─────────────────────────────────────────────
    # 6. CREATE CALENDAR EVENT
    # ─────────────────────────────────────────────
    def _create_calendar_meeting(self, record):
        """
        Auto-schedules a 1-hour calendar event in Odoo linked
        to the responsible agent and the customer.
        """
        now = fields.Datetime.now()

        event_vals = {
            'name': f"Meeting with {record.partner_id.name or record.name}",
            'start': now,
            'stop': now + timedelta(hours=1),
            'description': (
                f"Auto-scheduled from AI conversation analysis.\n\n"
                f"Sentiment  : {record.sentiment}\n"
                f"Meeting    : {record.meeting_required}\n"
                f"Visit      : {record.client_visit}\n\n"
                f"Summary:\n{record.conversation_summary}"
            ),
            'user_id': record.user_id.id if record.user_id else self.env.uid,
        }

        partner_ids = []

        # Add customer
        if record.partner_id:
            partner_ids.append((4, record.partner_id.id))

        # Add responsible agent
        if record.user_id and record.user_id.partner_id:
            partner_ids.append((4, record.user_id.partner_id.id))

        if partner_ids:
            event_vals['partner_ids'] = partner_ids

        self.env['calendar.event'].create(event_vals)

    # ─────────────────────────────────────────────
    # 7. MAIN ACTION
    # ─────────────────────────────────────────────
    def action_analyze_conversation(self):
        for record in self:
            if not record.conversation_summary:
                continue

            # Step 1: Call AI
            result = record._call_groq_api(record.conversation_summary)

            if not result:
                continue

            # Step 2: Post-process for safety
            result = record._post_process_flags(result, record.conversation_summary)

            # Step 3: Write fields
            record.sentiment = result.get('sentiment')
            record.meeting_required = result.get('meeting_required', False)
            record.client_visit = result.get('client_visit', False)

            # Step 4: Auto-schedule if meeting or visit confirmed
            if record.meeting_required or record.client_visit:
                record._create_calendar_meeting(record)