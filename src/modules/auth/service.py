
from .schema import VerifyEmailEnum, RegisterSchema
from src.models import User, EmailVerification
from src.utils.response import CustomResponse as cr
from src.common.utils import generate_numeric_token, hash_password
from datetime import datetime, timedelta
from fastapi import BackgroundTasks
from src.config.mail import mail_sender
from src.tasks.auth_task import send_verification_email,send_forgot_password_email


class AuthService:

    @staticmethod
    def send_verification_email(email:str,token:str):
        print("send email verifications ...")
        mail_sender.send(
            subject="Email Verification",
            recipients=[email],
            body_html=f"<p>Email Verification Token: {token}</p>",
            # body_text="This is a test email.",
        )
    
    @staticmethod
    def send_forgot_password_email(email: str, token: str, frontend_url: str):
        full_link = f"{frontend_url}/forgot-password-verify?email={email}&token={token}"
        print(f"Sending forgot password email to {email} with token {token}")
        mail_sender.send(
            subject="Forgot Password",
            recipients=[email],
            body_html=f"<p>Forgot Password Token: {token} and <a href='{full_link}'>Click here to reset your password. </a></p> ",
            body_text="This is a test email.",
        )
    
    
    


    @staticmethod
    async def generate_verification(user,type:VerifyEmailEnum):
        token = generate_numeric_token(6)
        print(f"token {token} for user {user.email}")
        # Here you would typically send a verification email

        await EmailVerification.create(
            user_id=user.id,
            token=token,
            is_used=False,
            expires_at=datetime.utcnow() + timedelta(days=1),
            type=type,
        )
        return token




    @staticmethod
    async def register(schema: RegisterSchema, backgroundTask:BackgroundTasks):
        user = await User.find_one({"email": schema.email})

        # Check if user already exists
        if user:
            return cr.error(
                data={"success": False}, message="This email has already been registered"
            )

        hashed_password = hash_password(schema.password)
        user = await User.create(
            email=schema.email, name=schema.name, password=hashed_password
        )
        print(f"user {user.email} created")

        token = await AuthService.generate_verification(user,VerifyEmailEnum.EmailVerification)
        send_verification_email.send(email=user.email, token=token)
        # backgroundTask.add_task(AuthService.send_verification_email,email=user.email,token=token)

        return cr.success(
            data={"user": user.to_json()}, message="User registered successfully"
        )

    @staticmethod
    async def forgot_password_request(email:str,origin:str,backgroundTask:BackgroundTasks):
        user = await User.find_one({"email": email})
        if not user:
            return cr.error(data={"success": False}, message="Email not found")
        token = await AuthService.generate_verification(user,VerifyEmailEnum.ForgotPassword)
        send_forgot_password_email.send(email=email, token=token, frontend_url=origin)
        return cr.success(data={"message": "Password reset link sent to your email"})


