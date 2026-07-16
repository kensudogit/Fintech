.PHONY: up down api frontend streamlit seed

up:
	docker compose up -d postgres

down:
	docker compose down

api:
	cd backend && .venv/Scripts/uvicorn.exe app.main:app --reload --port 8080

frontend:
	cd frontend && npm run dev

streamlit:
	cd streamlit_app && ../backend/.venv/Scripts/streamlit.exe run app.py --server.port 8501

seed:
	cd backend && .venv/Scripts/python.exe -m scripts.seed_events
