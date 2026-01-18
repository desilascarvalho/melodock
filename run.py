from app import create_app

app = create_app()

if __name__ == '__main__':
    print("=== AUTOGRATHUS REBOOT ===")
    app.run(host='0.0.0.0', port=9014, debug=True, use_reloader=False)