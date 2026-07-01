import app

print("=== DEBUGGING: What live data does the CEO see? ===\n")
data = app._fetch_live_company_data(user_id=1, user_role="ceo")
print(data)
print("\n\n=== END OF LIVE DATA ===")
