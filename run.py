from app import create_app

app = create_app()

if __name__ == "__main__":
    # use_reloader=False evita que o Flask mate o APScheduler ao recarregar
    app.run(debug=True, use_reloader=False)
