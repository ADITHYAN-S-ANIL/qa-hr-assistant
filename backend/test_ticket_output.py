import sys
import app

output = app.get_jira_ticket_status.invoke({"ticket_id": "999", "current_user_id": 1, "current_user_role": "ceo"})
print(output)
