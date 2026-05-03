from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr

# Konfiguracja FastAPI-Mail
conf = ConnectionConfig(
    MAIL_USERNAME = "091e732ec48e10", 
    MAIL_PASSWORD = "f81a2fa2d3bb61",
    MAIL_FROM = "powiadomienia@royalepackage.pl",
    MAIL_PORT = 2525,
    MAIL_SERVER = "sandbox.smtp.mailtrap.io",
    MAIL_STARTTLS = False,
    MAIL_SSL_TLS = False,
    USE_CREDENTIALS = True,
    VALIDATE_CERTS = True
)

fast_mail = FastMail(conf)

# Funkcja do wysyłania maila o zmianie statusu paczki
async def send_status_email(email: EmailStr, tracking_number: str, new_status: str, eta: str = None, courier_name: str = None):

    # Generujemy dodatkowe linijki tekstu tylko wtedy, gdy przekazaliśmy te dane
    eta_html = f"<p style='color: #e5a93d; font-size: 16px;'><strong>Przewidywany czas dostawy:</strong> {eta}</p>" if eta else ""
    courier_html = f"<p style='font-size: 16px;'>Twoją paczkę doręczy nasz kurier: <strong>{courier_name}</strong></p>" if courier_name else ""

    # Tworzymy NOWY, ostylowany szablon HTML w barwach Royale Package i ładujemy zmienne
    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; background-color: #f3f4f6; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                <div style="background-color: #111827; padding: 20px; text-align: center;">
                    <h1 style="color: #e5a93d; margin: 0; font-size: 24px;">ROYALE PACKAGE</h1>
                    <p style="color: #9ca3af; margin: 5px 0 0 0; font-size: 14px;">Premium Courier Services</p>
                </div>
                <div style="padding: 30px; color: #333333;">
                    <h2 style="color: #111827; margin-top: 0;">Witaj, status Twojej przesyłki uległ zmianie!</h2>
                    <p style="font-size: 16px;">Numer paczki: <strong style="color: #111827;">{tracking_number}</strong></p>
                    <p style="font-size: 16px;">Nowy status: <strong style="background-color: #f3f4f6; padding: 5px 10px; border-radius: 4px; color: #111827;">{new_status}</strong></p>
                    
                    {eta_html}
                    {courier_html}
                    
                    <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 25px 0;">
                    <p style="text-align: center; margin: 0;">
                        <a href="http://localhost:5173/tracking/{tracking_number}" style="display: inline-block; background-color: #e5a93d; color: #111827; text-decoration: none; font-weight: bold; padding: 12px 25px; border-radius: 4px;">ŚLEDŹ SWOJĄ PACZKĘ</a>
                    </p>
                </div>
            </div>
        </body>
    </html>
    """

    # Tworzymy wiadomość email
    message = MessageSchema(
        subject=f"Royale Package - Aktualizacja statusu paczki {tracking_number}",
        recipients=[email],
        body=body,
        subtype=MessageType.html
    )

    # Wysyłka maila asynchronicznie
    try:
        await fast_mail.send_message(message)
    except Exception as e:
        print(f"Błąd wysyłki maila: {e}")